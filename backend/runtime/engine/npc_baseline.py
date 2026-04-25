from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Callable

from ..eval.scene_evaluator import evaluate_scene
from ..schema.home_schema import normalize_home_scene, set_scene_graph
from ..world.environment import apply_environment_step, ensure_world_environment
from ..world.npc_runtime import apply_npc_routines
from ..world.rules import apply_runtime_rules
from .state import build_runtime_state


GAME_OVER_WORLD_SCORE = 0.60
FIXED_EXPERIMENT_STEPS = 215


def _current_step(world_state: dict[str, Any]) -> int:
    return int(world_state.get("step") or 0)


def _current_time_min(world_state: dict[str, Any]) -> int:
    return int(world_state.get("time_min") or 0)


def _minutes_per_step(world_state: dict[str, Any]) -> int:
    return max(1, int(world_state.get("minutes_per_step") or 10))


def _episode_max_steps(scene: dict[str, Any], max_days: int) -> int:
    _ = (scene, max_days)
    return FIXED_EXPERIMENT_STEPS


def _dynamic_edges(state: dict) -> list[dict[str, Any]]:
    edges = []
    nodes = state["nodes"]
    for node_id, parent_id in state["parent_of"].items():
        if parent_id == "outside_home":
            continue
        if node_id not in nodes or parent_id not in nodes:
            continue
        node = nodes[node_id]
        relation = str(((node.get("runtime") or {}).get("relation")) or "in")
        category = "containment"
        edge_type = "containment_edge"
        if relation in {"inside_room", "part_of"}:
            category = "structural"
            edge_type = "structural_edge"
        edges.append(
            {
                "source_id": parent_id,
                "target_id": node_id,
                "edge_type": edge_type,
                "relation": relation,
                "category": category,
                "properties": {"runtime": True},
            }
        )
    return edges


def _state_to_scene(raw_scene: dict[str, Any], state: dict) -> dict[str, Any]:
    scene = copy.deepcopy(raw_scene)
    set_scene_graph(
        scene,
        list(state["nodes"].values()),
        state["structural_edges"] + state["control_edges"] + _dynamic_edges(state),
    )
    scene.setdefault("world_state", {})
    scene["world_state"].update(copy.deepcopy(state.get("world_state") or {}))
    scene["world_state"]["event_log"] = copy.deepcopy(state.get("logs") or [])
    return scene


def run_npc_baseline_episode(
    raw_scene: dict[str, Any],
    *,
    max_days: int = 7,
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    scene = normalize_home_scene(copy.deepcopy(raw_scene))
    state = build_runtime_state(scene)
    ensure_world_environment(state.setdefault("world_state", {}))

    current_scene = _state_to_scene(scene, state)
    replay_steps: list[dict[str, Any]] = []
    max_steps = _episode_max_steps(scene, max_days)
    terminated = False
    termination_reason = ""
    first_below_threshold_step: int | None = None

    for episode_step in range(max_steps):
        world_state = state.setdefault("world_state", {})
        next_step = _current_step(world_state) + 1
        world_state["step"] = next_step
        world_state["time_min"] = _current_time_min(world_state) + _minutes_per_step(world_state)
        if world_state["time_min"] >= 24 * 60:
            world_state["day"] = int(world_state.get("day") or 1) + (world_state["time_min"] // (24 * 60))
            world_state["time_min"] = world_state["time_min"] % (24 * 60)

        apply_npc_routines(state, next_step)
        apply_runtime_rules(state, next_step)
        apply_environment_step(state, next_step)

        current_scene = _state_to_scene(scene, state)
        metrics = evaluate_scene(current_scene)
        world_metrics = metrics.get("world_metrics") or {}

        step_payload = {
            "episode_step": episode_step,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reasoning": "npc_only_baseline",
            "planner": {
                "mode": "npc_only_baseline",
                "subgoal": "advance world without robot intervention",
                "candidate_actions": [],
            },
            "action": {
                "agent": "npc_only",
                "action": "noop",
            },
            "ok": True,
            "failed_preconds": [],
            "observation": {},
            "memory_before": {},
            "memory_after": {},
            "event_log": copy.deepcopy(current_scene.get("world_state", {}).get("event_log") or []),
            "scene_metrics": copy.deepcopy(metrics),
            "world_score": float(world_metrics.get("world_score") or 0.0),
            "scene": copy.deepcopy(current_scene),
        }
        replay_steps.append(step_payload)
        if on_step is not None:
            on_step(copy.deepcopy(step_payload))

        if (
            first_below_threshold_step is None
            and float(world_metrics.get("world_score") or 0.0) < GAME_OVER_WORLD_SCORE
        ):
            first_below_threshold_step = int(episode_step)

    final_metrics = copy.deepcopy(replay_steps[-1]["scene_metrics"]) if replay_steps else evaluate_scene(current_scene)
    if len(replay_steps) >= max_steps:
        terminated = True
        termination_reason = f"fixed_steps_reached_{max_steps}"
    return {
        "config": {
            "agent_id": "npc_only",
            "agent_model": "npc_only_baseline",
            "max_days": int(max_days),
            "max_steps": int(max_steps),
            "fixed_experiment_steps": FIXED_EXPERIMENT_STEPS,
            "timeout": 0,
            "game_over_world_score_below": GAME_OVER_WORLD_SCORE,
            "first_below_threshold_step": first_below_threshold_step,
        },
        "task": {"goal": "npc_only_baseline"},
        "initial_scene_name": str(scene.get("scene_name") or ""),
        "steps": replay_steps,
        "final_scene": current_scene,
        "final_metrics": final_metrics,
        "terminated": terminated,
        "termination_reason": termination_reason,
    }


__all__ = ["run_npc_baseline_episode"]
