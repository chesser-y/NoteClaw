from __future__ import annotations

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import SearchMode
from noteclaw_backend.schemas.common import Citation


class EvaluationDatasetItem(BaseModel):
    id: str | None = None
    question: str = Field(min_length=1)
    expected_answer: str | None = None
    expected_note_ids: list[str] = Field(default_factory=list)
    expected_chunk_ids: list[str] = Field(default_factory=list)


class EvaluationRunRequest(BaseModel):
    name: str | None = None
    items: list[EvaluationDatasetItem] = Field(default_factory=list)
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = Field(default=5, ge=1, le=20)
    generate_answers: bool = True


class EvaluationItemResult(BaseModel):
    id: str
    question: str
    answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    retrieved_note_ids: list[str] = Field(default_factory=list)
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    recall_at_k: float
    reciprocal_rank: float
    answer_overlap: float | None = None
    latency_ms: float


class EvaluationRunResponse(BaseModel):
    run_id: str
    name: str
    total: int
    metrics: dict[str, float]
    results: list[EvaluationItemResult] = Field(default_factory=list)
