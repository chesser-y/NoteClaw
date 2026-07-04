from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import ContentType, TaskStatus


class IngestRequest(BaseModel):
    content_type: ContentType
    content: str = Field(min_length=1)
    title: str | None = None
    source: str | None = "manual"
    source_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    note_id: str
    task_id: str | None = None
    status: TaskStatus
    message: str
