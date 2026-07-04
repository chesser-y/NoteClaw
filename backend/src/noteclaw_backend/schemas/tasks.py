from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import TaskStatus, TaskType, WorkItemStatus


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


class TaskWorkItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    task_type: TaskType | None = None
    status: WorkItemStatus = WorkItemStatus.QUEUED
    description: str | None = Field(default=None, max_length=600)
    tags: list[str] = Field(default_factory=list)
    material_count: int = Field(default=0, ge=0)
    current_stage: str | None = Field(default=None, max_length=220)
    result_url: str | None = None
    result_label: str | None = Field(default=None, max_length=120)
    requires_confirmation: bool = False
    source_task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskWorkItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    task_type: TaskType | None = None
    status: WorkItemStatus | None = None
    description: str | None = Field(default=None, max_length=600)
    tags: list[str] | None = None
    material_count: int | None = Field(default=None, ge=0)
    current_stage: str | None = Field(default=None, max_length=220)
    result_url: str | None = None
    result_label: str | None = Field(default=None, max_length=120)
    requires_confirmation: bool | None = None
    metadata: dict[str, Any] | None = None


class TaskWorkItemRead(BaseModel):
    id: str
    title: str
    task_type: TaskType | None = None
    status: WorkItemStatus
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    material_count: int = 0
    current_stage: str | None = None
    result_url: str | None = None
    result_label: str | None = None
    requires_confirmation: bool = False
    source_task_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class TaskWorkItemListResponse(BaseModel):
    items: list[TaskWorkItemRead]
    total: int
    limit: int
    offset: int


class TaskKanbanColumn(BaseModel):
    id: WorkItemStatus
    title: str
    items: list[TaskWorkItemRead] = Field(default_factory=list)


class TaskKanbanBoardResponse(BaseModel):
    columns: list[TaskKanbanColumn]
    total: int
