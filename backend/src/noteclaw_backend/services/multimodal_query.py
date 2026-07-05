from __future__ import annotations

import re
from pathlib import Path

from fastapi import HTTPException

from noteclaw_backend.domain.enums import ContentType, SearchMode
from noteclaw_backend.schemas.common import new_id
from noteclaw_backend.schemas.multimodal import MultimodalQueryContext, MultimodalSearchResponse
from noteclaw_backend.schemas.search import SearchResult
from noteclaw_backend.services.document_parser import parse_file_bytes
from noteclaw_backend.services.providers import get_vision_provider
from noteclaw_backend.services.retrieval import retrieval_service
from noteclaw_backend.settings import get_settings


class MultimodalQueryService:
    async def search(
        self,
        *,
        query: str,
        mode: SearchMode,
        limit: int,
        filename: str | None = None,
        data: bytes | None = None,
    ) -> MultimodalSearchResponse:
        query = query.strip()
        if not query and not data:
            raise HTTPException(status_code=400, detail="Provide a text query, an uploaded file, or both.")

        context = await self._build_context(query=query, filename=filename, data=data)
        rows = await retrieval_service.retrieve_chunks_for_question(
            context.enhanced_query,
            limit,
            mode=mode,
        )
        return MultimodalSearchResponse(
            query=query,
            mode=mode,
            enhanced_query=context.enhanced_query,
            modality=context.modality,
            query_context=context,
            results=[self._to_search_result(row) for row in rows],
        )

    async def _build_context(
        self,
        *,
        query: str,
        filename: str | None,
        data: bytes | None,
    ) -> MultimodalQueryContext:
        if not data:
            return MultimodalQueryContext(
                original_query=query,
                enhanced_query=query,
                modality="text",
            )

        filename = filename or "query_upload.bin"
        saved_path = self._save_query_upload(filename, data)
        parsed = parse_file_bytes(filename=filename, data=data, saved_path=saved_path)
        extracted_text = parsed.content.strip()
        visual_description: str | None = None
        metadata = dict(parsed.metadata)

        if parsed.content_type == ContentType.IMAGE:
            vision = await get_vision_provider().understand_image(
                str(saved_path),
                parsed.metadata.get("ocr_text"),
            )
            visual_description = str(vision.get("description", "")).strip() or None
            metadata["vision"] = vision

        enhanced_query = self._compose_enhanced_query(
            query=query,
            filename=filename,
            modality=parsed.content_type.value,
            extracted_text=extracted_text,
            visual_description=visual_description,
        )
        return MultimodalQueryContext(
            original_query=query,
            enhanced_query=enhanced_query,
            modality=parsed.content_type.value,
            extracted_text=self._compact(extracted_text, 2400),
            visual_description=self._compact(visual_description or "", 1600) or None,
            metadata={**metadata, "query_upload_path": str(saved_path)},
        )

    def _compose_enhanced_query(
        self,
        *,
        query: str,
        filename: str,
        modality: str,
        extracted_text: str,
        visual_description: str | None,
    ) -> str:
        parts = []
        if query:
            parts.append(f"User query: {query}")
        parts.append(f"Attached {modality} file: {filename}")
        if extracted_text:
            parts.append("Extracted content/OCR:\n" + self._compact(extracted_text, 3200))
        if visual_description:
            parts.append("Visual description:\n" + self._compact(visual_description, 2200))
        if not query:
            parts.append("Find knowledge-base documents that match this attached content.")
        return "\n\n".join(parts)

    def _save_query_upload(self, filename: str, data: bytes) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name) or "query_upload.bin"
        upload_dir = get_settings().storage_dir / "query_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / f"{new_id('query')}_{safe_name}"
        path.write_bytes(data)
        return path

    def _to_search_result(self, row: dict) -> SearchResult:
        return SearchResult(
            note_id=row["note_id"],
            chunk_id=row.get("chunk_id"),
            title=row["title"],
            snippet=row.get("snippet") or row["text"][:220],
            score=row.get("score"),
            content_type=row["content_type"],
            tags=row.get("tags", []),
            source=row.get("source"),
        )

    def _compact(self, text: str, limit: int) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[:limit].rstrip() + "..."


multimodal_query_service = MultimodalQueryService()
