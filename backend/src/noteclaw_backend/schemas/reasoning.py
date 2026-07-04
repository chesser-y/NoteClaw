from __future__ import annotations

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import SearchMode
from noteclaw_backend.schemas.common import Citation, Scope


class ReasoningRequest(BaseModel):
    question: str = Field(min_length=1)
    retrieval_mode: SearchMode = SearchMode.HYBRID
    top_k: int = Field(default=5, ge=1, le=20)
    max_sub_questions: int = Field(default=3, ge=1, le=5)
    scope: Scope = Field(default_factory=Scope)


class ReasoningStep(BaseModel):
    sub_question: str
    citations: list[Citation] = Field(default_factory=list)
    evidence_summary: str


class ReasoningResponse(BaseModel):
    question: str
    answer: str
    sub_questions: list[str] = Field(default_factory=list)
    steps: list[ReasoningStep] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)
