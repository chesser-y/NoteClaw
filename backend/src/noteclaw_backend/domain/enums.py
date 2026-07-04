from __future__ import annotations

from enum import StrEnum


class ContentType(StrEnum):
    TEXT = "text"
    CODE = "code"
    TABLE = "table"
    IMAGE = "image"
    DOCUMENT = "document"
    WEBPAGE = "webpage"
    REPOSITORY = "repository"


class NoteStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    VISION_PENDING = "vision_pending"
    READY = "ready"
    FAILED = "failed"


class SearchMode(StrEnum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class ChatReasoningMode(StrEnum):
    NORMAL = "normal"
    DEEP = "deep"
    WEB = "web"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkItemStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    NEED_REVIEW = "need_review"
    DONE = "done"


class TimelineKind(StrEnum):
    RESEARCH = "research"
    SOURCE = "source"
    OUTPUT = "output"


class TimelineItemStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    BLOCKED = "blocked"
    MILESTONE = "milestone"
    DONE = "done"


class GenerationType(StrEnum):
    LEARNING_NOTE = "learning_note"
    TECHNICAL_SUMMARY = "technical_summary"
    REPORT_DRAFT = "report_draft"
    PPT_OUTLINE = "ppt_outline"
    PPTX = "pptx"
    MIND_MAP = "mind_map"
    TABLE = "table"
    IMAGE = "image"
    DIAGRAM = "diagram"
    VIDEO_SCRIPT = "video_script"


class TaskType(StrEnum):
    INGESTION = "ingestion"
    VISION_ENRICHMENT = "vision_enrichment"
    GENERATION = "generation"
    HARNESS = "harness"
