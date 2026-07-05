from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import HTTPException

from noteclaw_backend.schemas.common import Citation, new_id
from noteclaw_backend.schemas.evaluation import (
    EvaluationDatasetItem,
    EvaluationItemResult,
    EvaluationRunRequest,
    EvaluationRunResponse,
)
from noteclaw_backend.services.providers import get_llm_provider
from noteclaw_backend.services.retrieval import retrieval_service


class EvaluationService:
    async def run(self, request: EvaluationRunRequest) -> EvaluationRunResponse:
        items = request.items or self._load_demo_items()
        if not items:
            raise HTTPException(status_code=400, detail="Provide evaluation items or add demo_questions.json.")

        results: list[EvaluationItemResult] = []
        hit_values: list[float] = []
        recall_values: list[float] = []
        precision_values: list[float] = []
        reciprocal_rank_values: list[float] = []
        answer_overlap_values: list[float] = []
        completeness_values: list[float] = []
        groundedness_values: list[float] = []
        citation_coverage_values: list[float] = []
        relevance_values: list[float] = []
        hallucination_risk_values: list[float] = []
        judge_values: dict[str, list[float]] = defaultdict(list)

        for index, item in enumerate(items, start=1):
            started = perf_counter()
            rows = await retrieval_service.retrieve_chunks_for_question(
                item.question,
                request.top_k,
                mode=request.mode,
            )
            answer = await self._answer(item.question, rows) if request.generate_answers else None
            latency_ms = round((perf_counter() - started) * 1000, 2)

            retrieved_note_ids = self._dedupe([row.get("note_id") for row in rows])
            retrieved_chunk_ids = self._dedupe([row.get("chunk_id") for row in rows])
            expected_refs = self._expected_refs(item)
            matched_refs = self._matched_refs(item, rows)
            has_expected_refs = bool(expected_refs)

            hit_at_k = 1.0 if matched_refs else 0.0
            recall_at_k = round(len(matched_refs) / len(expected_refs), 4) if has_expected_refs else 0.0
            precision_at_k = self._precision_at_k(item, rows) if has_expected_refs else 0.0
            reciprocal_rank = self._reciprocal_rank(item, rows) if has_expected_refs else 0.0
            if has_expected_refs:
                hit_values.append(hit_at_k)
                recall_values.append(recall_at_k)
                precision_values.append(precision_at_k)
                reciprocal_rank_values.append(reciprocal_rank)

            answer_overlap = None
            completeness_score = None
            groundedness_score = None
            citation_coverage = None
            relevance_score = None
            hallucination_risk = None
            judge_scores: dict[str, float] = {}
            judge_comment: str | None = None

            if answer:
                if item.expected_answer:
                    answer_overlap = self._answer_overlap(answer, item.expected_answer)
                    completeness_score = answer_overlap
                    answer_overlap_values.append(answer_overlap)
                    completeness_values.append(completeness_score)
                groundedness_score = self._groundedness_score(answer, rows)
                citation_coverage = self._citation_coverage(answer, rows)
                relevance_score = self._relevance_score(answer, item.question, item.expected_answer)
                hallucination_risk = round(1.0 - groundedness_score, 4)
                groundedness_values.append(groundedness_score)
                citation_coverage_values.append(citation_coverage)
                relevance_values.append(relevance_score)
                hallucination_risk_values.append(hallucination_risk)

                if request.judge_answers:
                    judge_scores, judge_comment = await self._judge_answer(
                        question=item.question,
                        answer=answer,
                        expected_answer=item.expected_answer,
                        rows=rows,
                    )
                    for key, value in judge_scores.items():
                        judge_values[key].append(value)

            results.append(
                EvaluationItemResult(
                    id=item.id or f"item_{index}",
                    question=item.question,
                    modality=item.modality,
                    answer=answer,
                    citations=[self._to_citation(row) for row in rows],
                    retrieved_note_ids=retrieved_note_ids,
                    retrieved_chunk_ids=retrieved_chunk_ids,
                    expected_ref_count=len(expected_refs),
                    matched_ref_count=len(matched_refs),
                    hit_at_k=hit_at_k,
                    recall_at_k=recall_at_k,
                    precision_at_k=precision_at_k,
                    reciprocal_rank=reciprocal_rank,
                    answer_overlap=answer_overlap,
                    completeness_score=completeness_score,
                    groundedness_score=groundedness_score,
                    citation_coverage=citation_coverage,
                    relevance_score=relevance_score,
                    hallucination_risk=hallucination_risk,
                    judge_scores=judge_scores,
                    judge_comment=judge_comment,
                    latency_ms=latency_ms,
                )
            )

        metrics = {
            "hit_rate_at_k": self._avg(hit_values),
            "recall_at_k": self._avg(recall_values),
            "precision_at_k": self._avg(precision_values),
            "mrr": self._avg(reciprocal_rank_values),
            "answer_overlap": self._avg(answer_overlap_values),
            "completeness_score": self._avg(completeness_values),
            "groundedness_score": self._avg(groundedness_values),
            "citation_coverage": self._avg(citation_coverage_values),
            "relevance_score": self._avg(relevance_values),
            "hallucination_risk": self._avg(hallucination_risk_values),
            "avg_latency_ms": self._avg([item.latency_ms for item in results]),
            "items_with_expected_refs": float(len(recall_values)),
            "items_with_expected_answers": float(len(answer_overlap_values)),
            "items_with_generated_answers": float(len(groundedness_values)),
        }
        for key, values in sorted(judge_values.items()):
            metrics[f"judge_{key}"] = self._avg(values)

        return EvaluationRunResponse(
            run_id=new_id("eval"),
            name=request.name or "ad-hoc evaluation",
            total=len(results),
            metrics=metrics,
            breakdown=self._breakdown_by_modality(results),
            results=results,
        )

    async def _answer(self, question: str, rows: list[dict]) -> str:
        if not rows:
            return "No relevant knowledge chunks were retrieved."
        context = "\n\n".join(
            "\n".join(
                [
                    f"Source [{index}] {row.get('title') or ''} ({row.get('source') or 'knowledge base'})",
                    f"Relevance score: {row.get('score') if row.get('score') is not None else 'N/A'}",
                    str(row.get("summary") or ""),
                    str(row.get("text") or row.get("snippet") or ""),
                ]
            )
            for index, row in enumerate(rows, start=1)
        )[:12000]
        messages = [
            {
                "role": "system",
                "content": (
                    "Answer only from the provided knowledge context. Every key factual claim must cite "
                    "the supporting source id like [1] or [2]. Prefer high-relevance sources, be concise, "
                    "and explicitly say when the context is insufficient."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ]
        return (await get_llm_provider().complete_text(messages)).strip()

    def _load_demo_items(self) -> list[EvaluationDatasetItem]:
        demo_path = Path(__file__).resolve().parents[4] / "data" / "demo_subset" / "qa" / "demo_questions.json"
        if not demo_path.exists():
            return []
        try:
            raw_items = json.loads(demo_path.read_text(encoding="utf-8"))
        except Exception:
            return []

        items: list[EvaluationDatasetItem] = []
        dataset_fields = self._dataset_item_fields()
        for index, raw in enumerate(raw_items, start=1):
            if not isinstance(raw, dict) or not raw.get("question"):
                continue
            items.append(
                EvaluationDatasetItem(
                    id=str(raw.get("id") or f"demo_{index}"),
                    question=str(raw["question"]),
                    expected_answer=raw.get("expected_answer"),
                    expected_note_ids=list(raw.get("expected_note_ids") or []),
                    expected_chunk_ids=list(raw.get("expected_chunk_ids") or []),
                    expected_sources=list(raw.get("expected_sources") or raw.get("recommended_files") or []),
                    recommended_files=list(raw.get("recommended_files") or []),
                    modality=raw.get("modality"),
                    metadata={key: value for key, value in raw.items() if key not in dataset_fields},
                )
            )
        return items

    def _dataset_item_fields(self) -> set[str]:
        return {
            "id",
            "question",
            "expected_answer",
            "expected_answer_hint",
            "expected_note_ids",
            "expected_chunk_ids",
            "expected_sources",
            "recommended_files",
            "modality",
        }

    def _expected_refs(self, item: EvaluationDatasetItem) -> set[str]:
        refs = {f"chunk:{chunk_id}" for chunk_id in item.expected_chunk_ids if chunk_id}
        refs.update(f"note:{note_id}" for note_id in item.expected_note_ids if note_id)
        refs.update(f"source:{self._normalize_source(source)}" for source in self._expected_sources(item))
        return {ref for ref in refs if not ref.endswith(":")}

    def _expected_sources(self, item: EvaluationDatasetItem) -> list[str]:
        return [source for source in [*item.expected_sources, *item.recommended_files] if source]

    def _matched_refs(self, item: EvaluationDatasetItem, rows: list[dict]) -> set[str]:
        expected_refs = self._expected_refs(item)
        matched: set[str] = set()
        for row in rows:
            for ref in self._row_refs(row, item):
                if ref in expected_refs:
                    matched.add(ref)
        return matched

    def _precision_at_k(self, item: EvaluationDatasetItem, rows: list[dict]) -> float:
        if not rows:
            return 0.0
        relevant_rows = sum(1 for row in rows if self._row_matches_expected(row, item))
        return round(relevant_rows / len(rows), 4)

    def _reciprocal_rank(self, item: EvaluationDatasetItem, rows: list[dict]) -> float:
        for rank, row in enumerate(rows, start=1):
            if self._row_matches_expected(row, item):
                return round(1.0 / rank, 4)
        return 0.0

    def _row_matches_expected(self, row: dict, item: EvaluationDatasetItem) -> bool:
        expected_refs = self._expected_refs(item)
        return any(ref in expected_refs for ref in self._row_refs(row, item))

    def _row_refs(self, row: dict, item: EvaluationDatasetItem) -> set[str]:
        refs: set[str] = set()
        chunk_id = row.get("chunk_id")
        note_id = row.get("note_id")
        if chunk_id:
            refs.add(f"chunk:{chunk_id}")
        if note_id:
            refs.add(f"note:{note_id}")

        source = str(row.get("source") or "")
        title = str(row.get("title") or "")
        normalized_source = self._normalize_source(source)
        if normalized_source:
            refs.add(f"source:{normalized_source}")
        for expected_source in self._expected_sources(item):
            normalized_expected = self._normalize_source(expected_source)
            if not normalized_expected:
                continue
            if self._source_matches(normalized_source, normalized_expected) or self._source_matches(
                self._normalize_source(title), normalized_expected
            ):
                refs.add(f"source:{normalized_expected}")
        return refs

    def _source_matches(self, candidate: str, expected: str) -> bool:
        if not candidate or not expected:
            return False
        if candidate == expected or candidate.endswith(expected) or expected.endswith(candidate):
            return True
        candidate_name = candidate.rsplit("/", 1)[-1]
        expected_name = expected.rsplit("/", 1)[-1]
        return bool(candidate_name and expected_name and candidate_name == expected_name)

    def _normalize_source(self, source: str) -> str:
        source = source.replace("\\", "/").strip().lower()
        source = re.sub(r"^.*?/data/demo_subset/", "", source)
        source = re.sub(r"^data/demo_subset/", "", source)
        return source.strip(" /")

    def _answer_overlap(self, answer: str, expected: str) -> float:
        answer_terms = set(self._terms(answer))
        expected_terms = set(self._terms(expected))
        if not expected_terms:
            return 0.0
        return round(len(answer_terms & expected_terms) / len(expected_terms), 4)

    def _groundedness_score(self, answer: str, rows: list[dict]) -> float:
        answer_terms = set(self._terms(answer))
        if not answer_terms:
            return 0.0
        context_terms = set(self._terms(self._context_text(rows)))
        if not context_terms:
            return 0.0
        return round(len(answer_terms & context_terms) / len(answer_terms), 4)

    def _relevance_score(self, answer: str, question: str, expected: str | None) -> float:
        answer_terms = set(self._terms(answer))
        target_terms = set(self._terms(question))
        if expected:
            target_terms.update(self._terms(expected))
        if not target_terms:
            return 0.0
        return round(len(answer_terms & target_terms) / len(target_terms), 4)

    def _citation_coverage(self, answer: str, rows: list[dict]) -> float:
        if not rows:
            return 0.0
        cited = {int(match) for match in re.findall(r"\[(\d+)\]", answer)}
        valid = {index for index in range(1, len(rows) + 1)}
        valid_citations = cited & valid
        if valid_citations:
            needed = self._needed_citation_count(answer, len(rows))
            return round(min(1.0, len(valid_citations) / needed), 4)

        answer_terms = set(self._terms(answer))
        represented = 0
        for row in rows:
            snippet_terms = set(self._terms(row.get("snippet") or str(row.get("text") or "")[:300]))
            if snippet_terms and len(answer_terms & snippet_terms) / max(1, len(snippet_terms)) >= 0.2:
                represented += 1
        return round(represented / len(rows), 4)

    def _needed_citation_count(self, answer: str, row_count: int) -> int:
        if row_count <= 0:
            return 1
        bullet_count = len(re.findall(r"(?m)^\s*(?:[-*]|\d+[.)])\s+", answer))
        sentence_parts = [part for part in re.split(r"[.!?。！？]+|\n+", answer) if len(self._terms(part)) >= 4]
        claim_count = max(1, bullet_count, len(sentence_parts))
        return min(row_count, max(1, min(3, claim_count)))

    async def _judge_answer(
        self,
        *,
        question: str,
        answer: str,
        expected_answer: str | None,
        rows: list[dict],
    ) -> tuple[dict[str, float], str | None]:
        try:
            data = await get_llm_provider().complete_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are an evaluator for a retrieval-augmented knowledge assistant. "
                            "Return JSON only with numeric scores from 0 to 1 for relevance, groundedness, "
                            "completeness, clarity, hallucination_risk, plus a short comment."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question:\n{question}\n\n"
                            f"Expected answer hint:\n{expected_answer or 'N/A'}\n\n"
                            f"Retrieved context:\n{self._context_text(rows)[:8000]}\n\n"
                            f"Answer:\n{answer[:4000]}"
                        ),
                    },
                ],
                schema={"type": "object"},
            )
        except Exception:
            return {}, None

        scores: dict[str, float] = {}
        for key in ("relevance", "groundedness", "completeness", "clarity", "hallucination_risk"):
            if key in data:
                scores[key] = self._clamp_score(data.get(key))
        comment = data.get("comment")
        return scores, str(comment)[:500] if comment is not None else None

    def _context_text(self, rows: list[dict]) -> str:
        parts = []
        for index, row in enumerate(rows, start=1):
            parts.append(
                "\n".join(
                    [
                        f"Source [{index}] {row.get('title') or ''}",
                        str(row.get("summary") or ""),
                        str(row.get("snippet") or ""),
                        str(row.get("text") or ""),
                    ]
                )
            )
        return "\n\n".join(parts)

    def _breakdown_by_modality(self, results: list[EvaluationItemResult]) -> dict[str, dict[str, float]]:
        grouped: dict[str, list[EvaluationItemResult]] = defaultdict(list)
        for result in results:
            grouped[result.modality or "unknown"].append(result)
        return {modality: self._metrics_for_results(items) for modality, items in sorted(grouped.items())}

    def _metrics_for_results(self, results: list[EvaluationItemResult]) -> dict[str, float]:
        return {
            "count": float(len(results)),
            "hit_rate_at_k": self._avg([item.hit_at_k for item in results]),
            "recall_at_k": self._avg([item.recall_at_k for item in results]),
            "precision_at_k": self._avg([item.precision_at_k for item in results]),
            "mrr": self._avg([item.reciprocal_rank for item in results]),
            "answer_overlap": self._avg([item.answer_overlap for item in results if item.answer_overlap is not None]),
            "completeness_score": self._avg(
                [item.completeness_score for item in results if item.completeness_score is not None]
            ),
            "groundedness_score": self._avg(
                [item.groundedness_score for item in results if item.groundedness_score is not None]
            ),
            "citation_coverage": self._avg(
                [item.citation_coverage for item in results if item.citation_coverage is not None]
            ),
            "relevance_score": self._avg([item.relevance_score for item in results if item.relevance_score is not None]),
            "hallucination_risk": self._avg(
                [item.hallucination_risk for item in results if item.hallucination_risk is not None]
            ),
            "avg_latency_ms": self._avg([item.latency_ms for item in results]),
        }

    def _terms(self, text: str) -> list[str]:
        raw_terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]+", text)]
        stop = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "into",
            "which",
            "what",
            "are",
            "was",
            "were",
            "does",
            "about",
            "source",
            "based",
            "provided",
            "knowledge",
        }
        return [term for term in raw_terms if term not in stop and len(term) > 1]

    def _to_citation(self, row: dict) -> Citation:
        return Citation(
            note_id=row["note_id"],
            chunk_id=row.get("chunk_id"),
            title=row["title"],
            snippet=row.get("snippet") or row["text"][:220],
            score=row.get("score"),
        )

    def _dedupe(self, values: list[str | None]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    def _avg(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)

    def _clamp_score(self, value: Any) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(max(0.0, min(1.0, score)), 4)


evaluation_service = EvaluationService()
