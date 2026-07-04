from __future__ import annotations

from noteclaw_backend.domain.enums import ContentType
from noteclaw_backend.schemas.common import Citation
from noteclaw_backend.schemas.search import SearchRequest, SearchResponse, SearchResult


class RetrievalService:
    async def search(self, request: SearchRequest) -> SearchResponse:
        result = SearchResult(
            note_id="note_stub",
            chunk_id="chunk_stub",
            title="Retrieval service placeholder",
            snippet=(
                "SQLite keyword search and embedding + FAISS semantic search will be "
                "implemented behind RetrievalService."
            ),
            score=None,
            content_type=ContentType.TEXT,
            tags=["stub", "retrieval"],
            source="system",
        )
        return SearchResponse(query=request.query, mode=request.mode, results=[result])

    async def retrieve_for_question(
        self,
        query: str,
        top_k: int,
        scope: dict | None = None,
    ) -> list[Citation]:
        return [
            Citation(
                note_id="note_stub",
                chunk_id="chunk_stub",
                title="Retrieval placeholder",
                snippet=f"Pending retrieval for query: {query[:120]}",
                score=None,
            )
        ][:top_k]


retrieval_service = RetrievalService()
