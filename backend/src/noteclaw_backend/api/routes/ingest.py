from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from noteclaw_backend.domain.enums import ContentType
from noteclaw_backend.schemas.ingest import IngestRequest, IngestResponse
from noteclaw_backend.services.ingestion import ingestion_service


router = APIRouter()


@router.post("", response_model=IngestResponse)
async def ingest(request: IngestRequest) -> IngestResponse:
    return await ingestion_service.ingest_text(request)


@router.post("/files", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    content_type: ContentType | None = Form(default=None),
    source: str | None = Form(default=None),
) -> IngestResponse:
    return await ingestion_service.ingest_file(file, content_type, source)
