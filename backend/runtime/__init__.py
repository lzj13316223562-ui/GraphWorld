from __future__ import annotations

from typing import Any

from .engine import Orchestrator, run_runtime
from .eval import build_matrix_snapshot, matrix_score


def simulate_scene(
    scene: dict[str, Any],
    steps: int = 1,
    *,
    robot_actions_by_step: list[list[dict[str, Any]]] | None = None,
    human_events_by_step: list[list[str | dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return run_runtime(
        scene,
        steps,
        robot_actions_by_step=robot_actions_by_step,
        human_events_by_step=human_events_by_step,
    )["scene"]


def evaluate_scene(
    scene: dict[str, Any],
    baseline_scene: dict[str, Any] | None = None,
    previous_scene: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = build_matrix_snapshot(scene)
    baseline = build_matrix_snapshot(baseline_scene or scene)
    previous = build_matrix_snapshot(previous_scene) if previous_scene else None
    return {"world_metrics": matrix_score(current, baseline, previous)}


__all__ = ["Orchestrator", "evaluate_scene", "run_runtime", "simulate_scene"]
