from __future__ import annotations

from noteclaw_backend.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionRead,
    ChatTrace,
)
from noteclaw_backend.schemas.common import Citation, Scope, new_id, utc_now
from noteclaw_backend.services.providers import get_llm_provider
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
        scope = self._session_scopes.get(session_id, Scope()).model_dump()
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
            if request.use_nanobot_reasoning:
                answer += "\n\nNote: Nanobot cross-document reasoning is reserved; this response used the normal RAG path."
        return ChatMessageResponse(
            message_id=new_id("msg"),
            answer=answer,
            citations=citations,
            trace=ChatTrace(
                retrieval_mode=request.retrieval_mode,
                used_nanobot=False,
                model=get_settings().llm_model or "fallback-local",
                metadata={"session_id": session_id, "retrieved_chunks": len(rows)},
            ),
        )

    async def _answer_with_context(self, question: str, rows: list[dict]) -> str:
        context_parts = []
        for index, row in enumerate(rows, start=1):
            context_parts.append(
                f"Source [{index}] {row['title']} ({row.get('source') or 'knowledge base'})\n{row['text']}"
            )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are NoteClaw, a personal knowledge-base assistant. Answer only from the provided context. "
                    "If the context is insufficient, say so. Keep the answer clear and cite sources like [1], [2] when useful."
                ),
            },
            {
                "role": "user",
                "content": "Context:\n" + "\n\n".join(context_parts) + f"\n\nQuestion: {question}",
            },
        ]
        return (await get_llm_provider().complete_text(messages)).strip()


chat_service = ChatService()
