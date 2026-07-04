from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import AgentRole, SearchMode
from noteclaw_backend.schemas.common import Citation, Scope
from noteclaw_backend.schemas.nanobot import EvidenceAnchor, WebSource


class AgentWorkflowRequest(BaseModel):
    goal: str = Field(min_length=1)
    scope: Scope = Field(default_factory=Scope)
    retrieval_mode: SearchMode = SearchMode.HYBRID
    top_k: int = Field(default=6, ge=1, le=20)
    max_steps: int = Field(default=4, ge=1, le=8)
    use_web: bool = False
    web_results: int = Field(default=4, ge=1, le=10)
    fetch_web_pages: bool = True
    output_format: str = Field(default="answer", max_length=40)
    create_work_item: bool = True
    create_timeline_item: bool = True


class AgentStep(BaseModel):
    index: int
    role: AgentRole
    title: str
    action: str
    status: str = "succeeded"
    input_summary: str | None = None
    output_summary: str | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)


class AgentReview(BaseModel):
    verdict: str
    requires_confirmation: bool = False
    confidence: float = Field(default=0.5, ge=0, le=1)
    risks: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class AgentWorkflowResponse(BaseModel):
    workflow_id: str
    task_id: str | None = None
    work_item_id: str | None = None
    timeline_item_id: str | None = None
    goal: str
    final_answer: str
    steps: list[AgentStep] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    evidence_anchors: list[EvidenceAnchor] = Field(default_factory=list)
    web_sources: list[WebSource] = Field(default_factory=list)
    review: AgentReview
    trace: dict[str, Any] = Field(default_factory=dict)


class AgentWorkflowListResponse(BaseModel):
    items: list[AgentWorkflowResponse]
    total: int
    limit: int
    offset: int
