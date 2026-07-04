from __future__ import annotations

from noteclaw_backend.domain.enums import TaskStatus, TaskType
from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.schemas.tasks import TaskRead


class TaskService:
    """Temporary in-memory task registry for API contract development."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRead] = {}

    def create_task(self, task_type: TaskType, message: str) -> TaskRead:
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

        updated = task.model_copy(
            update={
                "status": status or task.status,
                "progress": task.progress if progress is None else progress,
                "message": task.message if message is None else message,
                "result": task.result if result is None else result,
                "error": task.error if error is None else error,
                "updated_at": utc_now(),
            }
        )
        self._tasks[task_id] = updated
        return updated

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
        return task

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TaskRead], int]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        return tasks[offset : offset + limit], len(tasks)


task_service = TaskService()
