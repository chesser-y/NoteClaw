from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from noteclaw_backend.domain.enums import TaskStatus, WorkItemStatus
from noteclaw_backend.schemas.tasks import (
    TaskKanbanBoardResponse,
    TaskListResponse,
    TaskRead,
    TaskWorkItemCreate,
    TaskWorkItemListResponse,
    TaskWorkItemRead,
    TaskWorkItemUpdate,
)
from noteclaw_backend.services.task_service import task_service


router = APIRouter()


@router.get("/board", response_model=TaskKanbanBoardResponse)
async def get_task_board(include_examples: bool = False) -> TaskKanbanBoardResponse:
    return task_service.kanban_board(include_examples=include_examples)


@router.post("/work-items", response_model=TaskWorkItemRead)
async def create_work_item(request: TaskWorkItemCreate) -> TaskWorkItemRead:
    return task_service.create_work_item(request)


@router.get("/work-items", response_model=TaskWorkItemListResponse)
async def list_work_items(
    status: WorkItemStatus | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TaskWorkItemListResponse:
    items, total = task_service.list_work_items(status=status, limit=limit, offset=offset)
    return TaskWorkItemListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/work-items/{work_item_id}", response_model=TaskWorkItemRead)
async def get_work_item(work_item_id: str) -> TaskWorkItemRead:
    item = task_service.get_work_item(work_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    return item


@router.patch("/work-items/{work_item_id}", response_model=TaskWorkItemRead)
async def update_work_item(work_item_id: str, request: TaskWorkItemUpdate) -> TaskWorkItemRead:
    item = task_service.update_work_item(work_item_id, request)
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    return item


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: TaskStatus | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TaskListResponse:
    items, total = task_service.list_tasks(status=status, limit=limit, offset=offset)
    return TaskListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: str) -> TaskRead:
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
