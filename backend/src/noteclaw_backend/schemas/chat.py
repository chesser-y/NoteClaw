from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import AgentRole, ChatReasoningMode, SearchMode
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
    reasoning_mode: ChatReasoningMode = ChatReasoningMode.NORMAL
    use_nanobot_reasoning: bool = False
    use_web_research: bool = False
    top_k: int = Field(default=8, ge=1, le=30)
    max_reasoning_steps: int = Field(default=4, ge=1, le=8)
    web_results: int = Field(default=4, ge=1, le=10)
    fetch_web_pages: bool = True


class ChatAgentStep(BaseModel):
    role: AgentRole
    title: str
    output: str | None = None
    duration_ms: int | None = None
    citations: list[Citation] = Field(default_factory=list)


class ChatAgentReview(BaseModel):
    verdict: str | None = None
    confidence: float | None = None
    risks: list[str] = Field(default_factory=list)
    needs_user_confirmation: bool = False


class ChatTrace(BaseModel):
    retrieval_mode: SearchMode
    used_nanobot: bool
    model: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    steps: list[ChatAgentStep] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    review: ChatAgentReview | None = None
    workflow_id: str | None = None


class ChatMessageResponse(BaseModel):
    message_id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    trace: ChatTrace
