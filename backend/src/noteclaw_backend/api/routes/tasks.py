from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from noteclaw_backend.domain.enums import TaskStatus
from noteclaw_backend.schemas.tasks import TaskListResponse, TaskRead
from noteclaw_backend.services.task_service import task_service


router = APIRouter()


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: str) -> TaskRead:
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: TaskStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TaskListResponse:
    items, total = task_service.list_tasks(status=status, limit=limit, offset=offset)
    return TaskListResponse(items=items, total=total, limit=limit, offset=offset)
