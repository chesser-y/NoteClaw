from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse

from noteclaw_backend.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionPatch,
    ChatSessionRead,
)
from noteclaw_backend.schemas.reasoning import ReasoningRequest, ReasoningResponse
from noteclaw_backend.services.chat import chat_service
from noteclaw_backend.services.reasoning import reasoning_service


router = APIRouter()


@router.post("/sessions", response_model=ChatSessionRead)
async def create_chat_session(request: ChatSessionCreate) -> ChatSessionRead:
    return await chat_service.create_session(request)


@router.get("/sessions", response_model=list[ChatSessionRead])
async def list_chat_sessions(
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ChatSessionRead]:
    return await chat_service.list_sessions(limit=limit)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(session_id: str) -> ChatSessionDetail:
    session = await chat_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.patch("/sessions/{session_id}", response_model=ChatSessionRead)
async def rename_chat_session(
    session_id: str,
    request: ChatSessionPatch,
) -> ChatSessionRead:
    if not request.title or not request.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    session = await chat_service.rename_session(session_id, request.title.strip()[:120])
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str) -> dict[str, bool]:
    deleted = await chat_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"deleted": True}


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: str,
    request: ChatMessageRequest,
) -> ChatMessageResponse:
    try:
        return await chat_service.send_message(session_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/messages/stream")
async def stream_chat_message(
    session_id: str,
    request: ChatMessageRequest,
) -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[bytes, None]:
        try:
            async for evt in chat_service.send_message_streaming(session_id, request):
                event_name = evt.get("event", "message")
                data = evt.get("data", {})
                yield _format_sse(event_name, data)
        except ValueError as exc:
            yield _format_sse("error", {"detail": str(exc)})
        except Exception as exc:  # noqa: BLE001
            yield _format_sse("error", {"detail": str(exc) or "stream failed"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _format_sse(event: str, data: Any) -> bytes:
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event}\ndata: {payload}\n\n".encode("utf-8")


@router.post("/reason", response_model=ReasoningResponse)
async def reason_over_knowledge(request: ReasoningRequest) -> ReasoningResponse:
    return await reasoning_service.reason(request)
