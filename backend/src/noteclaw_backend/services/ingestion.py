from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException, UploadFile

from noteclaw_backend.domain.enums import ContentType, NoteStatus, TaskStatus, TaskType
from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.schemas.ingest import IngestRequest, IngestResponse
from noteclaw_backend.schemas.knowledge import ChunkRead, NoteDetail
from noteclaw_backend.services.document_parser import ParsedDocument, parse_file_bytes
from noteclaw_backend.services.image_analysis import extract_vision_text
from noteclaw_backend.services.providers import (
    get_embedding_provider,
    get_llm_provider,
    get_vision_provider,
)
from noteclaw_backend.services.task_service import task_service
from noteclaw_backend.services.text_processing import chunk_text, enrich_content
from noteclaw_backend.storage.faiss_store import get_vector_store
from noteclaw_backend.storage.repositories import get_repository
from noteclaw_backend.settings import get_settings


class IngestionService:
    async def ingest_text(self, request: IngestRequest) -> IngestResponse:
        note_id = new_id("note")
        task = task_service.create_task(TaskType.INGESTION, "Ingestion started.")
        task_service.mark_running(task.id, "Analyzing and indexing content")
        try:
            parsed = ParsedDocument(
                content_type=request.content_type,
                content=request.content,
                title=request.title,
                metadata={**request.metadata, "source_url": request.source_url},
            )
            await self._ingest_parsed(
                note_id=note_id,
                parsed=parsed,
                source=request.source,
                source_url=request.source_url,
            )
            task_service.mark_succeeded(
                task.id,
                message="Ingestion completed",
                result={"note_id": note_id},
            )
            return IngestResponse(
                note_id=note_id,
                task_id=task.id,
                status=TaskStatus.SUCCEEDED,
                message="Ingestion completed",
            )
        except Exception as exc:
            task_service.mark_failed(task.id, str(exc))
            raise

    async def ingest_file(
        self,
        file: UploadFile,
        content_type: ContentType | None = None,
        source: str | None = None,
    ) -> IngestResponse:
        note_id = new_id("note")
        task = task_service.create_task(TaskType.INGESTION, f"File ingestion started for {file.filename}.")
        task_service.mark_running(task.id, "Reading uploaded file")
        filename = file.filename or "upload.bin"
        data = await file.read()
        if not data:
            task_service.mark_failed(task.id, "Uploaded file is empty")
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        try:
            saved_path = self._save_upload(note_id, filename, data)
            parsed = parse_file_bytes(
                filename=filename,
                data=data,
                content_type=content_type,
                saved_path=saved_path,
            )
            if parsed.content_type == ContentType.IMAGE:
                try:
                    vision = await get_vision_provider().understand_image(
                        str(saved_path),
                        parsed.metadata.get("ocr_text"),
                    )
                    description = extract_vision_text(vision)
                    if description and description not in parsed.content:
                        parsed = ParsedDocument(
                            content_type=parsed.content_type,
                            content=f"{parsed.content}\n\nImage visual description:\n{description}",
                            title=parsed.title,
                            metadata={**parsed.metadata, "vision": vision},
                        )
                except Exception:
                    task_service.update_task(
                        task.id,
                        status=TaskStatus.RUNNING,
                        progress=task.progress,
                        message="OCR successful, vision understanding skipped due error",
                    )

            await self._ingest_parsed(
                note_id=note_id,
                parsed=parsed,
                source=source or "upload",
                source_url=None,
            )
            task_service.mark_succeeded(
                task.id,
                message="File ingestion completed",
                result={"note_id": note_id, "filename": filename},
            )
            return IngestResponse(
                note_id=note_id,
                task_id=task.id,
                status=TaskStatus.SUCCEEDED,
                message="File ingestion completed",
            )
        except Exception as exc:
            task_service.mark_failed(task.id, str(exc))
            raise

    async def _ingest_parsed(
        self,
        *,
        note_id: str,
        parsed: ParsedDocument,
        source: str | None,
        source_url: str | None,
    ) -> None:
        content = parsed.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="No text could be extracted from the input")
        metadata = await enrich_content(
            content=content,
            content_type=parsed.content_type,
            title=parsed.title,
            llm=get_llm_provider(),
        )
        chunk_texts = chunk_text(content)
        if not chunk_texts:
            chunk_texts = [content]
        now = utc_now()
        chunks = [
            ChunkRead(
                id=new_id("chunk"),
                note_id=note_id,
                text=chunk,
                chunk_index=index,
            )
            for index, chunk in enumerate(chunk_texts)
        ]
        note = NoteDetail(
            id=note_id,
            title=metadata.title,
            content_type=parsed.content_type,
            content=content,
            summary=metadata.summary,
            tags=metadata.tags,
            category=metadata.category,
            source=source or "manual",
            source_url=source_url,
            status=NoteStatus.READY,
            chunks=chunks,
            metadata=parsed.metadata,
            created_at=now,
            updated_at=now,
        )
        chunk_ids = [chunk.id for chunk in chunks]
        embeddings = await get_embedding_provider().embed_texts([chunk.text for chunk in chunks])
        repository = get_repository()
        vector_store = get_vector_store()
        await repository.create_note(note)
        try:
            row_ids = vector_store.add(embeddings, chunk_ids)
            await repository.upsert_vector_mappings(
                chunk_ids,
                row_ids,
                get_settings().embedding_model or "hashing-local",
            )
        except Exception:
            vector_store.mark_deleted(chunk_ids)
            await repository.delete_note(note_id)
            raise

    def _save_upload(self, note_id: str, filename: str, data: bytes) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name) or "upload.bin"
        upload_dir = get_settings().storage_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"{note_id}_{safe_name}"
        path.write_bytes(data)
        return path


ingestion_service = IngestionService()
