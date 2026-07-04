from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeGraphNode(BaseModel):
    id: str
    label: str
    type: str
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    weight: float = 1.0
    note_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphStats(BaseModel):
    note_count: int = 0
    tag_count: int = 0
    category_count: int = 0
    content_type_count: int = 0
    edge_count: int = 0
    max_tag_weight: float = 0.0
    max_edge_weight: float = 0.0


class KnowledgeGraphResponse(BaseModel):
    nodes: list[KnowledgeGraphNode] = Field(default_factory=list)
    edges: list[KnowledgeGraphEdge] = Field(default_factory=list)
    stats: KnowledgeGraphStats = Field(default_factory=KnowledgeGraphStats)
