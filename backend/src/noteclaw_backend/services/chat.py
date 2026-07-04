from __future__ import annotations

from noteclaw_backend.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionRead,
    ChatTrace,
)
from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.services.retrieval import retrieval_service


class ChatService:
    async def create_session(self, request: ChatSessionCreate) -> ChatSessionRead:
        return ChatSessionRead(
            id=new_id("chat"),
            title=request.title or "Untitled chat",
            created_at=utc_now(),
        )

    async def send_message(
        self,
        session_id: str,
        request: ChatMessageRequest,
    ) -> ChatMessageResponse:
        citations = await retrieval_service.retrieve_for_question(
            request.message,
            request.top_k,
            scope=None,
        )
        if request.use_nanobot_reasoning:
            answer = (
                "Nanobot cross-document reasoning is reserved behind NanobotHarness. "
                "This response confirms the frontend-backend contract."
            )
        else:
            answer = (
                "RAG answer generation is pending provider integration. "
                "The backend will retrieve SQLite/FAISS context, call the configured "
                "OpenAI-compatible LLM, and return citations."
            )
        return ChatMessageResponse(
            message_id=new_id("msg"),
            answer=answer,
            citations=citations,
            trace=ChatTrace(
                retrieval_mode=request.retrieval_mode,
                used_nanobot=request.use_nanobot_reasoning,
                model=None,
                metadata={"session_id": session_id},
            ),
        )


chat_service = ChatService()
