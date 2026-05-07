from __future__ import annotations

import copy
from typing import Any


def remember(
    memory: dict[str, Any] | None,
    observation: dict[str, Any],
    action_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    memory = copy.deepcopy(memory or {})
    memory.setdefault("nodes", {})
    memory.setdefault("rooms", {})
    memory.setdefault("events", [])
    step = int((observation.get("world_state") or {}).get("step") or 0)
    for node in observation.get("nodes") or []:
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        stored = copy.deepcopy(node)
        stored["last_seen_step"] = step
        memory["nodes"][node_id] = stored
        if str(node.get("node_type") or "") == "room":
            memory["rooms"][node_id] = stored
    if action_result:
        memory.setdefault("action_results", []).append(copy.deepcopy(action_result))
    memory["last_observation_step"] = step
    return memory


__all__ = ["remember"]
