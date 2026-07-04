from __future__ import annotations

import json
import re
from pathlib import Path
from time import perf_counter

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

        for index, item in enumerate(items, start=1):
            started = perf_counter()
            rows = await retrieval_service.retrieve_chunks_for_question(
                item.question,
                request.top_k,
                mode=request.mode,
            )
            answer = await self._answer(item.question, rows) if request.generate_answers else None
            latency_ms = round((perf_counter() - started) * 1000, 2)
            retrieved_note_ids = self._dedupe([row["note_id"] for row in rows])
            retrieved_chunk_ids = self._dedupe([row.get("chunk_id") for row in rows if row.get("chunk_id")])

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
            if answer and item.expected_answer:
                answer_overlap = self._answer_overlap(answer, item.expected_answer)
                answer_overlap_values.append(answer_overlap)

            results.append(
                EvaluationItemResult(
                    id=item.id or f"item_{index}",
                    question=item.question,
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
                    latency_ms=latency_ms,
                )
            )

        metrics = {
            "hit_rate_at_k": self._avg(hit_values),
            "recall_at_k": self._avg(recall_values),
            "precision_at_k": self._avg(precision_values),
            "mrr": self._avg(reciprocal_rank_values),
            "answer_overlap": self._avg(answer_overlap_values),
            "avg_latency_ms": self._avg([item.latency_ms for item in results]),
            "items_with_expected_refs": float(len(recall_values)),
            "items_with_expected_answers": float(len(answer_overlap_values)),
        }
        return EvaluationRunResponse(
            run_id=new_id("eval"),
            name=request.name or "ad-hoc evaluation",
            total=len(results),
            metrics=metrics,
            results=results,
        )

    async def _answer(self, question: str, rows: list[dict]) -> str:
        if not rows:
            return "No relevant knowledge chunks were retrieved."
        context = "\n\n".join(
            f"Source [{index}] {row['title']}\n{row['text']}"
            for index, row in enumerate(rows, start=1)
        )[:12000]
        messages = [
            {
                "role": "system",
                "content": "Answer from the provided knowledge context. Keep it concise and cite sources like [1].",
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
            raw_items = json.loads(demo_path.read_text())
        except Exception:
            return []
        items: list[EvaluationDatasetItem] = []
        for index, raw in enumerate(raw_items, start=1):
            if not isinstance(raw, dict) or not raw.get("question"):
                continue
            items.append(
                EvaluationDatasetItem(
                    id=str(raw.get("id") or f"demo_{index}"),
                    question=str(raw["question"]),
                    expected_answer=raw.get("expected_answer") or raw.get("expected_answer_hint"),
                    expected_note_ids=list(raw.get("expected_note_ids") or []),
                    expected_chunk_ids=list(raw.get("expected_chunk_ids") or []),
                    expected_sources=list(raw.get("expected_sources") or raw.get("recommended_files") or []),
                    recommended_files=list(raw.get("recommended_files") or []),
                )
            )
        return items

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

    def _terms(self, text: str) -> list[str]:
        return [term.lower() for term in re.findall(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]+", text)]

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


evaluation_service = EvaluationService()
