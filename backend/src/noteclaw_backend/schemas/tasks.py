from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import TaskStatus, TaskType


class TaskRead(BaseModel):
    id: str
    type: TaskType
    status: TaskStatus
    progress: float = Field(ge=0, le=1)
    message: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int
