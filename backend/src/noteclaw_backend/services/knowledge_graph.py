from __future__ import annotations

import itertools
import re
from collections import Counter, defaultdict
from typing import Any

from noteclaw_backend.schemas.knowledge import NoteListItem
from noteclaw_backend.schemas.knowledge_graph import (
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    KnowledgeGraphResponse,
    KnowledgeGraphStats,
)
from noteclaw_backend.storage.repositories import get_repository


class KnowledgeGraphService:
    async def build_graph(
        self,
        *,
        include_notes: bool = True,
        include_categories: bool = True,
        include_content_types: bool = True,
        min_tag_count: int = 1,
        min_edge_weight: int = 1,
        limit_tags: int = 80,
        limit_notes: int = 300,
        focus_tag: str | None = None,
    ) -> KnowledgeGraphResponse:
        notes = await self._load_notes(limit_notes)
        note_tags = {note.id: self._clean_tags(note.tags) for note in notes}
        tag_counts = Counter(tag for tags in note_tags.values() for tag in tags)
        allowed_tags = self._allowed_tags(
            tag_counts,
            min_tag_count=min_tag_count,
            limit_tags=limit_tags,
            focus_tag=focus_tag,
        )
        if focus_tag:
            notes = [note for note in notes if allowed_tags.intersection(note_tags.get(note.id, []))]

        nodes: dict[str, KnowledgeGraphNode] = {}
        edges: dict[str, KnowledgeGraphEdge] = {}
        tag_note_ids: dict[str, list[str]] = defaultdict(list)

        for note in notes:
            tags = [tag for tag in note_tags.get(note.id, []) if tag in allowed_tags]
            if not tags:
                continue
            for tag in tags:
                tag_note_ids[tag].append(note.id)
            if include_notes:
                self._upsert_node(
                    nodes,
                    KnowledgeGraphNode(
                        id=self._node_id("note", note.id),
                        label=note.title,
                        type="note",
                        weight=float(len(tags)),
                        metadata={
                            "note_id": note.id,
                            "summary": note.summary,
                            "category": note.category,
                            "content_type": note.content_type.value,
                            "source": note.source,
                            "source_url": note.source_url,
                            "tags": tags,
                        },
                    ),
                )
            if include_categories and note.category:
                self._upsert_node(
                    nodes,
                    KnowledgeGraphNode(
                        id=self._node_id("category", note.category),
                        label=note.category,
                        type="category",
                        weight=1,
                        metadata={"category": note.category},
                    ),
                    increment=1,
                )
            if include_content_types:
                self._upsert_node(
                    nodes,
                    KnowledgeGraphNode(
                        id=self._node_id("content_type", note.content_type.value),
                        label=note.content_type.value,
                        type="content_type",
                        weight=1,
                        metadata={"content_type": note.content_type.value},
                    ),
                    increment=1,
                )

            for tag in tags:
                if include_notes:
                    self._merge_edge(
                        edges,
                        source=self._node_id("note", note.id),
                        target=self._node_id("tag", tag),
                        edge_type="has_tag",
                        note_id=note.id,
                    )
                if include_categories and note.category:
                    self._merge_edge(
                        edges,
                        source=self._node_id("category", note.category),
                        target=self._node_id("tag", tag),
                        edge_type="category_tag",
                        note_id=note.id,
                    )
                if include_content_types:
                    self._merge_edge(
                        edges,
                        source=self._node_id("content_type", note.content_type.value),
                        target=self._node_id("tag", tag),
                        edge_type="content_type_tag",
                        note_id=note.id,
                    )
            for left, right in itertools.combinations(sorted(set(tags)), 2):
                self._merge_edge(
                    edges,
                    source=self._node_id("tag", left),
                    target=self._node_id("tag", right),
                    edge_type="tag_cooccurs",
                    note_id=note.id,
                )

        for tag, count in tag_counts.items():
            if tag not in allowed_tags:
                continue
            self._upsert_node(
                nodes,
                KnowledgeGraphNode(
                    id=self._node_id("tag", tag),
                    label=tag,
                    type="tag",
                    weight=float(count),
                    metadata={"note_ids": tag_note_ids.get(tag, []), "note_count": len(tag_note_ids.get(tag, []))},
                ),
            )

        filtered_edges = [edge for edge in edges.values() if edge.weight >= min_edge_weight]
        if focus_tag:
            focus_id = self._node_id("tag", self._normalize_tag(focus_tag))
            filtered_edges = [edge for edge in filtered_edges if edge.source == focus_id or edge.target == focus_id]
            connected = {focus_id}
            for edge in filtered_edges:
                connected.add(edge.source)
                connected.add(edge.target)
            nodes = {node_id: node for node_id, node in nodes.items() if node_id in connected}

        ordered_nodes = sorted(nodes.values(), key=lambda node: (node.type != "tag", -node.weight, node.label.lower()))
        ordered_edges = sorted(filtered_edges, key=lambda edge: (-edge.weight, edge.type, edge.source, edge.target))
        stats = KnowledgeGraphStats(
            note_count=len({node.id for node in ordered_nodes if node.type == "note"}),
            tag_count=len({node.id for node in ordered_nodes if node.type == "tag"}),
            category_count=len({node.id for node in ordered_nodes if node.type == "category"}),
            content_type_count=len({node.id for node in ordered_nodes if node.type == "content_type"}),
            edge_count=len(ordered_edges),
            max_tag_weight=max((node.weight for node in ordered_nodes if node.type == "tag"), default=0.0),
            max_edge_weight=max((edge.weight for edge in ordered_edges), default=0.0),
        )
        return KnowledgeGraphResponse(nodes=ordered_nodes, edges=ordered_edges, stats=stats)

    async def _load_notes(self, limit: int) -> list[NoteListItem]:
        notes: list[NoteListItem] = []
        offset = 0
        page_size = min(max(limit, 1), 100)
        while len(notes) < limit:
            page, total = await get_repository().list_notes(limit=page_size, offset=offset)
            notes.extend(page)
            offset += len(page)
            if not page or offset >= total:
                break
        return notes[:limit]

    def _allowed_tags(
        self,
        tag_counts: Counter[str],
        *,
        min_tag_count: int,
        limit_tags: int,
        focus_tag: str | None,
    ) -> set[str]:
        focus = self._normalize_tag(focus_tag) if focus_tag else None
        ranked = [
            tag
            for tag, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))
            if count >= min_tag_count
        ]
        allowed = set(ranked[:limit_tags])
        if focus and focus in tag_counts:
            allowed.add(focus)
        return allowed

    def _clean_tags(self, tags: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            normalized = self._normalize_tag(tag)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(normalized)
        return cleaned

    def _normalize_tag(self, tag: str | None) -> str:
        if not tag:
            return ""
        tag = re.sub(r"\s+", " ", str(tag)).strip().lower()
        return tag[:80]

    def _node_id(self, node_type: str, value: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9_\-:.\u4e00-\u9fff]+", "_", str(value).strip().lower()).strip("_")
        return f"{node_type}:{cleaned or 'unknown'}"

    def _upsert_node(
        self,
        nodes: dict[str, KnowledgeGraphNode],
        node: KnowledgeGraphNode,
        *,
        increment: float = 0.0,
    ) -> None:
        existing = nodes.get(node.id)
        if existing is None:
            nodes[node.id] = node
            return
        if increment:
            nodes[node.id] = existing.model_copy(update={"weight": existing.weight + increment})

    def _merge_edge(
        self,
        edges: dict[str, KnowledgeGraphEdge],
        *,
        source: str,
        target: str,
        edge_type: str,
        note_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if source == target:
            return
        left, right = sorted([source, target]) if edge_type == "tag_cooccurs" else [source, target]
        edge_id = f"{edge_type}:{left}->{right}"
        existing = edges.get(edge_id)
        if existing is None:
            edges[edge_id] = KnowledgeGraphEdge(
                id=edge_id,
                source=left,
                target=right,
                type=edge_type,
                weight=1,
                note_ids=[note_id],
                metadata=metadata or {},
            )
            return
        note_ids = existing.note_ids if note_id in existing.note_ids else [*existing.note_ids, note_id]
        edges[edge_id] = existing.model_copy(update={"weight": existing.weight + 1, "note_ids": note_ids})


knowledge_graph_service = KnowledgeGraphService()
