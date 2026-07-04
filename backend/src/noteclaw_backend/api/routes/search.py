from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from noteclaw_backend.domain.enums import SearchMode
from noteclaw_backend.schemas.multimodal import MultimodalSearchResponse
from noteclaw_backend.schemas.search import SearchRequest, SearchResponse
from noteclaw_backend.services.multimodal_query import multimodal_query_service
from noteclaw_backend.services.retrieval import retrieval_service


router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    return await retrieval_service.search(request)


@router.post("/multimodal", response_model=MultimodalSearchResponse)
async def multimodal_search(
    query: str = Form(default=""),
    mode: SearchMode = Form(default=SearchMode.HYBRID),
    limit: int = Form(default=10, ge=1, le=50),
    file: UploadFile | None = File(default=None),
) -> MultimodalSearchResponse:
    data = await file.read() if file is not None else None
    filename = file.filename if file is not None else None
    return await multimodal_query_service.search(
        query=query,
        mode=mode,
        limit=limit,
        filename=filename,
        data=data,
    )
