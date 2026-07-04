from __future__ import annotations

from fastapi import APIRouter

from noteclaw_backend.schemas.generation import (
    GenerationPreviewResponse,
    GenerationRequest,
    GenerationTaskResponse,
)
from noteclaw_backend.services.generation import generation_service


router = APIRouter()


@router.post("", response_model=GenerationTaskResponse)
async def generate(request: GenerationRequest) -> GenerationTaskResponse:
    return await generation_service.create_generation_task(request)


@router.post("/preview", response_model=GenerationPreviewResponse)
async def preview_generation(request: GenerationRequest) -> GenerationPreviewResponse:
    return await generation_service.preview(request)
