from __future__ import annotations

import copy
from typing import Any

from backend.runtime.engine import Orchestrator

from .planning import plan


def decide(memory: dict[str, Any], task: str = "maintain_order", agent_id: str = "robot_01") -> dict[str, Any]:
    candidates = plan(memory, task)
    if not candidates:
        return {}
    selected = max(candidates, key=lambda item: int(item.get("priority") or 0))
    action = {key: value for key, value in selected.items() if key != "priority"}
    action.setdefault("agent", agent_id)
    return action


def execute(orchestrator: Orchestrator, action: dict[str, Any], agent_id: str = "robot_01") -> dict[str, Any]:
    if not action:
        return orchestrator.step([], [])
    payload = copy.deepcopy(action)
    payload.setdefault("agent", agent_id)
    return orchestrator.step([payload], [])


__all__ = ["decide", "execute"]
