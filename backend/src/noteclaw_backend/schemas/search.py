from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import ContentType, SearchMode


class SearchFilters(BaseModel):
    content_types: list[ContentType] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    date_from: date | None = None
    date_to: date | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    mode: SearchMode = SearchMode.HYBRID
    filters: SearchFilters = Field(default_factory=SearchFilters)
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    note_id: str
    chunk_id: str | None = None
    title: str
    snippet: str
    score: float | None = None
    content_type: ContentType
    tags: list[str] = Field(default_factory=list)
    source: str | None = None


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    results: list[SearchResult]
