from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import SearchMode
from noteclaw_backend.schemas.common import Citation


class EvaluationDatasetItem(BaseModel):
    id: str | None = None
    question: str = Field(min_length=1)
    expected_answer: str | None = None
    expected_note_ids: list[str] = Field(default_factory=list)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    recommended_files: list[str] = Field(default_factory=list)
    modality: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationRunRequest(BaseModel):
    name: str | None = None
    items: list[EvaluationDatasetItem] = Field(default_factory=list)
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = Field(default=5, ge=1, le=20)
    generate_answers: bool = True
    judge_answers: bool = False


class EvaluationItemResult(BaseModel):
    id: str
    question: str
    modality: str | None = None
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    retrieved_note_ids: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    expected_ref_count: int = 0
    matched_ref_count: int = 0
    hit_at_k: float
    recall_at_k: float
    precision_at_k: float
    reciprocal_rank: float
    answer_overlap: float | None = None
    completeness_score: float | None = None
    groundedness_score: float | None = None
    citation_coverage: float | None = None
    relevance_score: float | None = None
    hallucination_risk: float | None = None
    judge_scores: dict[str, float] = Field(default_factory=dict)
    judge_comment: str | None = None
    latency_ms: float


class EvaluationRunResponse(BaseModel):
    run_id: str
    name: str
    total: int
    metrics: dict[str, float]
    breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)
    results: list[EvaluationItemResult] = Field(default_factory=list)
