from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import SearchMode
from noteclaw_backend.schemas.common import Citation, Scope


class ChatSessionCreate(BaseModel):
    title: str | None = None
    scope: Scope = Field(default_factory=Scope)


class ChatSessionRead(BaseModel):
    id: str
    title: str
    created_at: datetime


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    retrieval_mode: SearchMode = SearchMode.HYBRID
    use_nanobot_reasoning: bool = False
    top_k: int = Field(default=8, ge=1, le=30)


class ChatTrace(BaseModel):
    retrieval_mode: SearchMode
    used_nanobot: bool
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatMessageResponse(BaseModel):
    message_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    trace: ChatTrace
