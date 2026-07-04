from __future__ import annotations

from fastapi import APIRouter

from noteclaw_backend.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionRead,
)
from noteclaw_backend.services.chat import chat_service


router = APIRouter()


@router.post("/sessions", response_model=ChatSessionRead)
async def create_chat_session(request: ChatSessionCreate) -> ChatSessionRead:
    return await chat_service.create_session(request)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: str,
    request: ChatMessageRequest,
) -> ChatMessageResponse:
    return await chat_service.send_message(session_id, request)
