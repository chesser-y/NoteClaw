from __future__ import annotations

import re
from typing import Any

from noteclaw_backend.domain.enums import GenerationType, SearchMode, TaskStatus, TaskType
from noteclaw_backend.schemas.common import Artifact, Citation, new_id
from noteclaw_backend.schemas.generation import (
    GenerationPreviewResponse,
    GenerationRequest,
    GenerationTaskResponse,
)
from noteclaw_backend.services.providers import get_image_provider, get_llm_provider
from noteclaw_backend.services.retrieval import retrieval_service
from noteclaw_backend.services.task_service import task_service
from noteclaw_backend.settings import get_settings


class GenerationService:
    async def create_generation_task(self, request: GenerationRequest) -> GenerationTaskResponse:
        task = task_service.create_task(
            TaskType.GENERATION,
            f"{request.generation_type.value} generation started.",
            work_item_title=request.prompt[:120],
            tags=["generation", request.generation_type.value],
            current_stage="Preparing retrieved context",
            requires_confirmation=True,
            metadata={
                "generation_type": request.generation_type.value,
                "scope": request.scope.model_dump(mode="json"),
            },
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
        should_retrieve = (
            request.generation_type != GenerationType.IMAGE
            or self._should_ground_image_prompt(request)
        )
        rows = []
        if should_retrieve:
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

    async def _generate_content(self, request: GenerationRequest, rows: list[dict]) -> dict[str, Any] | str:
        if request.generation_type == GenerationType.PPT_OUTLINE:
            outline = await self._try_llm_ppt_outline(request, rows)
            return outline or self._fallback_ppt_outline(request, rows)
        if request.generation_type == GenerationType.PPTX:
            return await self._pptx_generation(request, rows)
        if request.generation_type == GenerationType.MIND_MAP:
            return self._mind_map(request, rows)
        if request.generation_type == GenerationType.TABLE:
            return self._knowledge_table(request, rows)
        if request.generation_type == GenerationType.DIAGRAM:
            return self._diagram(request, rows)
        if request.generation_type == GenerationType.VIDEO_SCRIPT:
            return self._video_script(request, rows)
        if request.generation_type == GenerationType.IMAGE:
            return await self._image_generation(request, rows)
        if request.generation_type in {
            GenerationType.LEARNING_NOTE,
            GenerationType.TECHNICAL_SUMMARY,
            GenerationType.REPORT_DRAFT,
        }:
            return await self._markdown_generation(request, rows)
        return await self._markdown_generation(request, rows)

    async def _try_llm_ppt_outline(self, request: GenerationRequest, rows: list[dict]) -> dict[str, Any] | None:
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

    async def _pptx_generation(self, request: GenerationRequest, rows: list[dict]) -> dict[str, Any]:
        outline = await self._try_llm_ppt_outline(request, rows)
        outline = outline or self._fallback_ppt_outline(request, rows)
        artifact, warning = self._write_pptx(outline)
        return {
            "outline": outline,
            "artifact": artifact.model_dump(mode="json") if artifact else None,
            "warning": warning,
        }

    def _write_pptx(self, outline: dict[str, Any]) -> tuple[Artifact | None, str | None]:
        try:
            from pptx import Presentation
        except Exception as exc:
            return None, f"python-pptx is unavailable: {exc}"

        try:
            presentation = Presentation()
            title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
            title_slide.shapes.title.text = str(outline.get("title") or "NoteClaw Deck")[:120]
            if len(title_slide.placeholders) > 1:
                title_slide.placeholders[1].text = "Generated from NoteClaw knowledge base"

            slide_items = list(outline.get("slides") or [])
            if slide_items and str(slide_items[0].get("layout", "")).lower() == "cover":
                slide_items = slide_items[1:]
            for slide_data in slide_items:
                slide = presentation.slides.add_slide(presentation.slide_layouts[1])
                title = str(slide_data.get("title") or "Untitled")[:120]
                slide.shapes.title.text = title
                body = slide.placeholders[1].text_frame
                body.clear()
                bullets = slide_data.get("bullets") or slide_data.get("points") or []
                if isinstance(bullets, str):
                    bullets = [bullets]
                for bullet in list(bullets)[:6] or ["Generated from retrieved knowledge."]:
                    paragraph = body.add_paragraph()
                    paragraph.text = str(bullet)[:220]
                    paragraph.level = 0

            output_dir = get_settings().storage_dir / "generated"
            output_dir.mkdir(parents=True, exist_ok=True)
            artifact_id = new_id("artifact")
            safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", str(outline.get("title") or "noteclaw_deck"))[:50]
            path = output_dir / f"{artifact_id}_{safe_title}.pptx"
            presentation.save(path)
            artifact = Artifact(
                id=artifact_id,
                type="pptx",
                name=path.name,
                url=str(path),
                metadata={"slide_count": len(presentation.slides)},
            )
            return artifact, None
        except Exception as exc:
            return None, f"PPTX generation failed: {exc}"

    def _fallback_ppt_outline(self, request: GenerationRequest, rows: list[dict]) -> dict[str, Any]:
        slide_count = request.options.slide_count or 6
        topics = rows[: max(1, slide_count - 2)]
        slides: list[dict[str, Any]] = [
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
        lines = ["mindmap", f"  root(({self._mermaid_text(request.prompt[:40]) or 'NoteClaw'}))"]
        if not rows:
            lines.extend(["    Knowledge", "    Search", "    Generation"])
            return "\n".join(lines)
        for row in rows[:8]:
            title = self._mermaid_text(row["title"][:36])
            lines.append(f"    {title}")
            for tag in row.get("tags", [])[:3]:
                lines.append(f"      {self._mermaid_text(str(tag)[:28])}")
        return "\n".join(lines)

    def _knowledge_table(self, request: GenerationRequest, rows: list[dict]) -> dict[str, Any]:
        table_rows = []
        for index, row in enumerate(rows[:10], start=1):
            table_rows.append(
                {
                    "source": f"[{index}]",
                    "title": row["title"],
                    "type": row["content_type"].value,
                    "category": row.get("category") or "general",
                    "key_points": "; ".join(self._bullets(row["text"])[:3]),
                }
            )
        columns = ["source", "title", "type", "category", "key_points"]
        return {
            "title": request.prompt[:120],
            "columns": columns,
            "rows": table_rows,
            "markdown": self._markdown_table(columns, table_rows),
        }

    def _diagram(self, request: GenerationRequest, rows: list[dict]) -> str:
        root = self._mermaid_label(request.prompt[:50] or "NoteClaw")
        lines = ["flowchart TD", f'  root["{root}"]']
        if not rows:
            lines.extend([
                '  root --> retrieve["Retrieve knowledge"]',
                '  retrieve --> generate["Generate answer"]',
            ])
            return "\n".join(lines)
        for index, row in enumerate(rows[:8], start=1):
            node = f"doc{index}"
            lines.append(f'  root --> {node}["{self._mermaid_label(row["title"][:48])}"]')
            category = row.get("category") or row["content_type"].value
            lines.append(f'  {node} --> {node}_cat["{self._mermaid_label(category)}"]')
            for tag_index, tag in enumerate(row.get("tags", [])[:2], start=1):
                lines.append(f'  {node} --> {node}_tag{tag_index}["{self._mermaid_label(str(tag)[:32])}"]')
        return "\n".join(lines)

    def _video_script(self, request: GenerationRequest, rows: list[dict]) -> dict[str, Any]:
        scenes = []
        source_rows = rows[:5] or [{"title": request.prompt, "text": request.prompt, "content_type": "text"}]
        for index, row in enumerate(source_rows, start=1):
            bullets = self._bullets(row["text"])
            scenes.append(
                {
                    "scene": index,
                    "title": row["title"][:80],
                    "voiceover": " ".join(bullets[:2])[:360],
                    "visual": f"Show {row['title'][:60]} with highlighted evidence and concise labels.",
                    "source": f"[{index}]" if rows else None,
                }
            )
        markdown = [f"# Video Script: {request.prompt[:80]}"]
        for scene in scenes:
            markdown.extend(
                [
                    f"\n## Scene {scene['scene']}: {scene['title']}",
                    f"Voiceover: {scene['voiceover']}",
                    f"Visual: {scene['visual']}",
                ]
            )
        return {"title": request.prompt[:120], "scenes": scenes, "markdown": "\n".join(markdown)}


    async def _image_generation(self, request: GenerationRequest, rows: list[dict]) -> dict[str, Any]:
        pack = self._image_prompt_pack(request, rows)
        size = str(pack.get("size") or "1024x1024")
        image_url = await get_image_provider().generate_image(str(pack["prompt"]), size=size)
        if image_url:
            return {**pack, "status": "generated", "url": image_url, "note": "Generated with the configured image API provider."}
        return pack

    def _image_prompt_pack(self, request: GenerationRequest, rows: list[dict]) -> dict[str, Any]:
        anchors = self._image_evidence_anchors(rows) if self._should_ground_image_prompt(request) else []
        prompt = self._compose_image_prompt(request, anchors)
        return {
            "status": "prompt_ready",
            "prompt": prompt[:1800],
            "size": request.options.extra.get("size", "1024x1024"),
            "grounded_with_retrieval": bool(anchors),
            "anchor_count": len(anchors),
            "source_titles": [str(row.get("title") or "")[:120] for row in rows[:4]] if anchors else [],
            "note": "No image generation provider is wired yet; this prompt is ready for a compatible image model.",
        }

    def _should_ground_image_prompt(self, request: GenerationRequest) -> bool:
        extra = request.options.extra
        explicit = extra.get("ground_with_retrieval", extra.get("use_retrieved_context"))
        if isinstance(explicit, bool):
            return explicit
        if isinstance(explicit, str):
            normalized = explicit.strip().lower()
            if normalized in {"1", "true", "yes", "on", "always"}:
                return True
            if normalized in {"0", "false", "no", "off", "never"}:
                return False

        prompt = request.prompt.lower()
        grounded_cues = (
            "based on",
            "according to",
            "from the provided",
            "use the retrieved",
            "use these sources",
            "source material",
            "source document",
            "provided document",
            "retrieved document",
            "from my notes",
            "from the knowledge base",
            "paper",
            "technical diagram",
            "schematic",
            "flowchart",
            "chart",
            "visualize the method",
            "visualize the evidence",
            "基于",
            "根据",
            "参考资料",
            "结合资料",
            "原文",
            "论文",
            "证据",
            "引用",
            "检索结果",
            "知识库内容",
            "技术图",
            "流程图",
            "图解",
        )
        generic_cues = (
            "icon",
            "logo",
            "app icon",
            "brand",
            "avatar",
            "poster",
            "cover",
            "wallpaper",
            "simple clean",
            "图标",
            "标志",
            "品牌",
            "头像",
            "海报",
            "封面",
            "壁纸",
            "插画",
        )
        if any(cue in prompt for cue in generic_cues) and not any(cue in prompt for cue in grounded_cues):
            return False
        return any(cue in prompt for cue in grounded_cues)

    def _image_evidence_anchors(self, rows: list[dict]) -> list[str]:
        anchors = []
        for row in rows[:4]:
            bullets = self._bullets(row.get("text", ""))
            if bullets:
                title = str(row.get("title") or "Source")[:80]
                anchors.append(f"{title}: {bullets[0]}")
        return anchors

    def _compose_image_prompt(self, request: GenerationRequest, anchors: list[str]) -> str:
        base_prompt = request.prompt.strip()
        style_note = (
            "Create a polished, coherent image. Keep composition readable, labels minimal, "
            "and avoid tiny illegible text."
        )
        if anchors:
            evidence = "\n".join(f"- {anchor}" for anchor in anchors)
            return (
                f"{style_note}\n"
                f"User visual request: {base_prompt}\n"
                "Use the retrieved knowledge below only as factual visual anchors, not as text to paste verbatim:\n"
                f"{evidence}"
            )
        return (
            f"{style_note}\n"
            f"User visual request: {base_prompt}\n"
            "Use the user request as the primary source. Do not introduce unrelated retrieved-paper terms, "
            "citations, abstracts, equations, or source snippets unless the user explicitly asks for a knowledge-grounded diagram."
        )

    def _context(self, rows: list[dict]) -> str:
        parts = []
        for index, row in enumerate(rows, start=1):
            parts.append(f"Source [{index}] {row['title']}\n{row['text']}")
        return "\n\n".join(parts)[:12000]

    def _bullets(self, text: str) -> list[str]:
        sentences = [part.strip() for part in re.split(r"[。.!?]\s*", text.replace("\n", " ")) if part.strip()]
        if not sentences:
            sentences = [text.strip()]
        return [sentence[:140] for sentence in sentences[:4] if sentence]

    def _markdown_table(self, columns: list[str], rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "| " + " | ".join(columns) + " |\n| " + " | ".join(["---"] * len(columns)) + " |"
        lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
        for row in rows:
            values = [self._table_cell(str(row.get(column, ""))) for column in columns]
            lines.append("| " + " | ".join(values) + " |")
        return "\n".join(lines)

    def _table_cell(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).replace("|", "\\|").strip()

    def _mermaid_text(self, text: str) -> str:
        return text.replace("(", "").replace(")", "").replace(":", " ").replace("#", "") or "item"

    def _mermaid_label(self, text: str) -> str:
        return self._mermaid_text(str(text)).replace('"', "'")[:80] or "item"


generation_service = GenerationService()
