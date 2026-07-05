from __future__ import annotations

from noteclaw_backend.domain.enums import ChatReasoningMode
from noteclaw_backend.schemas.agents import AgentWorkflowRequest
from noteclaw_backend.schemas.chat import (
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
        scope = session_scope.model_dump()
        reasoning_mode = self._resolve_reasoning_mode(request)

        if reasoning_mode == ChatReasoningMode.AGENT:
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
                )
            )
            return ChatMessageResponse(
                message_id=new_id("msg"),
                answer=workflow.final_answer,
                citations=workflow.citations,
                trace=ChatTrace(
                    retrieval_mode=request.retrieval_mode,
                    used_nanobot=True,
                    model=get_settings().llm_model or "fallback-local",
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

        if reasoning_mode == ChatReasoningMode.WEB:
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

        if reasoning_mode == ChatReasoningMode.DEEP:
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
                    metadata={
                        "session_id": session_id,
                        "reasoning_mode": reasoning_mode.value,
                        "reasoning_trace": reasoning.trace,
                        "sub_questions": reasoning.sub_questions,
                    },
                ),
            )

        rows = await retrieval_service.retrieve_chunks_for_question(
            request.message,
            request.top_k,
            mode=request.retrieval_mode,
            scope=scope,
        )
        citations = [
            Citation(
                note_id=row["note_id"],
                chunk_id=row.get("chunk_id"),
                title=row["title"],
                snippet=row.get("snippet") or row["text"][:220],
                score=row.get("score"),
            )
            for row in rows
        ]
        if not rows:
            answer = "I could not find relevant content in the current knowledge base. Add or broaden knowledge first, then ask again."
        else:
            answer = await self._answer_with_context(request.message, rows)
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
                    "retrieved_chunks": len(rows),
                },
            ),
        )

    def _resolve_reasoning_mode(self, request: ChatMessageRequest) -> ChatReasoningMode:
        if request.reasoning_mode != ChatReasoningMode.NORMAL:
            return request.reasoning_mode
        if request.use_web_research:
            return ChatReasoningMode.WEB
        if request.use_nanobot_reasoning:
            return ChatReasoningMode.DEEP
        return ChatReasoningMode.NORMAL

    async def _answer_with_context(self, question: str, rows: list[dict]) -> str:
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
        return (await get_llm_provider().complete_text(messages)).strip()



chat_service = ChatService()
