from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from noteclaw_backend.services.duplicate_detection import duplicate_detection_service
from noteclaw_backend.storage.repositories import get_repository


router = APIRouter()


class ReviewAction(BaseModel):
    action: Literal["approve", "reject", "defer"]


class DuplicateRunResponse(BaseModel):
    inserted: int
    total_found: int


@router.get("/items")
async def list_review_items() -> dict[str, Any]:
    repo = get_repository()
    drafts, drafts_total = await repo.list_notes(
        limit=50,
        offset=0,
        source="generation",
        metadata_filters={"review_status": "pending"},
    )
    low_conf, low_conf_total = await repo.list_notes(
        limit=50,
        offset=0,
        source="chat_low_confidence",
        metadata_filters={"review_status": "pending"},
    )
    duplicates = await duplicate_detection_service.list_open_items()

    return {
        "drafts": {
            "total": drafts_total,
            "items": [_note_to_draft(d.model_dump(mode="json")) for d in drafts],
        },
        "low_confidence": {
            "total": low_conf_total,
            "items": [_note_to_low_conf(n.model_dump(mode="json")) for n in low_conf],
        },
        "duplicates": {
            "total": len(duplicates),
            "items": duplicates,
        },
    }


@router.post("/items/{item_id}/action")
async def act_on_review_item(
    item_id: str,
    payload: ReviewAction,
) -> dict[str, Any]:
    """Resolve a review item.

    For note-backed items (drafts, low-confidence) the item_id is the note id;
    for duplicate pairs it's the review_items.id.
    """
    repo = get_repository()

    note = await repo.get_note(item_id)
    if note is not None:
        if payload.action == "approve":
            metadata = dict(note.metadata or {})
            metadata["review_status"] = "approved"
            updated = note.model_copy(update={"metadata": metadata})
            await repo.create_note(updated)
            return {"status": "approved", "id": item_id}
        if payload.action == "reject":
            await repo.delete_note(item_id)
            return {"status": "rejected", "id": item_id}
        # defer
        metadata = dict(note.metadata or {})
        metadata["review_status"] = "deferred"
        updated = note.model_copy(update={"metadata": metadata})
        await repo.create_note(updated)
        return {"status": "deferred", "id": item_id}

    resolved = await duplicate_detection_service.resolve_item(
        item_id,
        "approved" if payload.action == "approve" else ("rejected" if payload.action == "reject" else "deferred"),
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Review item not found")
    return {"status": payload.action, "id": item_id}


@router.post("/duplicates/run", response_model=DuplicateRunResponse)
async def run_duplicate_detection() -> DuplicateRunResponse:
    pairs = await duplicate_detection_service.find_duplicates(threshold=0.85, max_pairs=50)
    inserted = await duplicate_detection_service.persist_pairs(pairs)
    return DuplicateRunResponse(inserted=inserted, total_found=len(pairs))


def _note_to_draft(n: dict) -> dict:
    meta = n.get("metadata") or {}
    return {
        "id": n["id"],
        "title": n.get("title") or "Untitled",
        "summary": n.get("summary") or "",
        "generation_type": meta.get("generation_type"),
        "prompt": meta.get("prompt"),
        "created_at": n.get("created_at"),
        "download_url": f"/api/knowledge/{n['id']}/file" if meta.get("stored_path") else None,
        "note_id": n["id"],
    }


def _note_to_low_conf(n: dict) -> dict:
    meta = n.get("metadata") or {}
    return {
        "id": n["id"],
        "title": n.get("title") or "Untitled",
        "answer": n.get("content") or "",
        "question": meta.get("question") or "",
        "confidence": meta.get("confidence"),
        "verdict": meta.get("verdict"),
        "risks": meta.get("risks") or [],
        "session_id": meta.get("session_id"),
        "created_at": n.get("created_at"),
        "note_id": n["id"],
    }
