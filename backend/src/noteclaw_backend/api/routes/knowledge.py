from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from noteclaw_backend.domain.enums import ContentType
from noteclaw_backend.schemas.common import ApiMessage
from noteclaw_backend.schemas.knowledge import (
    FavoriteRequest,
    FeedbackRequest,
    FeedbackResponse,
    KnowledgeListResponse,
    NoteDetail,
    NoteUpdateRequest,
)
from noteclaw_backend.schemas.knowledge_graph import KnowledgeGraphResponse
from noteclaw_backend.services.knowledge_graph import knowledge_graph_service
from noteclaw_backend.storage.faiss_store import get_vector_store
from noteclaw_backend.storage.repositories import get_repository


router = APIRouter()


@router.get("", response_model=KnowledgeListResponse)
async def list_knowledge(
    q: str | None = None,
    content_type: ContentType | None = None,
    tag: list[str] = Query(default_factory=list),
    category: str | None = None,
    source: str | None = None,
    source_contains: str | None = None,
    review_status: str | None = None,
    is_favorite: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> KnowledgeListResponse:
    metadata_filters: dict[str, str] | None = None
    if review_status:
        metadata_filters = {"review_status": review_status}
    items, total = await get_repository().list_notes(
        limit,
        offset,
        q=q,
        content_type=content_type,
        tags=tag,
        category=category,
        source=source,
        source_contains=source_contains,
        date_from=date_from,
        date_to=date_to,
        metadata_filters=metadata_filters,
        is_favorite=is_favorite,
    )
    return KnowledgeListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/_facets")
async def list_facets() -> dict:
    return await get_repository().facets()


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    include_notes: bool = True,
    include_categories: bool = True,
    include_content_types: bool = True,
    min_tag_count: int = Query(default=1, ge=1, le=50),
    min_edge_weight: int = Query(default=1, ge=1, le=50),
    limit_tags: int = Query(default=80, ge=1, le=300),
    limit_notes: int = Query(default=300, ge=1, le=1000),
    focus_tag: str | None = None,
) -> KnowledgeGraphResponse:
    return await knowledge_graph_service.build_graph(
        include_notes=include_notes,
        include_categories=include_categories,
        include_content_types=include_content_types,
        min_tag_count=min_tag_count,
        min_edge_weight=min_edge_weight,
        limit_tags=limit_tags,
        limit_notes=limit_notes,
        focus_tag=focus_tag,
    )


@router.get("/{note_id}", response_model=NoteDetail)
async def get_knowledge(note_id: str) -> NoteDetail:
    note = await get_repository().get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def _resolve_stored_path(note) -> Path | None:
    """Resolve the on-disk file for a note, if any."""
    meta = getattr(note, "metadata", None)
    if not isinstance(meta, dict):
        return None
    candidate = meta.get("stored_path")
    if not candidate:
        return None
    p = Path(str(candidate))
    if not p.is_absolute():
        from noteclaw_backend.settings import get_settings

        root = get_settings().storage_dir
        rel = str(p).removeprefix("storage/").removeprefix("storage" + str(Path("/")))
        p = root / rel
    return p if p.exists() else None


@router.get("/{note_id}/file")
async def get_note_file(note_id: str):
    note = await get_repository().get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    path = _resolve_stored_path(note)
    if path is None:
        raise HTTPException(status_code=404, detail="Note has no associated file")
    return FileResponse(str(path), filename=path.name)


@router.patch("/{note_id}", response_model=NoteDetail)
async def update_knowledge(note_id: str, request: NoteUpdateRequest) -> NoteDetail:
    note = await get_repository().update_note(
        note_id,
        title=request.title,
        summary=request.summary,
        tags=request.tags,
        category=request.category,
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}/metadata", response_model=NoteDetail)
async def patch_note_metadata(
    note_id: str,
    payload: dict,
) -> NoteDetail:
    note = await get_repository().get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    metadata = dict(note.metadata or {})
    for key, value in (payload or {}).items():
        if value is None:
            metadata.pop(key, None)
        else:
            metadata[key] = value
    updated = note.model_copy(update={"metadata": metadata})
    await get_repository().create_note(updated)
    return updated


@router.patch("/{note_id}/favorite", response_model=NoteDetail)
async def set_note_favorite(note_id: str, request: FavoriteRequest) -> NoteDetail:
    ok = await get_repository().set_note_favorite(note_id, request.is_favorite)
    if not ok:
        raise HTTPException(status_code=404, detail="Note not found")
    note = await get_repository().get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/{note_id}", response_model=ApiMessage)
async def delete_knowledge(note_id: str) -> ApiMessage:
    chunks = await get_repository().list_by_note(note_id)
    note = await get_repository().get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]
    await get_repository().mark_vectors_deleted(chunk_ids)
    get_vector_store().mark_deleted(chunk_ids)
    await get_repository().delete_note(note_id)
    return ApiMessage(message=f"Deleted {note_id}")


@router.post("/{note_id}/feedback", response_model=FeedbackResponse)
async def create_feedback(note_id: str, request: FeedbackRequest) -> FeedbackResponse:
    note = await get_repository().get_note(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    await get_repository().add_feedback(
        note_id=note_id,
        target=request.target,
        rating=request.rating,
        comment=request.comment,
    )
    return FeedbackResponse(
        note_id=note_id,
        accepted=True,
        message="Feedback saved",
    )
