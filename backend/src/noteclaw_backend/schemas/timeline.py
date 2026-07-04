from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from noteclaw_backend.domain.enums import TimelineItemStatus, TimelineKind


class TimelineItemCreate(BaseModel):
    kind: TimelineKind
    title: str = Field(min_length=1, max_length=180)
    lane: str | None = Field(default=None, max_length=120)
    start_date: date
    end_date: date | None = None
    progress: float = Field(default=0, ge=0, le=1)
    status: TimelineItemStatus = TimelineItemStatus.PLANNED
    milestone_date: date | None = None
    dependency_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_note_ids: list[str] = Field(default_factory=list)
    source_task_ids: list[str] = Field(default_factory=list)
    current_stage: str | None = Field(default=None, max_length=240)
    result_url: str | None = None
    result_label: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimelineItemUpdate(BaseModel):
    kind: TimelineKind | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    lane: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    progress: float | None = Field(default=None, ge=0, le=1)
    status: TimelineItemStatus | None = None
    milestone_date: date | None = None
    dependency_ids: list[str] | None = None
    tags: list[str] | None = None
    source_note_ids: list[str] | None = None
    source_task_ids: list[str] | None = None
    current_stage: str | None = Field(default=None, max_length=240)
    result_url: str | None = None
    result_label: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] | None = None


class TimelineItemRead(BaseModel):
    id: str
    kind: TimelineKind
    title: str
    lane: str
    start_date: date
    end_date: date | None = None
    progress: float = Field(ge=0, le=1)
    status: TimelineItemStatus
    milestone_date: date | None = None
    dependency_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_note_ids: list[str] = Field(default_factory=list)
    source_task_ids: list[str] = Field(default_factory=list)
    current_stage: str | None = None
    result_url: str | None = None
    result_label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class TimelineItemListResponse(BaseModel):
    items: list[TimelineItemRead]
    total: int
    limit: int
    offset: int


class TimelineMonth(BaseModel):
    id: str
    label: str
    year: int
    month: int
    start_date: date


class TimelineLane(BaseModel):
    id: str
    title: str
    items: list[TimelineItemRead] = Field(default_factory=list)


class TimelineMilestone(BaseModel):
    id: str
    item_id: str
    title: str
    date: date
    lane: str


class TimelineDependency(BaseModel):
    source_id: str
    target_id: str
    source_title: str
    target_title: str


class TimelineBoardResponse(BaseModel):
    kind: TimelineKind
    title: str
    months: list[TimelineMonth]
    lanes: list[TimelineLane]
    milestones: list[TimelineMilestone] = Field(default_factory=list)
    dependencies: list[TimelineDependency] = Field(default_factory=list)
    total: int
