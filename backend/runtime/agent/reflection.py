from __future__ import annotations

import copy
from typing import Any


def reflect(memory: dict[str, Any] | None, result: dict[str, Any]) -> dict[str, Any]:
    memory = copy.deepcopy(memory or {})
    memory.setdefault("reflections", []).append(
        {
            "ok": all(item.get("ok", True) for item in result.get("robot_actions", [])),
            "step": int(((result.get("scene") or {}).get("world_state") or {}).get("step") or 0),
        }
    )
    return memory


__all__ = ["reflect"]
