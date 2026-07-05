from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import ChatReasoningMode, SearchMode
from noteclaw_backend.schemas.common import Citation, Scope


class ChatSessionCreate(BaseModel):
    title: str | None = None
    scope: Scope = Field(default_factory=Scope)


class ChatSessionRead(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime | None = None
    message_count: int = 0
    is_favorite: bool = False


class ChatMessageRead(BaseModel):
    id: str
    role: str
    content: str
    citations: list[Citation] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ChatSessionDetail(ChatSessionRead):
    scope: Scope = Field(default_factory=Scope)
    messages: list[ChatMessageRead] = Field(default_factory=list)


class ChatSessionPatch(BaseModel):
    title: str | None = None


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1)
    retrieval_mode: SearchMode = SearchMode.HYBRID
    reasoning_mode: ChatReasoningMode = ChatReasoningMode.NORMAL
    use_nanobot_reasoning: bool = False
    use_web_research: bool = False
    top_k: int = Field(default=8, ge=1, le=30)
    max_reasoning_steps: int = Field(default=4, ge=1, le=8)
    web_results: int = Field(default=4, ge=1, le=10)
    fetch_web_pages: bool = True


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
