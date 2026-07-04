from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApiMessage(BaseModel):
    message: str


class Scope(BaseModel):
    note_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    note_id: str
    chunk_id: str | None = None
    title: str
    snippet: str
    score: float | None = None


class Page(BaseModel):
    total: int
    limit: int
    offset: int


class Artifact(BaseModel):
    id: str
    type: str
    name: str
    url: str
    metadata: dict[str, Any] = Field(default_factory=dict)
