from __future__ import annotations

from typing import Any

from backend.runtime.engine import Orchestrator


def perceive(orchestrator: Orchestrator, agent_id: str = "robot_01") -> dict[str, Any]:
    return orchestrator.perception.robot_view(agent_id)


__all__ = ["perceive"]
