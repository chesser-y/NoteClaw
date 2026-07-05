from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from noteclaw_backend.domain.enums import ContentType, GenerationType, NoteStatus, SearchMode, TaskStatus, TaskType
from noteclaw_backend.schemas.common import Artifact, Citation, new_id, utc_now
from noteclaw_backend.schemas.generation import (
    GenerationPreviewResponse,
    GenerationRequest,
    GenerationTaskResponse,
)
from noteclaw_backend.schemas.knowledge import NoteDetail
from noteclaw_backend.services.html_renderer import render_slide_html
from noteclaw_backend.services.html_screenshot import html_batch_to_png, shutdown_browser
from noteclaw_backend.services.providers import get_image_provider, get_llm_provider
from noteclaw_backend.services.retrieval import retrieval_service
from noteclaw_backend.services.slide_layout_agent import decide_slide_layouts
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
        note_id: str | None = None
        try:
            note_id = await self._persist_generation_note(request, content, citations)
        except Exception:
            # Persistence is best-effort; never block the preview response.
            pass
        download_url = f"/api/knowledge/{note_id}/file" if note_id else None
        artifact_url = self._extract_artifact_url(content) if isinstance(content, dict) else None
        document_extension = self._document_extension_for(request.generation_type, content)
        return GenerationPreviewResponse(
            generation_type=request.generation_type,
            content=content,
            citations=citations,
            note_id=note_id,
            artifact_url=artifact_url,
            download_url=download_url,
            document_extension=document_extension,
        )

    def _extract_artifact_url(self, content: dict[str, Any]) -> str | None:
        artifact = content.get("artifact")
        if isinstance(artifact, dict):
            url = artifact.get("url")
            if isinstance(url, str):
                return url
        return None

    def _document_extension_for(self, gtype: GenerationType, content: dict[str, Any] | str) -> str | None:
        """File extension to use when persisting this generation as a downloadable document."""
        if gtype == GenerationType.PPTX:
            return "pptx"
        if gtype == GenerationType.IMAGE:
            return None  # image_url is remote; no local file
        if gtype in {GenerationType.MIND_MAP, GenerationType.DIAGRAM}:
            return "mmd"
        if gtype == GenerationType.TABLE:
            return "md"
        # All other markdown-shaped outputs
        return "md"

    async def _persist_generation_note(
        self,
        request: GenerationRequest,
        content: dict[str, Any] | str,
        citations: list[Citation],
    ) -> str | None:
        """Persist a generation output as a note so it shows up in Library / Graph / Research."""
        from noteclaw_backend.storage.repositories import get_repository

        gtype = request.generation_type
        title = self._derive_generation_title(request, content)
        markdown, content_type, stored_path, extra_meta = self._serialize_generation_content(gtype, content)

        # For text/markdown/mermaid outputs without an existing artifact, write the
        # body to a real file so the user can download an actual document.
        if stored_path is None:
            extension = self._document_extension_for(gtype, content)
            if extension and markdown:
                stored_path = self._write_document_file(title, markdown, extension)
                extra_meta = {**(extra_meta or {}), "document_extension": extension}

        citation_tag = f"gen:{gtype.value}"
        tags = ["generation", citation_tag]
        theme = request.options.theme
        if theme:
            tags.append(theme)

        now = utc_now()
        metadata: dict[str, Any] = {
            "generation_type": gtype.value,
            "prompt": request.prompt[:400],
            "citation_count": len(citations),
            "citation_note_ids": [c.note_id for c in citations[:8]],
        }
        if stored_path is not None:
            metadata["stored_path"] = str(stored_path)
        if extra_meta:
            metadata.update(extra_meta)

        note = NoteDetail(
            id=new_id("note"),
            title=title,
            content_type=content_type,
            content=markdown,
            summary=self._summary_from_markdown(markdown),
            tags=tags,
            category="generation",
            source="generation",
            source_url=None,
            status=NoteStatus.READY,
            created_at=now,
            updated_at=now,
            metadata=metadata,
            chunks=[],
        )
        await get_repository().create_note(note)
        return note.id

    def _write_document_file(self, title: str, body: str, extension: str) -> Path:
        out_dir = get_settings().storage_dir / "generated"
        out_dir.mkdir(parents=True, exist_ok=True)
        doc_id = new_id("doc")
        safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", title or "document")[:50] or "document"
        path = out_dir / f"{doc_id}_{safe_title}.{extension}"
        path.write_text(body, encoding="utf-8")
        return path

    def _derive_generation_title(self, request: GenerationRequest, content: dict[str, Any] | str) -> str:
        if isinstance(content, dict):
            for key in ("title",):
                value = content.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()[:140]
            inner = content.get("outline")
            if isinstance(inner, dict) and isinstance(inner.get("title"), str):
                return inner["title"].strip()[:140]
        label = request.generation_type.value.replace("_", " ")
        return f"{label.title()} · {request.prompt.strip()[:80]}"

    def _summary_from_markdown(self, markdown: str) -> str:
        text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", markdown)
        text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:200]

    def _serialize_generation_content(
        self,
        gtype: GenerationType,
        content: dict[str, Any] | str,
    ) -> tuple[str, ContentType, Path | None, dict[str, Any]]:
        """Convert a generation payload into (markdown_body, content_type, optional file path, extra metadata)."""
        if isinstance(content, str):
            ctype = ContentType.CODE if gtype in {GenerationType.MIND_MAP, GenerationType.DIAGRAM} else ContentType.TEXT
            return content, ctype, None, {}

        if gtype == GenerationType.PPTX:
            outline = content.get("outline") or {}
            artifact = content.get("artifact") or {}
            stored_path_str = artifact.get("url") if isinstance(artifact, dict) else None
            stored_path = Path(stored_path_str) if stored_path_str else None
            slide_images = content.get("slide_images") or []
            markdown = self._ppt_outline_to_markdown(outline)
            extra: dict[str, Any] = {
                "slide_count": len(outline.get("slides") or []),
                "slide_images": [str(p) for p in slide_images] if slide_images else [],
                "renderer": artifact.get("metadata", {}).get("renderer") if isinstance(artifact, dict) else None,
                "artifact_url": stored_path_str,
            }
            return markdown, ContentType.DOCUMENT, stored_path, extra

        if gtype == GenerationType.PPT_OUTLINE:
            outline = content if isinstance(content, dict) else {}
            return self._ppt_outline_to_markdown(outline), ContentType.TEXT, None, {}

        if gtype == GenerationType.TABLE:
            markdown = content.get("markdown") if isinstance(content, dict) else ""
            return str(markdown or ""), ContentType.TABLE, None, {}

        if gtype == GenerationType.VIDEO_SCRIPT:
            markdown = content.get("markdown") if isinstance(content, dict) else ""
            return str(markdown or json.dumps(content, ensure_ascii=False, indent=2)), ContentType.TEXT, None, {}

        if gtype == GenerationType.IMAGE:
            data = content if isinstance(content, dict) else {}
            prompt = str(data.get("prompt") or "")
            url = data.get("url")
            md_lines = [f"# Image prompt", "", prompt]
            if url:
                md_lines += ["", f"![generated image]({url})"]
            extra_meta: dict[str, Any] = {"image_prompt": prompt[:600]}
            if url:
                extra_meta["image_url"] = url
            return "\n".join(md_lines), ContentType.IMAGE, None, extra_meta

        # Fallback: dump as pretty JSON inside a fenced block.
        body = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2)
        return f"```json\n{body}\n```", ContentType.TEXT, None, {}

    def _ppt_outline_to_markdown(self, outline: dict[str, Any]) -> str:
        title = str(outline.get("title") or "Untitled deck").strip()
        slides = list(outline.get("slides") or [])
        lines = [f"# {title}", ""]
        for idx, slide in enumerate(slides, start=1):
            slide_title = str(slide.get("title") or f"Slide {idx}").strip()
            lines.append(f"## {idx}. {slide_title}")
            layout = slide.get("layout")
            if layout:
                lines.append(f"_layout: {layout}_")
            for key in ("bullets", "points", "subtitle"):
                bullets = slide.get(key)
                if not bullets:
                    continue
                if isinstance(bullets, str):
                    bullets = [bullets]
                for b in bullets:
                    lines.append(f"- {b}")
            lines.append("")
        return "\n".join(lines)

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

        deck_meta = {
            "title": outline.get("title") or request.prompt[:80],
            "label": outline.get("title") or "NoteClaw Deck",
            "author": "Generated by NoteClaw",
        }
        slides = list(outline.get("slides") or [])
        layouts = await decide_slide_layouts(slides, deck_title=deck_meta["title"])

        # Build HTML for each slide (always — used for preview + PNG render)
        html_strings: list[str] = []
        for idx, (slide, layout) in enumerate(zip(slides, layouts), start=1):
            html_strings.append(render_slide_html(slide, layout, deck_meta, idx))

        artifact, warning, slide_images = await self._write_pptx_from_html(outline, html_strings)

        return {
            "outline": outline,
            "html_slides": html_strings,
            "slide_images": [str(p) for p in slide_images] if slide_images else [],
            "layouts": layouts,
            "artifact": artifact.model_dump(mode="json") if artifact else None,
            "warning": warning,
        }

    async def _write_pptx_from_html(
        self,
        outline: dict[str, Any],
        html_strings: list[str],
    ) -> tuple[Artifact | None, str | None, list[Path]]:
        """Try HTML→PNG→python-pptx; fall back to legacy direct-write if Playwright missing."""
        if html_strings:
            png_paths = await self._render_html_slides(html_strings, outline.get("title") or "deck")
            if png_paths:
                artifact = self._write_pptx_from_images(png_paths)
                if artifact is not None:
                    return artifact, None, list(png_paths)
                return None, "HTML→PNG rendered but PPTX assembly failed", list(png_paths)
            # PNG render failed entirely → fall back to legacy writer
            legacy_artifact, legacy_warning = self._write_pptx(outline)
            warning = f"playwright unavailable, fell back to plain PPTX; {legacy_warning or ''}".strip("; ")
            return legacy_artifact, warning, []

        # No HTML slides (empty outline?) — try legacy
        artifact, warning = self._write_pptx(outline)
        return artifact, warning, []

    async def _render_html_slides(self, html_strings: list[str], title: str) -> list[Any]:
        storage = get_settings().storage_dir / "slide_images"
        storage.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", str(title))[:40] or "deck"
        items = []
        for idx, html in enumerate(html_strings, start=1):
            out_path = storage / f"{safe_title}_{idx:02d}.png"
            items.append((html, out_path))
        return await html_batch_to_png(items)

    def _write_pptx_from_images(self, png_paths: list[Any]) -> Artifact | None:
        try:
            from pptx import Presentation  # type: ignore
            from pptx.util import Inches  # type: ignore
        except Exception as exc:  # noqa: BLE001
            return None

        try:
            presentation = Presentation()
            presentation.slide_width = Inches(13.333)  # 16:9 widescreen
            presentation.slide_height = Inches(7.5)
            blank_layout = presentation.slide_layouts[6]

            for png in png_paths:
                slide = presentation.slides.add_slide(blank_layout)
                slide.shapes.add_picture(
                    str(png),
                    left=0,
                    top=0,
                    width=presentation.slide_width,
                    height=presentation.slide_height,
                )

            output_dir = get_settings().storage_dir / "generated"
            output_dir.mkdir(parents=True, exist_ok=True)
            artifact_id = new_id("artifact")
            safe_title = f"deck_{artifact_id[-8:]}"
            path = output_dir / f"{artifact_id}_{safe_title}.pptx"
            presentation.save(path)
            return Artifact(
                id=artifact_id,
                type="pptx",
                name=path.name,
                url=str(path),
                metadata={
                    "slide_count": len(presentation.slides),
                    "renderer": "html_to_png",
                },
            )
        except Exception:
            return None

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
