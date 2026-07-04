from __future__ import annotations

from fastapi import APIRouter

from noteclaw_backend.schemas.nanobot import NanobotResearchRequest, NanobotResearchResponse
from noteclaw_backend.services.nanobot_research import nanobot_research_service


router = APIRouter()


@router.post("/research", response_model=NanobotResearchResponse)
async def run_nanobot_research(request: NanobotResearchRequest) -> NanobotResearchResponse:
    return await nanobot_research_service.research(request)
