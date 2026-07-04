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
        recall_values: list[float] = []
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

            has_expected_refs = bool(item.expected_note_ids or item.expected_chunk_ids)
            recall_at_k = self._recall_at_k(item, rows) if has_expected_refs else 0.0
            reciprocal_rank = self._reciprocal_rank(item, rows) if has_expected_refs else 0.0
            if has_expected_refs:
                recall_values.append(recall_at_k)
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
                    recall_at_k=recall_at_k,
                    reciprocal_rank=reciprocal_rank,
                    answer_overlap=answer_overlap,
                    latency_ms=latency_ms,
                )
            )

        metrics = {
            "recall_at_k": self._avg(recall_values),
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
                )
            )
        return items

    def _recall_at_k(self, item: EvaluationDatasetItem, rows: list[dict]) -> float:
        expected_chunks = set(item.expected_chunk_ids)
        expected_notes = set(item.expected_note_ids)
        expected_total = len(expected_chunks) + len(expected_notes)
        if expected_total == 0:
            return 0.0
        hit_chunks = {row.get("chunk_id") for row in rows if row.get("chunk_id") in expected_chunks}
        hit_notes = {row["note_id"] for row in rows if row["note_id"] in expected_notes}
        return round((len(hit_chunks) + len(hit_notes)) / expected_total, 4)

    def _reciprocal_rank(self, item: EvaluationDatasetItem, rows: list[dict]) -> float:
        expected_chunks = set(item.expected_chunk_ids)
        expected_notes = set(item.expected_note_ids)
        for rank, row in enumerate(rows, start=1):
            if row.get("chunk_id") in expected_chunks or row["note_id"] in expected_notes:
                return round(1.0 / rank, 4)
        return 0.0

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
