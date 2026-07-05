from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import ContentType, NoteStatus


class ChunkRead(BaseModel):
    id: str
    note_id: str
    text: str
    chunk_index: int
    score: float | None = None


class NoteListItem(BaseModel):
    id: str
    title: str
    content_type: ContentType
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    category: str | None = None
    source: str | None = None
    source_url: str | None = None
    status: NoteStatus = NoteStatus.QUEUED
    is_favorite: bool = False
    created_at: datetime
    updated_at: datetime


class NoteDetail(NoteListItem):
    content: str
    chunks: list[ChunkRead] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeListResponse(BaseModel):
    items: list[NoteListItem]
    total: int
    limit: int
    offset: int


class NoteUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    category: str | None = None


class FavoriteRequest(BaseModel):
    is_favorite: bool


class FeedbackRequest(BaseModel):
    target: str
    rating: int = Field(ge=-1, le=1)
    comment: str | None = None


class FeedbackResponse(BaseModel):
    note_id: str
    accepted: bool
    message: str
