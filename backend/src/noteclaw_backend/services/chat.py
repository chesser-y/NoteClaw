from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional

from noteclaw_backend.domain.enums import ChatReasoningMode
from noteclaw_backend.schemas.agents import AgentWorkflowRequest, AgentWorkflowResponse
from noteclaw_backend.schemas.chat import (
    ChatAgentReview,
    ChatAgentStep,
    ChatMessageRead,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetail,
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
from noteclaw_backend.storage.chat_repository import get_chat_repository

logger = logging.getLogger(__name__)


class ChatService:
    async def create_session(self, request: ChatSessionCreate) -> ChatSessionRead:
        repo = get_chat_repository()
        scope_dict = request.scope.model_dump(mode="json") if request.scope else {}
        row = await repo.create_session(
            title=request.title or "Untitled chat",
            scope=scope_dict,
        )
        return self._session_read(row)

    async def list_sessions(
        self, limit: int = 50, *, favorites_only: bool = False
    ) -> list[ChatSessionRead]:
        repo = get_chat_repository()
        rows = await repo.list_sessions(limit=limit, favorites_only=favorites_only)
        return [self._session_read(row) for row in rows]

    async def get_session(self, session_id: str) -> ChatSessionDetail | None:
        repo = get_chat_repository()
        session = await repo.get_session(session_id)
        if session is None:
            return None
        messages = await repo.list_messages(session_id, limit=200)
        return ChatSessionDetail(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=session.message_count,
            scope=Scope(**session.scope) if session.scope else Scope(),
            messages=[self._message_read(m) for m in messages],
        )

    async def rename_session(self, session_id: str, title: str) -> ChatSessionRead | None:
        repo = get_chat_repository()
        existing = await repo.get_session(session_id)
        if existing is None:
            return None
        await repo.rename_session(session_id, title)
        session = await repo.get_session(session_id)
        return self._session_read(session) if session else None

    async def delete_session(self, session_id: str) -> bool:
        repo = get_chat_repository()
        existing = await repo.get_session(session_id)
        if existing is None:
            return False
        await repo.delete_session(session_id)
        return True

    async def set_session_favorite(self, session_id: str, value: bool) -> bool:
        repo = get_chat_repository()
        return await repo.set_session_favorite(session_id, value)

    async def send_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
    ) -> ChatMessageResponse:
        repo = get_chat_repository()
        session = await repo.get_session(session_id)
        if session is None:
            raise ValueError(f"Chat session {session_id} not found")
        session_scope = Scope(**session.scope) if session.scope else Scope()
        scope = session_scope.model_dump()
        reasoning_mode = self._resolve_reasoning_mode(request)

        await repo.append_message(
            session_id=session_id,
            role="user",
            content=request.message,
            citations=[],
            trace={
                "retrieval_mode": request.retrieval_mode.value,
                "reasoning_mode": reasoning_mode.value,
            },
        )

        response = await self._dispatch_response(
            session_id, request, session_scope, scope, reasoning_mode
        )

        trace_meta: dict[str, Any] = dict(response.trace.metadata or {})
        await self._persist_assistant_response(repo, session_id, response)

        if session.message_count == 0:
            await self._maybe_summarize_title(session_id, request.message, response.answer)

        await self._maybe_persist_low_confidence(request, response, session_id, trace_meta)

        return response

    async def send_message_streaming(
        self,
        session_id: str,
        request: ChatMessageRequest,
    ) -> AsyncGenerator[dict[str, Any], None]:
        repo = get_chat_repository()
        session = await repo.get_session(session_id)
        if session is None:
            yield {"event": "error", "data": {"detail": f"Chat session {session_id} not found"}}
            return

        session_scope = Scope(**session.scope) if session.scope else Scope()
        scope = session_scope.model_dump()
        reasoning_mode = self._resolve_reasoning_mode(request)

        await repo.append_message(
            session_id=session_id,
            role="user",
            content=request.message,
            citations=[],
            trace={
                "retrieval_mode": request.retrieval_mode.value,
                "reasoning_mode": reasoning_mode.value,
            },
        )

        yield {
            "event": "status",
            "data": {
                "stage": "received",
                "message": "Question received",
                "progress": 0.02,
                "reasoning_mode": reasoning_mode.value,
                "retrieval_mode": request.retrieval_mode.value,
                "session_id": session_id,
            },
        }

        if reasoning_mode == ChatReasoningMode.NORMAL:
            yield {
                "event": "status",
                "data": {"stage": "retrieval", "message": "Retrieving knowledge chunks", "progress": 0.18},
            }
            rows = await retrieval_service.retrieve_chunks_for_question(
                request.message,
                request.top_k,
                mode=request.retrieval_mode,
                scope=scope,
            )
            citations = self._citations_from_rows(rows)
            yield {
                "event": "status",
                "data": {
                    "stage": "retrieval",
                    "message": f"Found {len(rows)} relevant chunks",
                    "progress": 0.36,
                    "citation_count": len(citations),
                },
            }
            yield {
                "event": "status",
                "data": {
                    "stage": "generation",
                    "message": (
                        "Generating answer from retrieved knowledge"
                        if rows
                        else "No related local knowledge found; generating a general answer"
                    ),
                    "progress": 0.52,
                    "knowledge_gap": not rows,
                },
            }
            parts: list[str] = []
            messages = (
                self._answer_messages(request.message, rows)
                if rows
                else self._no_context_answer_messages(request.message)
            )
            async for delta in get_llm_provider().stream_text(messages):
                parts.append(delta)
                yield {"event": "delta", "data": {"delta": delta}}
            answer = "".join(parts).strip()
            if not answer and not rows:
                answer = self._no_context_fallback_answer(request.message)
                async for delta in self._text_chunks(answer):
                    yield {"event": "delta", "data": {"delta": delta}}
            response = self._normal_response(session_id, request, reasoning_mode, answer, citations, len(rows))
            await self._persist_assistant_response(repo, session_id, response)
            if session.message_count == 0:
                await self._maybe_summarize_title(session_id, request.message, response.answer)
            await self._maybe_persist_low_confidence(
                request,
                response,
                session_id,
                dict(response.trace.metadata or {}),
            )
            yield {"event": "final", "data": response.model_dump(mode="json")}
            return

        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def progress_cb(role: str, phase: str, extra: dict[str, Any]) -> None:
            payload: dict[str, Any] = {"role": role, "phase": phase}
            for key, value in (extra or {}).items():
                payload[key] = self._safe_json(value)
            await queue.put({"event": "step", "data": payload})
            await queue.put(
                {
                    "event": "status",
                    "data": {
                        "stage": payload.get("stage") or role,
                        "message": payload.get("message") or f"{role} {phase}",
                        "progress": payload.get("progress"),
                        "reasoning_mode": reasoning_mode.value,
                        "plan": payload.get("plan"),
                        "workflow_id": payload.get("workflow_id"),
                        "task_id": payload.get("task_id"),
                        "review": payload.get("review"),
                    },
                }
            )

        dispatch_task = asyncio.ensure_future(
            self._dispatch_response(
                session_id,
                request,
                session_scope,
                scope,
                reasoning_mode,
                progress_cb=progress_cb if reasoning_mode == ChatReasoningMode.AGENT else None,
            )
        )

        get_task: Optional[asyncio.Task] = None
        try:
            while True:
                if get_task is None:
                    get_task = asyncio.ensure_future(queue.get())
                done, _pending = await asyncio.wait(
                    {dispatch_task, get_task}, return_when=asyncio.FIRST_COMPLETED
                )
                if get_task in done:
                    try:
                        evt = get_task.result()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("progress queue error: %s", exc)
                    else:
                        if evt is not None:
                            yield evt
                    get_task = None
                if dispatch_task in done:
                    while not queue.empty():
                        evt = queue.get_nowait()
                        if evt is not None:
                            yield evt
                    break
        finally:
            if get_task is not None and not get_task.done():
                get_task.cancel()

        exc = dispatch_task.exception()
        if exc is not None:
            yield {"event": "error", "data": {"detail": str(exc) or "workflow failed"}}
            return

        response = await dispatch_task

        async for delta in self._text_chunks(response.answer):
            yield {"event": "delta", "data": {"delta": delta}}

        trace_meta: dict[str, Any] = dict(response.trace.metadata or {})
        await self._persist_assistant_response(repo, session_id, response)

        if session.message_count == 0:
            await self._maybe_summarize_title(session_id, request.message, response.answer)

        await self._maybe_persist_low_confidence(request, response, session_id, trace_meta)

        yield {"event": "final", "data": response.model_dump(mode="json")}

    def _safe_json(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            try:
                return str(value)
            except Exception:
                return None

    async def _persist_assistant_response(
        self,
        repo: Any,
        session_id: str,
        response: ChatMessageResponse,
    ) -> None:
        await repo.append_message(
            session_id=session_id,
            role="assistant",
            content=response.answer,
            citations=[c.model_dump(mode="json") for c in response.citations],
            trace=response.trace.model_dump(mode="json"),
        )

    async def _maybe_persist_low_confidence(
        self,
        request: ChatMessageRequest,
        response: ChatMessageResponse,
        session_id: str,
        trace_meta: dict[str, Any],
    ) -> None:
        review = trace_meta.get("review") if isinstance(trace_meta, dict) else None
        if not isinstance(review, dict):
            return
        confidence = review.get("confidence")
        verdict = review.get("verdict")
        is_low = (confidence is not None and float(confidence) < 0.6) or verdict not in (None, "approved")
        if not is_low:
            return
        try:
            from noteclaw_backend.storage.repositories import get_repository
            from noteclaw_backend.schemas.knowledge import NoteDetail
            from noteclaw_backend.domain.enums import NoteStatus, ContentType

            now = utc_now()
            note = NoteDetail(
                id=new_id("note"),
                title=f"Low-confidence answer · {request.message[:60]}",
                content_type=ContentType.TEXT,
                content=response.answer,
                summary=request.message[:200],
                tags=["chat", "low-confidence"],
                category="chat_review",
                source="chat_low_confidence",
                source_url=None,
                status=NoteStatus.READY,
                created_at=now,
                updated_at=now,
                metadata={
                    "review_status": "pending",
                    "session_id": session_id,
                    "confidence": confidence,
                    "verdict": verdict,
                    "risks": review.get("risks") or [],
                    "question": request.message[:400],
                },
                chunks=[],
            )
            await get_repository().create_note(note)
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to persist low-confidence answer: %s", exc)

    async def _dispatch_response(
        self,
        session_id: str,
        request: ChatMessageRequest,
        session_scope: Scope,
        scope: dict[str, Any],
        reasoning_mode: ChatReasoningMode,
        *,
        progress_cb: Callable[[str, str, dict[str, Any]], Awaitable[None]] | None = None,
    ) -> ChatMessageResponse:
        if reasoning_mode == ChatReasoningMode.AGENT:
            return await self._agent_message(
                session_id,
                request,
                session_scope,
                reasoning_mode,
                progress_cb=progress_cb,
            )

        if reasoning_mode == ChatReasoningMode.WEB:
            return await self._web_message(session_id, request, session_scope, reasoning_mode)

        if reasoning_mode == ChatReasoningMode.DEEP:
            return await self._deep_message(session_id, request, session_scope, reasoning_mode)

        return await self._normal_message(session_id, request, session_scope, reasoning_mode)

    async def _agent_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
        session_scope: Scope,
        reasoning_mode: ChatReasoningMode,
        *,
        progress_cb: Callable[[str, str, dict[str, Any]], Awaitable[None]] | None = None,
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
            progress_cb=progress_cb,
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
        if rows:
            answer = await self._answer_with_context(request.message, rows)
        else:
            answer = await self._answer_without_context(request.message)
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
                    "knowledge_gap": retrieved_chunks == 0,
                    "answer_source": "knowledge_base" if retrieved_chunks else "general_model",
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

    async def _answer_without_context(self, question: str) -> str:
        answer = (await get_llm_provider().complete_text(self._no_context_answer_messages(question))).strip()
        return answer or self._no_context_fallback_answer(question)

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

    def _no_context_answer_messages(self, question: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": (
                    "You are NoteClaw, a personal knowledge-base assistant. The current database retrieval "
                    "found no relevant stored knowledge for this question. Still answer the user using general "
                    "knowledge and reasoning. Start by explicitly stating that the current database does not "
                    "contain relevant stored knowledge for this question. Do not fabricate citations or imply "
                    "that the answer is grounded in the local knowledge base. If the answer depends on current "
                    "or uncertain facts, say what would need to be verified. Match the language of the user's question."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Database retrieval result: no relevant stored knowledge found.\n\n"
                    f"Question: {question}"
                ),
            },
        ]

    def _no_context_fallback_answer(self, question: str) -> str:
        return (
            "当前数据库中没有检索到与这个问题相关的知识。"
            "我可以先基于通用知识给出初步回答，但这个回答不引用本地知识库内容；"
            f"如需更可靠的知识库回答，请先补充相关资料。问题：{question}"
        )

    async def _maybe_summarize_title(self, session_id: str, question: str, answer: str) -> None:
        snippet = f"Q: {question[:300]}\nA: {answer[:500]}"
        messages = [
            {
                "role": "system",
                "content": (
                    "Summarize the following conversation into a short title of 6 to 10 words. "
                    "No punctuation, no quotes, no prefix like 'Title:'. Output only the title text. "
                    "Match the language of the user's question."
                ),
            },
            {"role": "user", "content": snippet},
        ]
        try:
            summary = (await get_llm_provider().complete_text(messages)).strip()
            summary = summary.splitlines()[0].strip('"“”‘’ ')[:80]
            if summary:
                await self._rename(session_id, summary)
                return
        except Exception as exc:  # noqa: BLE001
            logger.warning("session title summarization failed: %s", exc)
        fallback = question.strip().splitlines()[0][:40] or "Untitled chat"
        try:
            await self._rename(session_id, fallback)
        except Exception as exc:  # noqa: BLE001
            logger.exception("failed to set fallback session title: %s", exc)

    async def _rename(self, session_id: str, title: str) -> None:
        repo = get_chat_repository()
        await repo.rename_session(session_id, title)

    def _session_read(self, row) -> ChatSessionRead:
        return ChatSessionRead(
            id=row.id,
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
            message_count=row.message_count,
            is_favorite=getattr(row, "is_favorite", False),
        )

    def _message_read(self, row) -> ChatMessageRead:
        return ChatMessageRead(
            id=row.id,
            role=row.role,
            content=row.content,
            citations=[Citation(**c) if isinstance(c, dict) else c for c in row.citations],
            trace=row.trace or {},
            created_at=row.created_at,
        )



chat_service = ChatService()
