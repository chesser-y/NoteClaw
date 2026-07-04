from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import SearchMode
from noteclaw_backend.schemas.common import Citation, Scope


class WebSource(BaseModel):
    title: str
    url: str
    snippet: str = ""
    content: str | None = None
    score: float | None = None
    provider: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NanobotResearchRequest(BaseModel):
    question: str = Field(min_length=1)
    retrieval_mode: SearchMode = SearchMode.HYBRID
    scope: Scope = Field(default_factory=Scope)
    top_k: int = Field(default=5, ge=1, le=20)
    max_steps: int = Field(default=4, ge=1, le=8)
    max_sub_questions: int = Field(default=4, ge=1, le=8)
    use_web: bool = True
    web_results: int = Field(default=4, ge=1, le=10)
    fetch_web_pages: bool = True
    save_web_evidence: bool = False


class EvidenceAnchor(BaseModel):
    id: str
    source_type: str
    title: str
    snippet: str
    url: str | None = None
    note_id: str | None = None
    chunk_id: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NanobotResearchStep(BaseModel):
    step_index: int
    objective: str
    action: str
    local_citations: list[Citation] = Field(default_factory=list)
    web_sources: list[WebSource] = Field(default_factory=list)
    evidence_anchors: list[EvidenceAnchor] = Field(default_factory=list)
    observation: str


class NanobotResearchResponse(BaseModel):
    question: str
    answer: str
    plan: list[str] = Field(default_factory=list)
    steps: list[NanobotResearchStep] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    web_sources: list[WebSource] = Field(default_factory=list)
    evidence_anchors: list[EvidenceAnchor] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)
