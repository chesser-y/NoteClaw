from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import SearchMode
from noteclaw_backend.schemas.search import SearchResult


class MultimodalQueryContext(BaseModel):
    original_query: str
    enhanced_query: str
    modality: str
    extracted_text: str | None = None
    visual_description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MultimodalSearchResponse(BaseModel):
    query: str
    mode: SearchMode
    enhanced_query: str
    modality: str
    query_context: MultimodalQueryContext
    results: list[SearchResult] = Field(default_factory=list)
