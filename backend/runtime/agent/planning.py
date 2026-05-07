from __future__ import annotations

from typing import Any


def plan(memory: dict[str, Any], task: str = "maintain_order") -> list[dict[str, Any]]:
    nodes = memory.get("nodes") or {}
    candidates: list[dict[str, Any]] = []
    for node_id, node in sorted(nodes.items()):
        states = node.get("states") or {}
        if str(node.get("door_kind") or "") in {"structural", "device"} and bool(states.get("is_open", False)):
            candidates.append(
                {
                    "action": "close",
                    "target": node_id,
                    "reason": "close open door",
                    "priority": 10,
                }
            )
    for node_id, node in sorted(nodes.items()):
        if bool((node.get("states") or {}).get("is_dirty", False)):
            candidates.append(
                {
                    "action": "brush",
                    "target": node_id,
                    "reason": "clean dirty object",
                    "priority": 8,
                }
            )
    return candidates


__all__ = ["plan"]
