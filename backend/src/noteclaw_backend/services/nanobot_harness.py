from __future__ import annotations

from noteclaw_backend.domain.enums import TaskStatus, TaskType
from noteclaw_backend.schemas.harness import HarnessJobRequest, HarnessJobResponse
from noteclaw_backend.services.task_service import task_service


class NanobotHarness:
    """Reserved integration point for nanobot-backed tool execution."""

    async def create_job(self, request: HarnessJobRequest) -> HarnessJobResponse:
        task = task_service.create_task(
            TaskType.HARNESS,
            (
                f"Nanobot harness job '{request.job_type}' queued. "
                "Final invocation strategy pending."
            ),
            work_item_title=request.instruction[:120] or f"Nanobot {request.job_type} task",
            tags=["agent", request.job_type],
            material_count=len(request.inputs),
            current_stage="Queued for agent execution",
            requires_confirmation=True,
            metadata={"job_type": request.job_type},
        )
        return HarnessJobResponse(
            task_id=task.id,
            status=TaskStatus.QUEUED,
            message="Harness job accepted",
        )

    async def run_job(self, job_type: str, instruction: str, inputs: dict) -> dict:
        return {
            "job_type": job_type,
            "instruction": instruction,
            "inputs": inputs,
            "status": "not_implemented",
        }


nanobot_harness = NanobotHarness()
