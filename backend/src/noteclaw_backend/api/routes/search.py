from __future__ import annotations

from fastapi import APIRouter

from noteclaw_backend.schemas.search import SearchRequest, SearchResponse
from noteclaw_backend.services.retrieval import retrieval_service


router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    return await retrieval_service.search(request)
