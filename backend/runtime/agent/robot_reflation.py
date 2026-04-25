from __future__ import annotations

import copy
from typing import Any

from ..eval.scene_evaluator import evaluate_scene
from ..world.environment import apply_environment_step, ensure_world_environment
from ..world.npc_runtime import apply_npc_routines
from ..world.rules import apply_runtime_rules
from .robot_executor import _state_to_scene
from .robot_memory import (
    consolidate_experience,
    remember_action_result,
    reflect_on_feedback,
    save_robot_memory,
    summarize_memory,
)
from .robot_observation import GAME_OVER_WORLD_SCORE, current_step, current_time_min, minutes_per_step


def _normalized_top_issues(metrics: dict[str, Any]) -> list[str]:
    return [str(item).strip() for item in list(metrics.get("top_issues") or []) if str(item).strip()]


def _simple_reflection(
    *,
    action_payload: dict[str, Any],
    ok: bool,
    failed_preconds: list[str],
    before_world_score: float,
    before_issues: list[str],
    after_metrics: dict[str, Any],
    step: int,
    recent_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    after_world_score = float(((after_metrics.get("world_metrics") or {}).get("world_score") or 0.0))
    after_issues = _normalized_top_issues(after_metrics)
    resolved = [issue for issue in before_issues if issue not in after_issues]
    action_key = (
        str(action_payload.get("action") or ""),
        str(action_payload.get("target") or action_payload.get("object") or ""),
    )
    tail = list(recent_actions or [])[-3:]
    repeated_ineffective = False
    if len(tail) >= 2:
        recent_same = [
            item
            for item in tail
            if (
                str(((item.get("action") or {}).get("action") or "")),
                str(((item.get("action") or {}).get("target") or (item.get("action") or {}).get("object") or "")),
            )
            == action_key
        ]
        if len(recent_same) >= 2 and after_world_score <= before_world_score and not resolved:
            repeated_ineffective = True

    return {
        "step": int(step),
        "action_type": str(action_payload.get("action") or ""),
        "target": str(action_payload.get("target") or action_payload.get("object") or ""),
        "ok": bool(ok),
        "failed_preconds": list(failed_preconds or []),
        "score_became_better": after_world_score > before_world_score,
        "score_delta": round(after_world_score - before_world_score, 4),
        "resolved_issues": resolved[:5],
        "resolved_issue_count": len(resolved),
        "repeated_ineffective": repeated_ineffective,
    }


def advance_world_one_step(scene: dict, runtime_state: dict, agent_id: str) -> tuple[dict, dict]:
    state = copy.deepcopy(runtime_state)
    world_state = state.setdefault("world_state", {})
    ensure_world_environment(world_state)
    next_step = current_step(world_state) + 1
    world_state["step"] = next_step
    world_state["time_min"] = current_time_min(world_state) + minutes_per_step(world_state)
    if world_state["time_min"] >= 24 * 60:
        world_state["day"] = int(world_state.get("day") or 1) + (world_state["time_min"] // (24 * 60))
        world_state["time_min"] = world_state["time_min"] % (24 * 60)

    apply_npc_routines(state, next_step)
    apply_runtime_rules(state, next_step)
    apply_environment_step(state, next_step)

    updated_scene = _state_to_scene(scene, state, agent_id)
    updated_scene.setdefault("world_state", {}).update(copy.deepcopy(world_state))
    updated_scene.setdefault("world_state", {})["event_log"] = copy.deepcopy(state.get("logs") or [])
    return updated_scene, state


def finalize_reflection(
    *,
    memory,
    agent_id: str,
    action_payload: dict[str, Any],
    agent_reasoning: str,
    execution: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    recent_actions_before = copy.deepcopy(list((memory.working_memory.get("recent_actions") or [])))
    scene_after_action = execution.get("scene_after_action") or execution.get("scene") or {}
    action_metrics = evaluate_scene(scene_after_action)
    action_world_score = float(((action_metrics.get("world_metrics") or {}).get("world_score") or 0.0))
    final_scene = execution.get("scene") or scene_after_action
    final_metrics = evaluate_scene(final_scene)
    final_world_score = float(((final_metrics.get("world_metrics") or {}).get("world_score") or 0.0))
    step = int((final_scene.get("world_state") or {}).get("step") or (observation.get("world") or {}).get("step") or 0)
    world_score_before = float((observation.get("scores") or {}).get("world_score") or 0.0)
    top_issues_before: list[str] = []
    planner_goal = str(((execution.get("agent_planner") or {}).get("intent") or "")).strip()

    immediate_reflection = reflect_on_feedback(
        memory,
        action=action_payload,
        reasoning=agent_reasoning,
        ok=bool(execution.get("ok", False)),
        failed_preconds=list(execution.get("failed_preconds") or []),
        world_score_before=world_score_before,
        world_score_after=action_world_score,
        step=step,
        phase="after_action",
    )
    world_reflection = None
    if bool(execution.get("world_step_advanced")):
        world_reflection = reflect_on_feedback(
            memory,
            action=action_payload,
            reasoning=agent_reasoning,
            ok=bool(execution.get("ok", False)),
            failed_preconds=list(execution.get("failed_preconds") or []),
            world_score_before=action_world_score,
            world_score_after=final_world_score,
            step=step,
            phase="after_world_step",
        )

    remember_action_result(
        memory,
        action=action_payload,
        reasoning=agent_reasoning,
        plan_goal=planner_goal,
        ok=bool(execution.get("ok", False)),
        failed_preconds=list(execution.get("failed_preconds") or []),
        world_score_before=world_score_before,
        world_score_after_action=action_world_score,
        world_score_after_world_step=final_world_score if bool(execution.get("world_step_advanced")) else None,
        observation=copy.deepcopy(execution.get("observation") or {}),
        step=step,
    )
    experience_summary = consolidate_experience(
        memory,
        action=action_payload,
        plan_goal=planner_goal,
        ok=bool(execution.get("ok", False)),
        failed_preconds=list(execution.get("failed_preconds") or []),
        immediate_reflection=immediate_reflection,
        world_reflection=world_reflection,
        step=step,
    )

    save_robot_memory(final_scene, agent_id, memory)
    simple_reflection = _simple_reflection(
        action_payload=action_payload,
        ok=bool(execution.get("ok", False)),
        failed_preconds=list(execution.get("failed_preconds") or []),
        before_world_score=world_score_before,
        before_issues=top_issues_before,
        after_metrics=final_metrics,
        step=step,
        recent_actions=recent_actions_before,
    )
    execution["agent_memory_after"] = summarize_memory(memory)
    execution["agent_reflection"] = simple_reflection
    execution["agent_reflection_debug"] = {
        "after_action": immediate_reflection,
        "after_world_step": world_reflection,
        "experience_summary": experience_summary,
    }
    execution["scene_metrics_after_action"] = action_metrics
    execution["scene_metrics"] = final_metrics
    execution["game_over"] = final_world_score < GAME_OVER_WORLD_SCORE
    execution["game_over_reason"] = f"world_score_below_{GAME_OVER_WORLD_SCORE:.2f}" if execution["game_over"] else ""
    return execution


__all__ = ["advance_world_one_step", "finalize_reflection"]
