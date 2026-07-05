from __future__ import annotations

from typing import Any

from noteclaw_backend.domain.enums import TaskStatus, TaskType, WorkItemStatus
from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.schemas.tasks import (
    TaskKanbanBoardResponse,
    TaskKanbanColumn,
    TaskRead,
    TaskWorkItemCreate,
    TaskWorkItemRead,
    TaskWorkItemUpdate,
)


class TaskService:
    """In-memory task registry plus user-facing Kanban work items."""

    _BOARD_ORDER = (
        WorkItemStatus.QUEUED,
        WorkItemStatus.IN_PROGRESS,
        WorkItemStatus.NEED_REVIEW,
        WorkItemStatus.DONE,
    )
    _BOARD_TITLES = {
        WorkItemStatus.QUEUED: "Queued",
        WorkItemStatus.IN_PROGRESS: "In progress",
        WorkItemStatus.NEED_REVIEW: "Need review",
        WorkItemStatus.DONE: "Done",
    }

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRead] = {}
        self._work_items: dict[str, TaskWorkItemRead] = {}
        self._task_to_work_item: dict[str, str] = {}

    def create_task(
        self,
        task_type: TaskType,
        message: str,
        *,
        work_item_title: str | None = None,
        tags: list[str] | None = None,
        material_count: int = 0,
        current_stage: str | None = None,
        requires_confirmation: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> TaskRead:
        now = utc_now()
        task = TaskRead(
            id=new_id("task"),
            type=task_type,
            status=TaskStatus.QUEUED,
            progress=0,
            message=message,
            created_at=now,
            updated_at=now,
        )
        self._tasks[task.id] = task
        if work_item_title:
            work_item = self.create_work_item(
                TaskWorkItemCreate(
                    title=work_item_title,
                    task_type=task_type,
                    status=WorkItemStatus.QUEUED,
                    tags=tags or [],
                    material_count=material_count,
                    current_stage=current_stage or message,
                    requires_confirmation=requires_confirmation,
                    source_task_id=task.id,
                    metadata=metadata or {},
                )
            )
            self._task_to_work_item[task.id] = work_item.id
        return task

    def update_task(
        self,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        progress: float | None = None,
        message: str | None = None,
        result: dict | None = None,
        error: str | None = None,
    ) -> TaskRead | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None

        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = max(0.0, min(1.0, float(progress)))
        if message is not None:
            task.message = message
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        task.updated_at = utc_now()
        self._sync_work_item_from_task(task, result=result, error=error)
        return task

    def mark_running(self, task_id: str, message: str | None = None) -> TaskRead | None:
        return self.update_task(
            task_id,
            status=TaskStatus.RUNNING,
            progress=0.1,
            message=message or "Running",
        )

    def mark_succeeded(
        self,
        task_id: str,
        *,
        message: str | None = None,
        result: dict | None = None,
    ) -> TaskRead | None:
        return self.update_task(
            task_id,
            status=TaskStatus.SUCCEEDED,
            progress=1,
            message=message or "Succeeded",
            result=result,
        )

    def mark_failed(self, task_id: str, error: str) -> TaskRead | None:
        return self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            progress=1,
            message="Failed",
            error=error,
        )

    def get_task(self, task_id: str) -> TaskRead | None:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TaskRead], int]:
        tasks = sorted(self._tasks.values(), key=lambda task: task.updated_at, reverse=True)
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        return tasks[offset : offset + limit], len(tasks)

    def create_work_item(self, request: TaskWorkItemCreate) -> TaskWorkItemRead:
        now = utc_now()
        item = TaskWorkItemRead(
            id=new_id("work"),
            title=request.title,
            task_type=request.task_type,
            status=request.status,
            description=request.description,
            tags=self._clean_tags(request.tags),
            material_count=request.material_count,
            current_stage=request.current_stage,
            result_url=request.result_url,
            result_label=request.result_label,
            requires_confirmation=request.requires_confirmation,
            source_task_id=request.source_task_id,
            metadata=request.metadata,
            created_at=now,
            updated_at=now,
        )
        self._work_items[item.id] = item
        if item.source_task_id:
            self._task_to_work_item[item.source_task_id] = item.id
        return item

    def get_work_item(self, work_item_id: str) -> TaskWorkItemRead | None:
        return self._work_items.get(work_item_id)

    def update_work_item(
        self,
        work_item_id: str,
        request: TaskWorkItemUpdate,
    ) -> TaskWorkItemRead | None:
        item = self._work_items.get(work_item_id)
        if item is None:
            return None

        updates = request.model_dump(exclude_unset=True)
        if "tags" in updates and updates["tags"] is not None:
            updates["tags"] = self._clean_tags(updates["tags"])
        if "metadata" in updates and updates["metadata"] is not None:
            updates["metadata"] = {**item.metadata, **updates["metadata"]}
        updates["updated_at"] = utc_now()
        updated = item.model_copy(update=updates)
        self._work_items[work_item_id] = updated
        return updated

    def list_work_items(
        self,
        status: WorkItemStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TaskWorkItemRead], int]:
        items = sorted(self._work_items.values(), key=lambda item: item.updated_at, reverse=True)
        if status is not None:
            items = [item for item in items if item.status == status]
        return items[offset : offset + limit], len(items)

    def kanban_board(self, *, include_examples: bool = False) -> TaskKanbanBoardResponse:
        items = list(self._work_items.values())
        if include_examples:
            items.extend(self._example_work_items())
        items = sorted(items, key=lambda item: item.updated_at, reverse=True)
        columns = []
        for status in self._BOARD_ORDER:
            columns.append(
                TaskKanbanColumn(
                    id=status,
                    title=self._BOARD_TITLES[status],
                    items=[item for item in items if item.status == status],
                )
            )
        return TaskKanbanBoardResponse(columns=columns, total=len(items))

    def _sync_work_item_from_task(
        self,
        task: TaskRead,
        *,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        work_item_id = self._task_to_work_item.get(task.id)
        if not work_item_id:
            return
        item = self._work_items.get(work_item_id)
        if item is None:
            return

        status = item.status
        current_stage = task.message or item.current_stage
        result_url = item.result_url
        result_label = item.result_label
        if task.status == TaskStatus.RUNNING:
            status = WorkItemStatus.IN_PROGRESS
        elif task.status == TaskStatus.SUCCEEDED:
            status = WorkItemStatus.NEED_REVIEW if item.requires_confirmation else WorkItemStatus.DONE
            result_entry = self._extract_result_entry(result or task.result or {})
            result_url = result_entry.get("url") or result_url
            result_label = result_entry.get("label") or result_label
        elif task.status == TaskStatus.FAILED:
            status = WorkItemStatus.NEED_REVIEW
            current_stage = f"Failed: {error or task.error or 'review required'}"
        elif task.status == TaskStatus.CANCELLED:
            status = WorkItemStatus.NEED_REVIEW
            current_stage = "Cancelled · review required"

        self._work_items[work_item_id] = item.model_copy(
            update={
                "status": status,
                "current_stage": current_stage,
                "result_url": result_url,
                "result_label": result_label,
                "updated_at": utc_now(),
            }
        )

    def _extract_result_entry(self, result: dict[str, Any]) -> dict[str, str]:
        candidates = [result]
        content = result.get("content")
        if isinstance(content, dict):
            candidates.append(content)
        for candidate in candidates:
            artifact = candidate.get("artifact") if isinstance(candidate, dict) else None
            if isinstance(artifact, dict) and artifact.get("url"):
                label = artifact.get("name") or artifact.get("type") or "Open result"
                return {"url": str(artifact["url"]), "label": str(label)}
            url = candidate.get("url") if isinstance(candidate, dict) else None
            if isinstance(url, str) and url:
                return {"url": url, "label": str(candidate.get("name") or candidate.get("type") or "Open result")}
        return {}

    def _clean_tags(self, tags: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for tag in tags:
            value = str(tag).strip()[:40]
            if not value or value.lower() in seen:
                continue
            seen.add(value.lower())
            cleaned.append(value)
        return cleaned[:8]

    def _example_work_items(self) -> list[TaskWorkItemRead]:
        now = utc_now()
        examples = [
            TaskWorkItemRead(
                id="example_benchmark",
                title="整理 NoteClaw benchmark 资料",
                task_type=TaskType.HARNESS,
                status=WorkItemStatus.IN_PROGRESS,
                tags=["benchmark", "research"],
                material_count=6,
                current_stage="Reading 6 sources · Drafting comparison",
                requires_confirmation=False,
                metadata={"example": True},
                created_at=now,
                updated_at=now,
            ),
            TaskWorkItemRead(
                id="example_ppt_outline",
                title="生成科研实习 PPT 大纲",
                task_type=TaskType.GENERATION,
                status=WorkItemStatus.NEED_REVIEW,
                tags=["ppt", "notes"],
                material_count=4,
                current_stage="Using 4 notes · Waiting for review",
                result_url="/api/generate/preview",
                result_label="Open PPT outline",
                requires_confirmation=True,
                metadata={"example": True},
                created_at=now,
                updated_at=now,
            ),
            TaskWorkItemRead(
                id="example_pdf_methods",
                title="分析 3 篇 PDF 的方法差异",
                task_type=TaskType.HARNESS,
                status=WorkItemStatus.QUEUED,
                tags=["pdf", "evidence"],
                material_count=3,
                current_stage="Extracting evidence · 12 chunks found",
                requires_confirmation=False,
                metadata={"example": True},
                created_at=now,
                updated_at=now,
            ),
        ]
        return examples


task_service = TaskService()
