from __future__ import annotations

from noteclaw_backend.domain.enums import GenerationType, SearchMode, TaskStatus, TaskType
from noteclaw_backend.schemas.common import Citation
from noteclaw_backend.schemas.generation import (
    GenerationPreviewResponse,
    GenerationRequest,
    GenerationTaskResponse,
)
from noteclaw_backend.services.providers import get_llm_provider
from noteclaw_backend.services.retrieval import retrieval_service
from noteclaw_backend.services.task_service import task_service


class GenerationService:
    async def create_generation_task(self, request: GenerationRequest) -> GenerationTaskResponse:
        task = task_service.create_task(
            TaskType.GENERATION,
            f"{request.generation_type.value} generation started.",
        )
        task_service.mark_running(task.id, "Generating content")
        try:
            preview = await self.preview(request)
            task_service.mark_succeeded(
                task.id,
                message="Generation completed",
                result=preview.model_dump(mode="json"),
            )
            return GenerationTaskResponse(
                task_id=task.id,
                status=TaskStatus.SUCCEEDED,
                message="Generation completed",
            )
        except Exception as exc:
            task_service.mark_failed(task.id, str(exc))
            raise

    async def preview(self, request: GenerationRequest) -> GenerationPreviewResponse:
        rows = await retrieval_service.retrieve_chunks_for_question(
            request.prompt,
            8,
            mode=SearchMode.HYBRID,
            scope=request.scope.model_dump(),
        )
        citations = [
            Citation(
                note_id=row["note_id"],
                chunk_id=row.get("chunk_id"),
                title=row["title"],
                snippet=row.get("snippet") or row["text"][:220],
                score=row.get("score"),
            )
            for row in rows
        ]
        content = await self._generate_content(request, rows)
        return GenerationPreviewResponse(
            generation_type=request.generation_type,
            content=content,
            citations=citations,
        )

    async def _generate_content(self, request: GenerationRequest, rows: list[dict]) -> dict | str:
        if request.generation_type == GenerationType.PPT_OUTLINE:
            outline = await self._try_llm_ppt_outline(request, rows)
            return outline or self._fallback_ppt_outline(request, rows)
        if request.generation_type == GenerationType.MIND_MAP:
            return self._mind_map(request, rows)
        if request.generation_type in {
            GenerationType.LEARNING_NOTE,
            GenerationType.TECHNICAL_SUMMARY,
            GenerationType.REPORT_DRAFT,
        }:
            return await self._markdown_generation(request, rows)
        return await self._markdown_generation(request, rows)

    async def _try_llm_ppt_outline(self, request: GenerationRequest, rows: list[dict]) -> dict | None:
        context = self._context(rows)
        data = await get_llm_provider().complete_json(
            [
                {
                    "role": "system",
                    "content": "Return a JSON PPT outline with keys title, theme, slides. Each slide has layout, title, bullets.",
                },
                {
                    "role": "user",
                    "content": (
                        f"Prompt: {request.prompt}\n"
                        f"Slide count: {request.options.slide_count or 6}\n"
                        f"Theme: {request.options.theme}\n"
                        f"Knowledge context:\n{context}"
                    ),
                },
            ]
        )
        slides = data.get("slides")
        if isinstance(slides, list) and slides:
            limit = request.options.slide_count or 8
            return {
                "title": str(data.get("title") or request.prompt)[:120],
                "theme": request.options.theme,
                "slides": slides[:limit],
            }
        return None

    async def _markdown_generation(self, request: GenerationRequest, rows: list[dict]) -> str:
        context = self._context(rows)
        if not context:
            context = "No knowledge chunks matched. Use the prompt as the only source."
        kind = request.generation_type.value.replace("_", " ")
        messages = [
            {
                "role": "system",
                "content": "Generate useful Markdown from the provided personal knowledge-base context. Cite source numbers where relevant.",
            },
            {
                "role": "user",
                "content": f"Task: create a {kind}.\nPrompt: {request.prompt}\n\nContext:\n{context}",
            },
        ]
        return (await get_llm_provider().complete_text(messages)).strip()

    def _fallback_ppt_outline(self, request: GenerationRequest, rows: list[dict]) -> dict:
        slide_count = request.options.slide_count or 6
        topics = rows[: max(1, slide_count - 2)]
        slides = [
            {
                "layout": "cover",
                "title": request.prompt[:80],
                "subtitle": "Generated from NoteClaw knowledge base",
            }
        ]
        for row in topics:
            slides.append(
                {
                    "layout": "text_image",
                    "title": row["title"][:80],
                    "bullets": self._bullets(row["text"]),
                }
            )
        slides.append(
            {
                "layout": "summary",
                "title": "Key Takeaways",
                "bullets": [
                    "Knowledge was retrieved from stored notes",
                    "Use citations to inspect original sources",
                    "Refine scope or tags for a sharper outline",
                ],
            }
        )
        return {"title": request.prompt[:120], "theme": request.options.theme, "slides": slides[:slide_count]}

    def _mind_map(self, request: GenerationRequest, rows: list[dict]) -> str:
        lines = ["mindmap", f"  root(({request.prompt[:40] or 'NoteClaw'}))"]
        if not rows:
            lines.extend(["    Knowledge", "    Search", "    Generation"])
            return "\n".join(lines)
        for row in rows[:8]:
            title = self._mermaid_text(row["title"][:36])
            lines.append(f"    {title}")
            for tag in row.get("tags", [])[:3]:
                lines.append(f"      {self._mermaid_text(str(tag)[:28])}")
        return "\n".join(lines)

    def _context(self, rows: list[dict]) -> str:
        parts = []
        for index, row in enumerate(rows, start=1):
            parts.append(f"Source [{index}] {row['title']}\n{row['text']}")
        return "\n\n".join(parts)[:12000]

    def _bullets(self, text: str) -> list[str]:
        sentences = [part.strip() for part in text.replace("\n", " ").split(".") if part.strip()]
        if not sentences:
            sentences = [text.strip()]
        return [sentence[:120] for sentence in sentences[:4]]

    def _mermaid_text(self, text: str) -> str:
        return text.replace("(", "").replace(")", "").replace(":", " ").replace("#", "") or "item"


generation_service = GenerationService()
