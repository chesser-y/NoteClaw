from __future__ import annotations

from calendar import month_abbr
from datetime import date, timedelta
from typing import Any

from noteclaw_backend.domain.enums import (
    ContentType,
    TaskType,
    TimelineItemStatus,
    TimelineKind,
    WorkItemStatus,
)
from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.schemas.knowledge import NoteListItem
from noteclaw_backend.schemas.tasks import TaskWorkItemRead
from noteclaw_backend.schemas.timeline import (
    TimelineBoardResponse,
    TimelineDependency,
    TimelineItemCreate,
    TimelineItemRead,
    TimelineItemUpdate,
    TimelineLane,
    TimelineMilestone,
    TimelineMonth,
)
from noteclaw_backend.services.task_service import task_service
from noteclaw_backend.storage.repositories import get_repository


class TimelineService:
    _TITLES = {
        TimelineKind.RESEARCH: "Research Timeline",
        TimelineKind.SOURCE: "Source Timeline",
        TimelineKind.OUTPUT: "Output Timeline",
    }

    def __init__(self) -> None:
        self._items: dict[str, TimelineItemRead] = {}

    def create_item(self, request: TimelineItemCreate) -> TimelineItemRead:
        now = utc_now()
        item = TimelineItemRead(
            id=new_id("timeline"),
            kind=request.kind,
            title=request.title,
            lane=request.lane or self._default_lane(request.kind),
            start_date=request.start_date,
            end_date=request.end_date,
            progress=request.progress,
            status=request.status,
            milestone_date=request.milestone_date,
            dependency_ids=self._clean_ids(request.dependency_ids),
            tags=self._clean_tags(request.tags),
            source_note_ids=self._clean_ids(request.source_note_ids),
            source_task_ids=self._clean_ids(request.source_task_ids),
            current_stage=request.current_stage,
            result_url=request.result_url,
            result_label=request.result_label,
            metadata=request.metadata,
            created_at=now,
            updated_at=now,
        )
        self._items[item.id] = item
        return item

    def get_item(self, item_id: str) -> TimelineItemRead | None:
        return self._items.get(item_id)

    def update_item(self, item_id: str, request: TimelineItemUpdate) -> TimelineItemRead | None:
        item = self._items.get(item_id)
        if item is None:
            return None
        updates = request.model_dump(exclude_unset=True)
        if "tags" in updates and updates["tags"] is not None:
            updates["tags"] = self._clean_tags(updates["tags"])
        for key in ("dependency_ids", "source_note_ids", "source_task_ids"):
            if key in updates and updates[key] is not None:
                updates[key] = self._clean_ids(updates[key])
        if "metadata" in updates and updates["metadata"] is not None:
            updates["metadata"] = {**item.metadata, **updates["metadata"]}
        if "lane" in updates and not updates["lane"]:
            kind = updates.get("kind") or item.kind
            updates["lane"] = self._default_lane(kind)
        updates["updated_at"] = utc_now()
        updated = item.model_copy(update=updates)
        self._items[item_id] = updated
        return updated

    def list_items(
        self,
        *,
        kind: TimelineKind | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TimelineItemRead], int]:
        items = sorted(self._items.values(), key=lambda item: (item.start_date, item.updated_at), reverse=True)
        if kind is not None:
            items = [item for item in items if item.kind == kind]
        return items[offset : offset + limit], len(items)

    async def board(
        self,
        *,
        kind: TimelineKind,
        start_date: date | None = None,
        end_date: date | None = None,
        include_examples: bool = False,
        include_sources: bool = True,
        include_outputs: bool = True,
    ) -> TimelineBoardResponse:
        items = [item for item in self._items.values() if item.kind == kind]
        if kind == TimelineKind.SOURCE and include_sources:
            items.extend(await self._source_items_from_notes())
        if kind == TimelineKind.OUTPUT and include_outputs:
            items.extend(self._output_items_from_work_items())
        if include_examples:
            items.extend(self._example_items(kind))

        items = self._dedupe_items(items)
        items = sorted(items, key=lambda item: (item.start_date, item.title))
        months = self._months_for(items, start_date=start_date, end_date=end_date)
        lanes = self._lanes_for(items)
        milestones = self._milestones_for(items)
        dependencies = self._dependencies_for(items)
        return TimelineBoardResponse(
            kind=kind,
            title=self._TITLES[kind],
            months=months,
            lanes=lanes,
            milestones=milestones,
            dependencies=dependencies,
            total=len(items),
        )

    async def _source_items_from_notes(self) -> list[TimelineItemRead]:
        try:
            notes, _ = await get_repository().list_notes(limit=100, offset=0)
        except Exception:
            return []
        return [self._source_item_from_note(note) for note in notes]

    def _source_item_from_note(self, note: NoteListItem) -> TimelineItemRead:
        created = note.created_at.date()
        title_prefix = {
            ContentType.WEBPAGE: "Collected webpage",
            ContentType.IMAGE: "Saved visual source",
            ContentType.CODE: "Saved code source",
            ContentType.TABLE: "Saved table source",
            ContentType.DOCUMENT: "Saved document",
        }.get(note.content_type, "Saved source")
        return TimelineItemRead(
            id=f"source_{note.id}",
            kind=TimelineKind.SOURCE,
            title=f"{title_prefix}: {note.title}",
            lane=note.content_type.value,
            start_date=created,
            end_date=created,
            progress=1,
            status=TimelineItemStatus.DONE,
            milestone_date=created,
            tags=note.tags[:6],
            source_note_ids=[note.id],
            current_stage=note.summary or note.source or "Stored in knowledge base",
            result_url=f"/api/knowledge/{note.id}",
            result_label="Open source",
            metadata={
                "category": note.category,
                "source": note.source,
                "source_url": note.source_url,
                "content_type": note.content_type.value,
            },
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    def _output_items_from_work_items(self) -> list[TimelineItemRead]:
        work_items, _ = task_service.list_work_items(limit=100, offset=0)
        return [self._output_item_from_work_item(item) for item in work_items]

    def _output_item_from_work_item(self, item: TaskWorkItemRead) -> TimelineItemRead:
        created = item.created_at.date()
        updated = item.updated_at.date()
        status_map = {
            WorkItemStatus.QUEUED: TimelineItemStatus.PLANNED,
            WorkItemStatus.IN_PROGRESS: TimelineItemStatus.ACTIVE,
            WorkItemStatus.NEED_REVIEW: TimelineItemStatus.MILESTONE,
            WorkItemStatus.DONE: TimelineItemStatus.DONE,
        }
        return TimelineItemRead(
            id=f"output_{item.id}",
            kind=TimelineKind.OUTPUT,
            title=item.title,
            lane=item.task_type.value if item.task_type else "work item",
            start_date=created,
            end_date=updated,
            progress=1 if item.status == WorkItemStatus.DONE else 0.6 if item.status == WorkItemStatus.NEED_REVIEW else 0.35,
            status=status_map[item.status],
            milestone_date=updated if item.status in {WorkItemStatus.NEED_REVIEW, WorkItemStatus.DONE} else None,
            tags=item.tags,
            source_task_ids=[item.source_task_id] if item.source_task_id else [],
            current_stage=item.current_stage,
            result_url=item.result_url,
            result_label=item.result_label,
            metadata={**item.metadata, "work_item_id": item.id, "requires_confirmation": item.requires_confirmation},
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _months_for(
        self,
        items: list[TimelineItemRead],
        *,
        start_date: date | None,
        end_date: date | None,
    ) -> list[TimelineMonth]:
        if items:
            min_date = min(item.start_date for item in items)
            max_date = max(item.end_date or item.milestone_date or item.start_date for item in items)
        else:
            today = date.today()
            min_date = date(today.year, max(1, today.month - 2), 1)
            max_date = self._add_months(min_date, 4)
        min_date = start_date or min_date
        max_date = end_date or max_date
        current = date(min_date.year, min_date.month, 1)
        last = date(max_date.year, max_date.month, 1)
        months: list[TimelineMonth] = []
        while current <= last:
            months.append(
                TimelineMonth(
                    id=current.strftime("%Y-%m"),
                    label=month_abbr[current.month].upper(),
                    year=current.year,
                    month=current.month,
                    start_date=current,
                )
            )
            current = self._add_months(current, 1)
        return months

    def _lanes_for(self, items: list[TimelineItemRead]) -> list[TimelineLane]:
        lane_names = []
        seen: set[str] = set()
        for item in items:
            key = item.lane or self._default_lane(item.kind)
            if key.lower() in seen:
                continue
            seen.add(key.lower())
            lane_names.append(key)
        return [
            TimelineLane(
                id=self._slug(lane),
                title=lane,
                items=[item for item in items if item.lane == lane],
            )
            for lane in lane_names
        ]

    def _milestones_for(self, items: list[TimelineItemRead]) -> list[TimelineMilestone]:
        milestones = []
        for item in items:
            if item.milestone_date:
                milestones.append(
                    TimelineMilestone(
                        id=f"milestone_{item.id}",
                        item_id=item.id,
                        title=item.result_label or item.title,
                        date=item.milestone_date,
                        lane=item.lane,
                    )
                )
        return milestones

    def _dependencies_for(self, items: list[TimelineItemRead]) -> list[TimelineDependency]:
        by_id = {item.id: item for item in items}
        dependencies = []
        for target in items:
            for source_id in target.dependency_ids:
                source = by_id.get(source_id)
                if not source:
                    continue
                dependencies.append(
                    TimelineDependency(
                        source_id=source.id,
                        target_id=target.id,
                        source_title=source.title,
                        target_title=target.title,
                    )
                )
        return dependencies

    def _dedupe_items(self, items: list[TimelineItemRead]) -> list[TimelineItemRead]:
        seen: set[str] = set()
        deduped = []
        for item in items:
            if item.id in seen:
                continue
            seen.add(item.id)
            deduped.append(item)
        return deduped

    def _example_items(self, kind: TimelineKind) -> list[TimelineItemRead]:
        year = date.today().year
        now = utc_now()
        if kind == TimelineKind.RESEARCH:
            return [
                self._example_item("research_benchmark", kind, "NoteClaw benchmark design", "Multimodal RAG benchmark", date(year, 4, 1), date(year, 6, 20), 0.9, TimelineItemStatus.ACTIVE, date(year, 6, 25), ["benchmark", "rag"], "Reading papers · Drafting comparison", now),
                self._example_item("research_pdf_rag", kind, "PDF RAG evaluation", "Evaluation", date(year, 4, 10), date(year, 5, 30), 0.75, TimelineItemStatus.MILESTONE, date(year, 6, 3), ["pdf", "evaluation"], "Scoring retrieval quality", now),
                self._example_item("research_visual_retrieval", kind, "Visual document retrieval", "Multimodal retrieval", date(year, 6, 1), date(year, 8, 8), 0.45, TimelineItemStatus.ACTIVE, None, ["vision", "retrieval"], "Testing image+text queries", now),
                self._example_item("research_code_search", kind, "Code knowledge search", "Code intelligence", date(year, 6, 12), date(year, 7, 18), 0.55, TimelineItemStatus.ACTIVE, date(year, 7, 20), ["code", "search"], "Indexing snippets · Comparing methods", now),
                self._example_item("research_notes_eval", kind, "Personal notes evaluation", "Personal knowledge", date(year, 8, 1), date(year, 8, 28), 0.1, TimelineItemStatus.PLANNED, None, ["notes", "ux"], "Planned after benchmark review", now),
            ]
        if kind == TimelineKind.SOURCE:
            return [
                self._example_item("source_pdf", kind, "Saved 3 PDF benchmark papers", "PDF", date(year, 4, 5), date(year, 4, 5), 1, TimelineItemStatus.DONE, date(year, 4, 5), ["pdf"], "Stored in knowledge base", now),
                self._example_item("source_web", kind, "Collected web notes for Agent Tasks", "Web", date(year, 5, 12), date(year, 5, 12), 1, TimelineItemStatus.DONE, date(year, 5, 12), ["web", "agent"], "Nanobot web evidence saved", now),
                self._example_item("source_visual", kind, "Added visual retrieval samples", "Images", date(year, 6, 2), date(year, 6, 2), 1, TimelineItemStatus.DONE, date(year, 6, 2), ["image"], "OCR and vision summaries ready", now),
            ]
        items = [
            self._example_item("output_collect", kind, "资料搜集", "Output pipeline", date(year, 4, 1), date(year, 4, 15), 1, TimelineItemStatus.DONE, date(year, 4, 15), ["collect"], "Sources collected", now),
            self._example_item("output_evidence", kind, "证据提取", "Output pipeline", date(year, 4, 16), date(year, 5, 10), 1, TimelineItemStatus.DONE, date(year, 5, 10), ["evidence"], "12 chunks found", now, ["output_collect"]),
            self._example_item("output_table", kind, "对比表", "Output pipeline", date(year, 5, 11), date(year, 5, 25), 0.9, TimelineItemStatus.MILESTONE, date(year, 5, 28), ["table"], "Waiting for review", now, ["output_evidence"]),
            self._example_item("output_report", kind, "报告草稿", "Output pipeline", date(year, 6, 1), date(year, 6, 22), 0.65, TimelineItemStatus.ACTIVE, None, ["report"], "Drafting sections", now, ["output_table"]),
            self._example_item("output_ppt", kind, "PPT 大纲", "Output pipeline", date(year, 6, 23), date(year, 7, 10), 0.35, TimelineItemStatus.PLANNED, None, ["ppt"], "Queued after report draft", now, ["output_report"]),
            self._example_item("output_final", kind, "最终版本", "Output pipeline", date(year, 7, 11), date(year, 7, 25), 0, TimelineItemStatus.PLANNED, date(year, 7, 26), ["final"], "Requires confirmation", now, ["output_ppt"]),
        ]
        return items

    def _example_item(
        self,
        item_id: str,
        kind: TimelineKind,
        title: str,
        lane: str,
        start: date,
        end: date,
        progress: float,
        status: TimelineItemStatus,
        milestone: date | None,
        tags: list[str],
        stage: str,
        now,
        dependencies: list[str] | None = None,
    ) -> TimelineItemRead:
        return TimelineItemRead(
            id=item_id,
            kind=kind,
            title=title,
            lane=lane,
            start_date=start,
            end_date=end,
            progress=progress,
            status=status,
            milestone_date=milestone,
            dependency_ids=dependencies or [],
            tags=tags,
            current_stage=stage,
            metadata={"example": True},
            created_at=now,
            updated_at=now,
        )

    def _default_lane(self, kind: TimelineKind) -> str:
        return {
            TimelineKind.RESEARCH: "Research topics",
            TimelineKind.SOURCE: "Knowledge sources",
            TimelineKind.OUTPUT: "Output pipeline",
        }[kind]

    def _clean_tags(self, tags: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned = []
        for tag in tags:
            value = str(tag).strip()[:40]
            if not value or value.lower() in seen:
                continue
            seen.add(value.lower())
            cleaned.append(value)
        return cleaned[:8]

    def _clean_ids(self, values: list[str]) -> list[str]:
        return [str(value).strip() for value in values if str(value).strip()]

    def _slug(self, value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "lane"

    def _add_months(self, value: date, months: int) -> date:
        month = value.month - 1 + months
        year = value.year + month // 12
        month = month % 12 + 1
        return date(year, month, 1)


timeline_service = TimelineService()
