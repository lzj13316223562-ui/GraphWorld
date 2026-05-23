from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    node_type: str = ""
    semantic_type: str = ""
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str
    properties: dict[str, Any] = Field(default_factory=dict)


class SceneGraphResponse(BaseModel):
    scene_version_id: str
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    source_json: dict[str, Any] = Field(default_factory=dict)
