from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import TaskStatus


class HarnessJobRequest(BaseModel):
    job_type: str
    instruction: str = Field(min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)


class HarnessJobResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
