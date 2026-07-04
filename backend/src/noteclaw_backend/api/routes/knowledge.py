from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from noteclaw_backend.domain.enums import ContentType
from noteclaw_backend.schemas.common import ApiMessage
from noteclaw_backend.schemas.knowledge import (
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
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> KnowledgeListResponse:
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
    )
    return KnowledgeListResponse(items=items, total=total, limit=limit, offset=offset)


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
