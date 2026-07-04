from __future__ import annotations

from fastapi import UploadFile

from noteclaw_backend.domain.enums import ContentType, TaskStatus, TaskType
from noteclaw_backend.schemas.common import new_id
from noteclaw_backend.schemas.ingest import IngestRequest, IngestResponse
from noteclaw_backend.services.task_service import task_service


class IngestionService:
    async def ingest_text(self, request: IngestRequest) -> IngestResponse:
        note_id = new_id("note")
        task = task_service.create_task(
            TaskType.INGESTION,
            "Ingestion queued. SQLite, embedding, and FAISS implementation pending.",
        )
        return IngestResponse(
            note_id=note_id,
            task_id=task.id,
            status=TaskStatus.QUEUED,
            message="Ingestion accepted",
        )

    async def ingest_file(
        self,
        file: UploadFile,
        content_type: ContentType | None = None,
        source: str | None = None,
    ) -> IngestResponse:
        note_id = new_id("note")
        task = task_service.create_task(
            TaskType.INGESTION,
            f"File ingestion queued for {file.filename}. OCR/vision pipeline pending.",
        )
        return IngestResponse(
            note_id=note_id,
            task_id=task.id,
            status=TaskStatus.QUEUED,
            message="File ingestion accepted",
        )


ingestion_service = IngestionService()
