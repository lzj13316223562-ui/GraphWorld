from __future__ import annotations

from typing import Any

def node(scene: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for item in scene.get("nodes") or []:
        if item.get("id") == node_id:
            return item
    return None


def room_of(scene: dict[str, Any], node_id: str) -> str:
    current_id = str(node_id or "")
    visited: set[str] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        item = node(scene, current_id)
        if not item:
            return ""
        node_type = str(item.get("node_type") or "")
        if node_type == "room":
            return current_id
        current_id = str(item.get("parent") or "")
    return ""


def relation_of(scene: dict[str, Any], node_id: str) -> str:
    item = node(scene, node_id)
    if not item:
        return ""
    runtime_relation = str(item.get("runtime_relation") or "")
    if runtime_relation:
        return runtime_relation
    parent_id = str(item.get("parent") or "")
    if not parent_id:
        return ""
    for edge in scene.get("edges") or []:
        if str(edge.get("source_id") or "") != parent_id:
            continue
        if str(edge.get("target_id") or "") != str(node_id or ""):
            continue
        relation = str(edge.get("relation") or "")
        if relation:
            return relation
    return "in"


def scene_type(scene: dict[str, Any]) -> str:
    name = str(scene.get("scene_name") or "")
    if "hospital" in name:
        return "hospital"
    if "supermarket" in name:
        return "supermarket"
    if "office" in name:
        return "office"
    if "factory" in name:
        return "factory"
    return "home"
