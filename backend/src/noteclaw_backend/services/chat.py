from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from noteclaw_backend.domain.enums import ChatReasoningMode
from noteclaw_backend.schemas.agents import AgentWorkflowRequest, AgentWorkflowResponse
from noteclaw_backend.schemas.chat import (
    ChatAgentReview,
    ChatAgentStep,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionRead,
    ChatTrace,
)
from noteclaw_backend.schemas.common import Citation, Scope, new_id, utc_now
from noteclaw_backend.schemas.nanobot import NanobotResearchRequest
from noteclaw_backend.schemas.reasoning import ReasoningRequest
from noteclaw_backend.services.multi_agent import multi_agent_workflow_service
from noteclaw_backend.services.providers import get_llm_provider
from noteclaw_backend.services.nanobot_research import nanobot_research_service
from noteclaw_backend.services.reasoning import reasoning_service
from noteclaw_backend.services.retrieval import retrieval_service
from noteclaw_backend.settings import get_settings


class ChatService:
    def __init__(self) -> None:
        self._session_scopes: dict[str, Scope] = {}

    async def create_session(self, request: ChatSessionCreate) -> ChatSessionRead:
        session_id = new_id("chat")
        self._session_scopes[session_id] = request.scope
        return ChatSessionRead(
            id=session_id,
            title=request.title or "Untitled chat",
            created_at=utc_now(),
        )

    async def send_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
    ) -> ChatMessageResponse:
        session_scope = self._session_scopes.get(session_id, Scope())
        reasoning_mode = self._resolve_reasoning_mode(request)

        if reasoning_mode == ChatReasoningMode.AGENT:
            return await self._agent_message(session_id, request, session_scope, reasoning_mode)

        if reasoning_mode == ChatReasoningMode.WEB:
            return await self._web_message(session_id, request, session_scope, reasoning_mode)

        if reasoning_mode == ChatReasoningMode.DEEP:
            return await self._deep_message(session_id, request, session_scope, reasoning_mode)

        return await self._normal_message(session_id, request, session_scope, reasoning_mode)

    async def stream_message_events(
        self,
        session_id: str,
        request: ChatMessageRequest,
    ) -> AsyncIterator[str]:
        try:
            async for event in self._stream_message_events(session_id, request):
                yield event
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield self._sse("error", {"message": str(exc) or exc.__class__.__name__})

    async def _stream_message_events(
        self,
        session_id: str,
        request: ChatMessageRequest,
    ) -> AsyncIterator[str]:
        session_scope = self._session_scopes.get(session_id, Scope())
        reasoning_mode = self._resolve_reasoning_mode(request)

        yield self._sse(
            "status",
            {
                "stage": "received",
                "message": "Question received",
                "progress": 0.02,
                "reasoning_mode": reasoning_mode.value,
            },
        )

        if reasoning_mode == ChatReasoningMode.NORMAL:
            async for event in self._stream_normal_message(session_id, request, session_scope, reasoning_mode):
                yield event
            return

        if reasoning_mode == ChatReasoningMode.AGENT:
            async for event in self._stream_agent_message(session_id, request, session_scope, reasoning_mode):
                yield event
            return

        if reasoning_mode == ChatReasoningMode.WEB:
            yield self._sse(
                "status",
                {
                    "stage": "web",
                    "message": "Planning local and web research",
                    "progress": 0.18,
                    "reasoning_mode": reasoning_mode.value,
                },
            )
            response = await self._web_message(session_id, request, session_scope, reasoning_mode)
            async for event in self._stream_response(response):
                yield event
            return

        yield self._sse(
            "status",
            {
                "stage": "deep",
                "message": "Decomposing question and retrieving evidence",
                "progress": 0.18,
                "reasoning_mode": reasoning_mode.value,
            },
        )
        response = await self._deep_message(session_id, request, session_scope, reasoning_mode)
        async for event in self._stream_response(response):
            yield event

    async def _stream_normal_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
        session_scope: Scope,
        reasoning_mode: ChatReasoningMode,
    ) -> AsyncIterator[str]:
        yield self._sse(
            "status",
            {"stage": "retrieval", "message": "Retrieving knowledge chunks", "progress": 0.18},
        )
        rows = await retrieval_service.retrieve_chunks_for_question(
            request.message,
            request.top_k,
            mode=request.retrieval_mode,
            scope=session_scope.model_dump(),
        )
        citations = self._citations_from_rows(rows)
        yield self._sse(
            "status",
            {
                "stage": "retrieval",
                "message": f"Found {len(rows)} relevant chunks",
                "progress": 0.36,
                "citation_count": len(citations),
            },
        )

        if not rows:
            answer = "I could not find relevant content in the current knowledge base. Add or broaden knowledge first, then ask again."
            response = self._normal_response(session_id, request, reasoning_mode, answer, citations, len(rows))
            async for event in self._stream_response(response):
                yield event
            return

        yield self._sse(
            "status",
            {"stage": "generation", "message": "Generating answer", "progress": 0.52},
        )
        answer_parts: list[str] = []
        async for delta in get_llm_provider().stream_text(self._answer_messages(request.message, rows)):
            answer_parts.append(delta)
            yield self._sse("delta", {"delta": delta})

        answer = "".join(answer_parts).strip()
        response = self._normal_response(session_id, request, reasoning_mode, answer, citations, len(rows))
        yield self._sse("final", response)

    async def _stream_agent_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
        session_scope: Scope,
        reasoning_mode: ChatReasoningMode,
    ) -> AsyncIterator[str]:
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

        async def on_progress(payload: dict[str, Any]) -> None:
            await queue.put(("status", payload))

        async def run_agent() -> None:
            try:
                response = await self._agent_message(
                    session_id,
                    request,
                    session_scope,
                    reasoning_mode,
                    on_progress=on_progress,
                )
                await queue.put(("response", response))
            except Exception as exc:
                await queue.put(("error", exc))

        task = asyncio.create_task(run_agent())
        try:
            while True:
                kind, payload = await queue.get()
                if kind == "status":
                    yield self._sse("status", payload)
                    continue
                if kind == "response":
                    async for event in self._stream_response(payload):
                        yield event
                    break
                if kind == "error":
                    raise payload
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def _agent_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
        session_scope: Scope,
        reasoning_mode: ChatReasoningMode,
        *,
        on_progress: Any | None = None,
    ) -> ChatMessageResponse:
        workflow = await multi_agent_workflow_service.run(
            AgentWorkflowRequest(
                goal=request.message,
                retrieval_mode=request.retrieval_mode,
                scope=session_scope,
                top_k=min(request.top_k, 20),
                max_steps=request.max_reasoning_steps,
                use_web=request.use_web_research,
                web_results=request.web_results,
                fetch_web_pages=request.fetch_web_pages,
                output_format="answer",
                create_work_item=True,
                create_timeline_item=True,
            ),
            on_progress=on_progress,
        )
        return self._agent_response(session_id, request, reasoning_mode, workflow)

    async def _web_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
        session_scope: Scope,
        reasoning_mode: ChatReasoningMode,
    ) -> ChatMessageResponse:
        research = await nanobot_research_service.research(
            NanobotResearchRequest(
                question=request.message,
                retrieval_mode=request.retrieval_mode,
                scope=session_scope,
                top_k=min(request.top_k, 20),
                max_steps=request.max_reasoning_steps,
                max_sub_questions=request.max_reasoning_steps,
                use_web=True,
                web_results=request.web_results,
                fetch_web_pages=request.fetch_web_pages,
                save_web_evidence=False,
            )
        )
        return ChatMessageResponse(
            message_id=new_id("msg"),
            answer=research.answer,
            citations=research.citations,
            trace=ChatTrace(
                retrieval_mode=request.retrieval_mode,
                used_nanobot=True,
                model=get_settings().llm_model or "fallback-local",
                plan=research.plan,
                metadata={
                    "session_id": session_id,
                    "reasoning_mode": reasoning_mode.value,
                    "nanobot_trace": research.trace,
                    "plan": research.plan,
                    "web_sources": [
                        {
                            "title": source.title,
                            "url": source.url,
                            "provider": source.provider,
                            "snippet": source.snippet[:240],
                        }
                        for source in research.web_sources[:8]
                    ],
                    "web_source_count": len(research.web_sources),
                    "evidence_anchor_count": len(research.evidence_anchors),
                },
            ),
        )

    async def _deep_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
        session_scope: Scope,
        reasoning_mode: ChatReasoningMode,
    ) -> ChatMessageResponse:
        reasoning = await reasoning_service.reason(
            ReasoningRequest(
                question=request.message,
                retrieval_mode=request.retrieval_mode,
                top_k=request.top_k,
                max_sub_questions=request.max_reasoning_steps,
                scope=session_scope,
            )
        )
        return ChatMessageResponse(
            message_id=new_id("msg"),
            answer=reasoning.answer,
            citations=reasoning.citations,
            trace=ChatTrace(
                retrieval_mode=request.retrieval_mode,
                used_nanobot=True,
                model=get_settings().llm_model or "fallback-local",
                plan=reasoning.sub_questions,
                metadata={
                    "session_id": session_id,
                    "reasoning_mode": reasoning_mode.value,
                    "reasoning_trace": reasoning.trace,
                    "sub_questions": reasoning.sub_questions,
                },
            ),
        )

    async def _normal_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
        session_scope: Scope,
        reasoning_mode: ChatReasoningMode,
    ) -> ChatMessageResponse:
        rows = await retrieval_service.retrieve_chunks_for_question(
            request.message,
            request.top_k,
            mode=request.retrieval_mode,
            scope=session_scope.model_dump(),
        )
        citations = self._citations_from_rows(rows)
        if not rows:
            answer = "I could not find relevant content in the current knowledge base. Add or broaden knowledge first, then ask again."
        else:
            answer = await self._answer_with_context(request.message, rows)
        return self._normal_response(session_id, request, reasoning_mode, answer, citations, len(rows))

    def _normal_response(
        self,
        session_id: str,
        request: ChatMessageRequest,
        reasoning_mode: ChatReasoningMode,
        answer: str,
        citations: list[Citation],
        retrieved_chunks: int,
    ) -> ChatMessageResponse:
        return ChatMessageResponse(
            message_id=new_id("msg"),
            answer=answer,
            citations=citations,
            trace=ChatTrace(
                retrieval_mode=request.retrieval_mode,
                used_nanobot=False,
                model=get_settings().llm_model or "fallback-local",
                metadata={
                    "session_id": session_id,
                    "reasoning_mode": reasoning_mode.value,
                    "retrieved_chunks": retrieved_chunks,
                },
            ),
        )

    def _agent_response(
        self,
        session_id: str,
        request: ChatMessageRequest,
        reasoning_mode: ChatReasoningMode,
        workflow: AgentWorkflowResponse,
    ) -> ChatMessageResponse:
        review = ChatAgentReview(
            verdict=workflow.review.verdict,
            confidence=workflow.review.confidence,
            risks=workflow.review.risks,
            needs_user_confirmation=workflow.review.requires_confirmation,
        )
        steps = [
            ChatAgentStep(
                role=step.role,
                title=step.title,
                output=step.output_summary,
                citations=workflow.citations[:6] if step.role.value == "researcher" else [],
            )
            for step in workflow.steps
        ]
        return ChatMessageResponse(
            message_id=new_id("msg"),
            answer=workflow.final_answer,
            citations=workflow.citations,
            trace=ChatTrace(
                retrieval_mode=request.retrieval_mode,
                used_nanobot=True,
                model=get_settings().llm_model or "fallback-local",
                steps=steps,
                plan=workflow.plan,
                review=review,
                workflow_id=workflow.workflow_id,
                metadata={
                    "session_id": session_id,
                    "reasoning_mode": reasoning_mode.value,
                    "workflow_id": workflow.workflow_id,
                    "task_id": workflow.task_id,
                    "work_item_id": workflow.work_item_id,
                    "timeline_item_id": workflow.timeline_item_id,
                    "plan": workflow.plan,
                    "steps": [step.model_dump(mode="json") for step in workflow.steps],
                    "review": workflow.review.model_dump(mode="json"),
                    "use_web": workflow.trace.get("use_web", False),
                    "web_source_count": len(workflow.web_sources),
                    "evidence_anchor_count": len(workflow.evidence_anchors),
                },
            ),
        )

    async def _stream_response(self, response: ChatMessageResponse) -> AsyncIterator[str]:
        async for chunk in self._text_chunks(response.answer):
            yield self._sse("delta", {"delta": chunk})
        yield self._sse("final", response)

    async def _text_chunks(self, text: str, *, size: int = 80) -> AsyncIterator[str]:
        for index in range(0, len(text), size):
            yield text[index : index + size]
            await asyncio.sleep(0)

    def _citations_from_rows(self, rows: list[dict]) -> list[Citation]:
        return [
            Citation(
                note_id=row["note_id"],
                chunk_id=row.get("chunk_id"),
                title=row["title"],
                snippet=row.get("snippet") or row["text"][:220],
                score=row.get("score"),
            )
            for row in rows
        ]

    def _sse(self, event: str, data: Any) -> str:
        if hasattr(data, "model_dump"):
            data = data.model_dump(mode="json")
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return f"event: {event}\ndata: {payload}\n\n"

    def _resolve_reasoning_mode(self, request: ChatMessageRequest) -> ChatReasoningMode:
        if request.reasoning_mode != ChatReasoningMode.NORMAL:
            return request.reasoning_mode
        if request.use_web_research:
            return ChatReasoningMode.WEB
        if request.use_nanobot_reasoning:
            return ChatReasoningMode.DEEP
        return ChatReasoningMode.NORMAL

    async def _answer_with_context(self, question: str, rows: list[dict]) -> str:
        return (await get_llm_provider().complete_text(self._answer_messages(question, rows))).strip()

    def _answer_messages(self, question: str, rows: list[dict]) -> list[dict]:
        context_parts = []
        for index, row in enumerate(rows, start=1):
            context_parts.append(
                "\n".join(
                    [
                        f"Source [{index}] {row['title']} ({row.get('source') or 'knowledge base'})",
                        f"Relevance score: {row.get('score') if row.get('score') is not None else 'N/A'}",
                        str(row.get("summary") or ""),
                        row["text"],
                    ]
                )
            )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are NoteClaw, a personal knowledge-base assistant. Answer only from the provided context. "
                    "Every key factual claim must cite the source id that supports it, using [1], [2]. "
                    "Prefer the highest-relevance sources. If evidence is weak or missing, say what is uncertain instead of guessing. "
                    "Keep the answer clear, concise, and directly responsive to the question."
                ),
            },
            {
                "role": "user",
                "content": "Context:\n" + "\n\n".join(context_parts) + f"\n\nQuestion: {question}",
            },
        ]
        return messages



chat_service = ChatService()
