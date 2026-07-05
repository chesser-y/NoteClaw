from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import GenerationType, TaskStatus
from noteclaw_backend.schemas.common import Citation, Scope


class GenerationOptions(BaseModel):
    slide_count: int | None = Field(default=None, ge=1, le=20)
    theme: str | None = "dark_academic"
    include_generated_images: bool = False
    output_format: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class GenerationRequest(BaseModel):
    generation_type: GenerationType
    prompt: str = Field(min_length=1)
    scope: Scope = Field(default_factory=Scope)
    options: GenerationOptions = Field(default_factory=GenerationOptions)


class GenerationTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


class GenerationPreviewResponse(BaseModel):
    generation_type: GenerationType
    content: dict[str, Any] | str
    citations: list[Citation] = Field(default_factory=list)
    note_id: str | None = None
    artifact_url: str | None = None
    download_url: str | None = None
    document_extension: str | None = None
