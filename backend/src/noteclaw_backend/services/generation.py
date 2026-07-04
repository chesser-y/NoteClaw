from __future__ import annotations

from noteclaw_backend.domain.enums import GenerationType, TaskStatus, TaskType
from noteclaw_backend.schemas.common import Citation
from noteclaw_backend.schemas.generation import (
    GenerationPreviewResponse,
    GenerationRequest,
    GenerationTaskResponse,
)
from noteclaw_backend.services.task_service import task_service


class GenerationService:
    async def create_generation_task(self, request: GenerationRequest) -> GenerationTaskResponse:
        task = task_service.create_task(
            TaskType.GENERATION,
            f"{request.generation_type.value} generation queued.",
        )
        return GenerationTaskResponse(
            task_id=task.id,
            status=TaskStatus.QUEUED,
            message="Generation accepted",
        )

    async def preview(self, request: GenerationRequest) -> GenerationPreviewResponse:
        content: dict | str
        if request.generation_type == GenerationType.PPT_OUTLINE:
            content = {
                "title": "NoteClaw PPT Outline Placeholder",
                "theme": request.options.theme,
                "slides": [
                    {
                        "layout": "cover",
                        "title": "NoteClaw",
                        "subtitle": "Personal knowledge base assistant",
                    },
                    {
                        "layout": "text_image",
                        "title": "System Architecture",
                        "bullets": [
                            "Vue frontend",
                            "FastAPI backend",
                            "SQLite metadata",
                            "FAISS vector retrieval",
                        ],
                    },
                ],
            }
        elif request.generation_type == GenerationType.MIND_MAP:
            content = "mindmap\n  root((NoteClaw))\n    Ingestion\n    Retrieval\n    QA\n    Generation"
        else:
            content = (
                "Generation preview placeholder. The final service will collect scoped "
                "knowledge, call the LLM provider, and return structured content."
            )
        return GenerationPreviewResponse(
            generation_type=request.generation_type,
            content=content,
            citations=[
                Citation(
                    note_id="note_stub",
                    chunk_id="chunk_stub",
                    title="Generation placeholder",
                    snippet="Generation will cite retrieved knowledge chunks.",
                    score=None,
                )
            ],
        )


generation_service = GenerationService()
