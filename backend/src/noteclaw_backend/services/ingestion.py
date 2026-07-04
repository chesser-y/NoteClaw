from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from noteclaw_backend.domain.enums import ContentType, NoteStatus, TaskStatus, TaskType
from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.schemas.ingest import IngestRequest, IngestResponse
from noteclaw_backend.services.providers import NoteClawOpenAICompat
from noteclaw_backend.settings import get_settings
from noteclaw_backend.services.task_service import task_service
from noteclaw_backend.storage.faiss_store import FaissVectorStore
from noteclaw_backend.storage.sqlite import SQLiteStore


class IngestionService:
    async def ingest_text(self, request: IngestRequest) -> IngestResponse:
        note_id = new_id("note")
        task = task_service.create_task(
            TaskType.INGESTION,
            "Text ingestion is not implemented yet; use /ingest/files for image flow.",
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
            f"Processing file {file.filename or 'unknown'}",
        )

        try:
            task_service.update_task(
                task.id,
                status=TaskStatus.RUNNING,
                progress=0.05,
                message="Saving uploaded file",
            )

            provider = self._build_provider()
            settings = get_settings()

            storage_root = settings.storage_dir / "attachments" / note_id
            storage_root.mkdir(parents=True, exist_ok=True)
            filename = file.filename or f"upload_{new_id('file')}"
            saved_path = storage_root / filename

            with saved_path.open("wb") as target:
                data = await file.read()
                target.write(data)

            task_service.update_task(
                task.id,
                progress=0.15,
                message="Running OCR",
            )
            try:
                ocr_text = await provider.extract_image_text(str(saved_path))
            except Exception:
                ocr_text = ""

            task_service.update_task(
                task.id,
                progress=0.45,
                message="Running vision understanding",
            )

            try:
                understanding = await provider.understand_image(
                    str(saved_path),
                    ocr_text=ocr_text,
                    enable_ocr=False,
                )
            except Exception:
                understanding = {
                    "summary": ocr_text[:240] if ocr_text else "",
                    "tags": ["image", "ocr_failed"],
                    "raw": "Vision understanding failed; fallback to OCR text.",
                }
            summary = self._extract_summary(understanding)
            tags = self._extract_tags(understanding)
            category = self._extract_category(understanding)

            task_service.update_task(
                task.id,
                progress=0.65,
                message="Persisting metadata to SQLite",
            )

            chunks = self._split_text_for_ingest(ocr_text or "")
            if not chunks:
                chunks = [""]

            created_at = utc_now().isoformat()
            note_content = ocr_text or ""
            metadata = {
                "task_id": task.id,
                "source_filename": filename,
                "stored_path": str(saved_path.as_posix()),
                "understanding": understanding,
                "vision_prompt": "image understanding from provider",
            }

            self._ensure_schema(settings)
            self._upsert_note_and_chunks(
                settings=settings,
                note_id=note_id,
                content_type=content_type or ContentType.IMAGE,
                title=self._infer_title(file.filename, source),
                content=note_content,
                summary=summary,
                tags=tags,
                category=category,
                source=source or "upload",
                source_url=None,
                status=NoteStatus.READY,
                created_at=created_at,
                updated_at=created_at,
                metadata=metadata,
                chunks=chunks,
                source_file_path=str(saved_path.as_posix()),
            )

            task_service.update_task(
                task.id,
                progress=0.85,
                message="Generating embeddings and updating FAISS index",
            )
            vectors_ready = await self._index_chunks(settings, note_id, chunks)

            task_service.update_task(
                task.id,
                status=TaskStatus.SUCCEEDED,
                progress=1.0,
                message="Ingestion finished",
                result={
                    "note_id": note_id,
                    "vector_chunks": vectors_ready,
                    "ocr_text_length": len(note_content),
                    "stored_path": str(saved_path.as_posix()),
                },
            )

        except Exception as exc:
            task_service.update_task(
                task.id,
                status=TaskStatus.FAILED,
                progress=1.0,
                message="Ingestion failed",
                error=str(exc),
            )
            return IngestResponse(
                note_id=note_id,
                task_id=task.id,
                status=TaskStatus.FAILED,
                message="File ingestion failed",
            )

        return IngestResponse(
            note_id=note_id,
            task_id=task.id,
            status=TaskStatus.SUCCEEDED,
            message="File ingested",
        )

    def _build_provider(self) -> NoteClawOpenAICompat:
        settings = get_settings()
        return NoteClawOpenAICompat.from_env_like(
            openai_compat_base_url=settings.openai_compat_base_url,
            openai_compat_api_key=settings.openai_compat_api_key,
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            vision_model=settings.vision_model,
            image_model=settings.image_model,
            chat_api_key=settings.openai_compat_chat_api_key,
            chat_base_url=settings.openai_compat_chat_base_url,
            chat_model=settings.openai_compat_chat_model,
            embedding_api_key=settings.openai_compat_embedding_api_key,
            embedding_base_url=settings.openai_compat_embedding_base_url,
            embedding_model_override=settings.openai_compat_embedding_model,
            vision_api_key=settings.openai_compat_vision_api_key,
            vision_base_url=settings.openai_compat_vision_base_url,
            vision_model_override=settings.openai_compat_vision_model,
            image_api_key=settings.openai_compat_image_api_key,
            image_base_url=settings.openai_compat_image_base_url,
            image_model_override=settings.openai_compat_image_model,
            ocr_api_key=settings.openai_compat_ocr_api_key,
            ocr_base_url=settings.openai_compat_ocr_base_url,
            ocr_model=settings.openai_compat_ocr_model,
        )

    def _infer_title(self, filename: str | None, source: str | None) -> str:
        if filename:
            return Path(filename).stem or "Uploaded image"
        if source:
            return f"Upload from {source}"
        return "Uploaded image"

    def _extract_summary(self, understanding: dict[str, Any]) -> str:
        candidate = understanding.get("summary")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

        raw = understanding.get("raw")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()

        return "Image ingested with OCR/vision enrichment pending"

    def _extract_tags(self, understanding: dict[str, Any]) -> list[str]:
        raw_tags = understanding.get("tags")
        if isinstance(raw_tags, list):
            return [str(t).strip() for t in raw_tags if str(t).strip()]

        if isinstance(raw_tags, str):
            parsed = [item.strip() for item in raw_tags.split(",") if item.strip()]
            if parsed:
                return parsed

        return ["image"]

    def _extract_category(self, understanding: dict[str, Any]) -> str | None:
        raw_category = understanding.get("category")
        if isinstance(raw_category, str) and raw_category.strip():
            return raw_category.strip()
        return None

    def _split_text_for_ingest(self, text: str, chunk_size: int = 1200) -> list[str]:
        if not text:
            return []
        normalized = text.replace("\r\n", "\n").strip()
        if not normalized:
            return []
        return [normalized[i : i + chunk_size] for i in range(0, len(normalized), chunk_size)]

    def _ensure_schema(self, settings) -> None:
        store = SQLiteStore(settings.sqlite_path)
        with store.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    tags_json TEXT NOT NULL,
                    category TEXT,
                    source TEXT,
                    source_url TEXT,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source_file_path TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    note_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(note_id) REFERENCES notes(id)
                )
                """
            )
            conn.commit()

    def _upsert_note_and_chunks(
        self,
        *,
        settings,
        source_file_path: str | None,
        note_id: str,
        content_type: ContentType,
        title: str,
        content: str,
        summary: str,
        tags: list[str],
        category: str | None,
        source: str | None,
        source_url: str | None,
        status: NoteStatus,
        created_at: str,
        updated_at: str,
        metadata: dict[str, Any],
        chunks: list[str],
    ) -> None:
        store = SQLiteStore(settings.sqlite_path)
        with store.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO notes (
                    id, title, content_type, content, summary, tags_json,
                    category, source, source_url, status, metadata_json,
                    created_at, updated_at, source_file_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note_id,
                    title,
                    content_type.value,
                    content,
                    summary,
                    json.dumps(tags, ensure_ascii=False),
                    category,
                    source,
                    source_url,
                    status.value,
                    json.dumps(metadata, ensure_ascii=False),
                    created_at,
                    updated_at,
                    source_file_path,
                ),
            )

            cur.execute("DELETE FROM chunks WHERE note_id = ?", (note_id,))
            for index, chunk_text in enumerate(chunks):
                chunk_id = f"chunk_{note_id}_{index}"
                chunk_meta = {
                    "note_id": note_id,
                    "order": index,
                    "source": "ocr",
                }
                cur.execute(
                    """
                    INSERT INTO chunks (id, note_id, chunk_index, text, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        note_id,
                        index,
                        chunk_text,
                        json.dumps(chunk_meta, ensure_ascii=False),
                        created_at,
                    ),
                )
            conn.commit()

    async def _index_chunks(self, settings, note_id: str, chunks: list[str]) -> int:
        if not chunks:
            return 0

        provider = self._build_provider()
        vectors = []
        try:
            vectors = await provider.embed_texts(chunks)
        except Exception:
            return 0

        if not vectors:
            return 0

        vector_list = list(vectors)
        chunk_ids = [f"chunk_{note_id}_{idx}" for idx in range(len(vector_list))]

        store = FaissVectorStore(settings.faiss_index_path)
        try:
            store.add(vector_list, chunk_ids)
        except NotImplementedError:
            return 0
        except Exception:
            return 0

        try:
            store.save()
        except Exception:
            return 0

        return len(chunk_ids)


ingestion_service = IngestionService()
