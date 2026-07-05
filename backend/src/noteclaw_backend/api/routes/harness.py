from __future__ import annotations

from fastapi import APIRouter

from noteclaw_backend.schemas.evaluation import EvaluationRunRequest, EvaluationRunResponse
from noteclaw_backend.schemas.harness import HarnessJobRequest, HarnessJobResponse
from noteclaw_backend.services.evaluation import evaluation_service
from noteclaw_backend.services.nanobot_harness import nanobot_harness


router = APIRouter()


@router.post("/jobs", response_model=HarnessJobResponse)
async def create_harness_job(request: HarnessJobRequest) -> HarnessJobResponse:
    return await nanobot_harness.create_job(request)


@router.post("/evaluate", response_model=EvaluationRunResponse)
async def run_evaluation(request: EvaluationRunRequest) -> EvaluationRunResponse:
    return await evaluation_service.run(request)
