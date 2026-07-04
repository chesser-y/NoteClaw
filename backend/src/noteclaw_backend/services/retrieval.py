from __future__ import annotations

from noteclaw_backend.domain.enums import SearchMode
from noteclaw_backend.schemas.common import Citation
from noteclaw_backend.schemas.search import SearchFilters, SearchRequest, SearchResponse, SearchResult
from noteclaw_backend.services.providers import get_embedding_provider
from noteclaw_backend.storage.faiss_store import get_vector_store
from noteclaw_backend.storage.repositories import get_repository


class RetrievalService:
    async def search(self, request: SearchRequest) -> SearchResponse:
        rows = await self.retrieve_chunks_for_question(
            request.query,
            request.limit,
            mode=request.mode,
            filters=request.filters,
        )
        return SearchResponse(
            query=request.query,
            mode=request.mode,
            results=[self._to_search_result(row) for row in rows],
        )

    async def retrieve_for_question(
        self,
        query: str,
        top_k: int,
        scope: dict | None = None,
    ) -> list[Citation]:
        rows = await self.retrieve_chunks_for_question(
            query,
            top_k,
            mode=SearchMode.HYBRID,
            scope=scope,
        )
        return [self._to_citation(row) for row in rows]

    async def retrieve_chunks_for_question(
        self,
        query: str,
        top_k: int,
        *,
        mode: SearchMode = SearchMode.HYBRID,
        filters: SearchFilters | None = None,
        scope: dict | None = None,
    ) -> list[dict]:
        filters = filters or SearchFilters()
        if mode == SearchMode.KEYWORD:
            rows = await get_repository().keyword_search(query, filters, top_k)
            return [row for row in rows if self._matches_scope(row, scope)][:top_k]
        if mode == SearchMode.SEMANTIC:
            return await self._semantic_search(query, top_k, filters=filters, scope=scope)
        keyword_rows = await get_repository().keyword_search(query, filters, max(top_k * 2, 10))
        semantic_rows = await self._semantic_search(query, max(top_k * 2, 10), filters=filters, scope=scope)
        return self._merge_results(keyword_rows, semantic_rows, top_k, scope=scope)

    async def _semantic_search(
        self,
        query: str,
        top_k: int,
        *,
        filters: SearchFilters,
        scope: dict | None,
    ) -> list[dict]:
        query_vector = (await get_embedding_provider().embed_texts([query]))[0]
        hits = get_vector_store().search(query_vector, max(top_k * 5, top_k))
        hit_scores = {hit.chunk_id: hit.score for hit in hits}
        rows = await get_repository().get_by_ids([hit.chunk_id for hit in hits])
        results: list[dict] = []
        for row in rows:
            row["score"] = hit_scores.get(row["chunk_id"])
            row["snippet"] = self._snippet(row["text"], query)
            if self._matches_filters(row, filters) and self._matches_scope(row, scope):
                results.append(row)
            if len(results) >= top_k:
                break
        return results

    def _merge_results(
        self,
        keyword_rows: list[dict],
        semantic_rows: list[dict],
        top_k: int,
        *,
        scope: dict | None,
    ) -> list[dict]:
        merged: dict[str, dict] = {}
        scores: dict[str, float] = {}
        max_keyword = max((float(row.get("score") or 0) for row in keyword_rows), default=1.0) or 1.0
        for rank, row in enumerate(keyword_rows):
            if not self._matches_scope(row, scope):
                continue
            key = row["chunk_id"]
            merged[key] = row
            scores[key] = scores.get(key, 0.0) + 0.45 * (float(row.get("score") or 0) / max_keyword) + 0.15 / (rank + 1)
        for rank, row in enumerate(semantic_rows):
            key = row["chunk_id"]
            merged.setdefault(key, row)
            scores[key] = scores.get(key, 0.0) + 0.55 * max(float(row.get("score") or 0), 0.0) + 0.15 / (rank + 1)
        ordered = sorted(merged.values(), key=lambda row: scores.get(row["chunk_id"], 0.0), reverse=True)
        for row in ordered:
            row["score"] = round(scores.get(row["chunk_id"], 0.0), 4)
        return ordered[:top_k]

    def _matches_filters(self, row: dict, filters: SearchFilters) -> bool:
        if filters.content_types and row["content_type"] not in filters.content_types:
            return False
        if filters.tags and not {tag.lower() for tag in filters.tags}.issubset({tag.lower() for tag in row.get("tags", [])}):
            return False
        if filters.category and row.get("category") != filters.category:
            return False
        return True

    def _matches_scope(self, row: dict, scope: dict | None) -> bool:
        if not scope:
            return True
        note_ids = set(scope.get("note_ids") or [])
        tags = {tag.lower() for tag in (scope.get("tags") or [])}
        content_types = set(scope.get("content_types") or [])
        if note_ids and row.get("note_id") not in note_ids:
            return False
        if tags and not tags.intersection({tag.lower() for tag in row.get("tags", [])}):
            return False
        if content_types and row.get("content_type").value not in content_types:
            return False
        return True

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

    def _to_citation(self, row: dict) -> Citation:
        return Citation(
            note_id=row["note_id"],
            chunk_id=row.get("chunk_id"),
            title=row["title"],
            snippet=row.get("snippet") or row["text"][:220],
            score=row.get("score"),
        )

    def _snippet(self, text: str, query: str, size: int = 220) -> str:
        lowered = text.lower()
        pos = lowered.find(query.lower()) if query else -1
        if pos < 0:
            for term in query.lower().split():
                pos = lowered.find(term)
                if pos >= 0:
                    break
        if pos < 0:
            return text[:size].strip()
        start = max(0, pos - size // 3)
        end = min(len(text), start + size)
        return ("..." if start else "") + text[start:end].strip() + ("..." if end < len(text) else "")


retrieval_service = RetrievalService()
