from __future__ import annotations

import re

from noteclaw_backend.schemas.common import Citation
from noteclaw_backend.schemas.reasoning import ReasoningRequest, ReasoningResponse, ReasoningStep
from noteclaw_backend.services.providers import get_llm_provider
from noteclaw_backend.services.retrieval import retrieval_service
from noteclaw_backend.settings import get_settings


class ReasoningService:
    async def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        sub_questions = await self._decompose_question(
            request.question,
            max_sub_questions=request.max_sub_questions,
        )
        all_rows: list[dict] = []
        steps: list[ReasoningStep] = []

        for sub_question in sub_questions:
            rows = await retrieval_service.retrieve_chunks_for_question(
                sub_question,
                request.top_k,
                mode=request.retrieval_mode,
                scope=request.scope.model_dump(),
            )
            all_rows.extend(rows)
            steps.append(
                ReasoningStep(
                    sub_question=sub_question,
                    citations=[self._to_citation(row) for row in rows],
                    evidence_summary=self._evidence_summary(rows),
                )
            )

        citations = self._dedupe_citations([citation for step in steps for citation in step.citations])
        answer = await self._synthesize_answer(
            question=request.question,
            sub_questions=sub_questions,
            rows=self._dedupe_rows(all_rows),
        )
        return ReasoningResponse(
            question=request.question,
            answer=answer,
            sub_questions=sub_questions,
            steps=steps,
            citations=citations,
            trace={
                "strategy": "decompose_retrieve_synthesize",
                "retrieval_mode": request.retrieval_mode.value,
                "sub_question_count": len(sub_questions),
                "evidence_chunks": len(citations),
                "model": get_settings().llm_model or "fallback-local",
            },
        )

    async def _decompose_question(self, question: str, *, max_sub_questions: int) -> list[str]:
        data = await get_llm_provider().complete_json(
            [
                {
                    "role": "system",
                    "content": (
                        "Decompose a complex knowledge-base question into up to N focused sub_questions. "
                        "Return JSON only: {\"sub_questions\": [\"...\"]}. Keep the original language."
                    ),
                },
                {
                    "role": "user",
                    "content": f"N={max_sub_questions}\nQuestion: {question}",
                },
            ],
            schema={"type": "object", "properties": {"sub_questions": {"type": "array"}}},
        )
        candidates = data.get("sub_questions") or data.get("questions") or []
        if isinstance(candidates, list):
            cleaned = self._clean_questions([str(item) for item in candidates], max_sub_questions)
            if cleaned:
                return cleaned
        return self._heuristic_decompose(question, max_sub_questions)

    def _heuristic_decompose(self, question: str, max_sub_questions: int) -> list[str]:
        stripped = question.strip()
        if max_sub_questions <= 1:
            return [stripped]

        split_pattern = (
            r"\s+(?:and|then|plus|versus|vs\.?|compare|contrast)\s+"
            r"|[;；。]\s*"
            r"|(?:以及|并且|同时|另外|此外|对比|比较)"
        )
        parts = [part.strip(" ,，?？") for part in re.split(split_pattern, stripped, flags=re.IGNORECASE)]
        questions = self._clean_questions(parts, max_sub_questions)
        if len(questions) >= 2:
            return questions
        return [stripped]

    def _clean_questions(self, questions: list[str], limit: int) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for question in questions:
            normalized = re.sub(r"\s+", " ", question).strip()
            if len(normalized) < 4:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(normalized)
            if len(cleaned) >= limit:
                break
        return cleaned

    async def _synthesize_answer(self, *, question: str, sub_questions: list[str], rows: list[dict]) -> str:
        if not rows:
            return (
                "I could not find enough relevant content in the current knowledge base to answer this. "
                "Try adding related documents or broadening the scope."
            )
        context_parts = []
        for index, row in enumerate(rows[:16], start=1):
            context_parts.append(
                f"Source [{index}] {row['title']} ({row.get('source') or 'knowledge base'})\n{row['text']}"
            )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are NoteClaw's cross-document reasoning engine. Use only the provided evidence. "
                    "Synthesize across sources, point out uncertainty, and cite evidence as [1], [2]."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Sub-questions:\n"
                    + "\n".join(f"- {item}" for item in sub_questions)
                    + "\n\nContext:\n"
                    + "\n\n".join(context_parts)
                    + f"\n\nQuestion: {question}"
                ),
            },
        ]
        return (await get_llm_provider().complete_text(messages)).strip()

    def _evidence_summary(self, rows: list[dict]) -> str:
        if not rows:
            return "No matching evidence found for this sub-question."
        summaries = []
        for index, row in enumerate(rows[:3], start=1):
            snippet = re.sub(r"\s+", " ", row.get("snippet") or row["text"][:220]).strip()
            summaries.append(f"[{index}] {row['title']}: {snippet}")
        return "\n".join(summaries)

    def _to_citation(self, row: dict) -> Citation:
        return Citation(
            note_id=row["note_id"],
            chunk_id=row.get("chunk_id"),
            title=row["title"],
            snippet=row.get("snippet") or row["text"][:220],
            score=row.get("score"),
        )

    def _dedupe_citations(self, citations: list[Citation]) -> list[Citation]:
        seen: set[str] = set()
        deduped: list[Citation] = []
        for citation in citations:
            key = citation.chunk_id or citation.note_id
            if key in seen:
                continue
            seen.add(key)
            deduped.append(citation)
        return deduped

    def _dedupe_rows(self, rows: list[dict]) -> list[dict]:
        seen: set[str] = set()
        deduped: list[dict] = []
        for row in rows:
            key = row.get("chunk_id") or row["note_id"]
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        return deduped


reasoning_service = ReasoningService()
