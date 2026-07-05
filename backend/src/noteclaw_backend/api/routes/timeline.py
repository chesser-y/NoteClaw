from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from noteclaw_backend.domain.enums import TimelineKind
from noteclaw_backend.schemas.timeline import (
    TimelineBoardResponse,
    TimelineItemCreate,
    TimelineItemListResponse,
    TimelineItemRead,
    TimelineItemUpdate,
)
from noteclaw_backend.services.timeline_service import timeline_service


router = APIRouter()


@router.get("", response_model=TimelineBoardResponse)
async def get_timeline(
    kind: TimelineKind = TimelineKind.RESEARCH,
    start_date: date | None = None,
    end_date: date | None = None,
    include_examples: bool = False,
    include_sources: bool = True,
    include_outputs: bool = True,
) -> TimelineBoardResponse:
    return await timeline_service.board(
        kind=kind,
        start_date=start_date,
        end_date=end_date,
        include_examples=include_examples,
        include_sources=include_sources,
        include_outputs=include_outputs,
    )


@router.get("/board", response_model=TimelineBoardResponse)
async def get_timeline_board(
    kind: TimelineKind = TimelineKind.RESEARCH,
    start_date: date | None = None,
    end_date: date | None = None,
    include_examples: bool = False,
    include_sources: bool = True,
    include_outputs: bool = True,
) -> TimelineBoardResponse:
    return await get_timeline(
        kind=kind,
        start_date=start_date,
        end_date=end_date,
        include_examples=include_examples,
        include_sources=include_sources,
        include_outputs=include_outputs,
    )


@router.post("/items", response_model=TimelineItemRead)
async def create_timeline_item(request: TimelineItemCreate) -> TimelineItemRead:
    return timeline_service.create_item(request)


@router.get("/items", response_model=TimelineItemListResponse)
async def list_timeline_items(
    kind: TimelineKind | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> TimelineItemListResponse:
    items, total = timeline_service.list_items(kind=kind, limit=limit, offset=offset)
    return TimelineItemListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/items/{item_id}", response_model=TimelineItemRead)
async def get_timeline_item(item_id: str) -> TimelineItemRead:
    item = timeline_service.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Timeline item not found")
    return item


@router.patch("/items/{item_id}", response_model=TimelineItemRead)
async def update_timeline_item(item_id: str, request: TimelineItemUpdate) -> TimelineItemRead:
    item = timeline_service.update_item(item_id, request)
    if item is None:
        raise HTTPException(status_code=404, detail="Timeline item not found")
    return item
