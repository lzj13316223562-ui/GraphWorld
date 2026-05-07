from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .edges import BaseEdge, SpatialRelation, create_edge
from .nodes import NodeType


@dataclass
class SceneGraph:
    """Lightweight dict-backed scene graph for the static core."""

    scene_name: str
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[BaseEdge] = field(default_factory=list)

    def add_node(self, node_id: str, node_type: NodeType | str, **payload: Any) -> dict[str, Any]:
        node_type_value = NodeType(node_type).value
        node = {
            "id": str(node_id),
            "node_type": node_type_value,
            "states": dict(payload.pop("states", {}) or {}),
            **payload,
        }
        node.setdefault("name", str(node_id))
        self.nodes[str(node_id)] = node
        return node

    def add_edge(self, source_id: str, target_id: str, relation: SpatialRelation | str, **kwargs: Any) -> BaseEdge:
        edge = create_edge(str(source_id), str(target_id), SpatialRelation(relation), **kwargs)
        self.edges.append(edge)
        return edge

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        return self.nodes.get(str(node_id))

    def to_dict(self) -> dict[str, Any]:
        node_list = list(self.nodes.values())
        edge_list = [edge.to_dict() for edge in self.edges]
        return {
            "scene_name": self.scene_name,
            "nodes": node_list,
            "edges": edge_list,
            "node": {str(node["id"]): node for node in node_list if node.get("id")},
            "edge": {
                str(edge.get("id") or f"edge_{idx:06d}"): edge
                for idx, edge in enumerate(edge_list)
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SceneGraph":
        graph = cls(str(data.get("scene_name") or "scene"))
        for node in data.get("nodes") or (data.get("node") or {}).values():
            node_id = str(node.get("id") or "")
            if node_id:
                graph.nodes[node_id] = dict(node)
        for edge in data.get("edges") or (data.get("edge") or {}).values():
            source = str(edge.get("source_id") or "")
            target = str(edge.get("target_id") or "")
            relation = str(edge.get("relation") or "")
            if source and target and relation:
                graph.edges.append(create_edge(source, target, SpatialRelation(relation), **dict(edge.get("properties") or {})))
        return graph


__all__ = ["SceneGraph"]
