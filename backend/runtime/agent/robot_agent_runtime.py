from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Callable

from ..engine.state import build_runtime_state
from ..eval.scene_evaluator import evaluate_scene
from ..schema.home_schema import normalize_home_scene
from .robot_memory import (
    ensure_robot_memory,
    load_robot_memory,
    summarize_memory,
    update_memory_from_observation,
)
from .robot_observation import (
    DEFAULT_AGENT_DRIVES,
    GAME_OVER_WORLD_SCORE,
    build_robot_observation,
    ensure_scene_robot_stub,
)
from .robot_resoning import DECISION_MODE_LLM, DECISION_MODE_PLANNER_ONLY, decide_next_action
from .robot_executor import execute_robot_action
from .robot_reflation import advance_world_one_step, finalize_reflection


DEFAULT_AGENT_MODEL = "local-qwen3.5-35b"
FIXED_EXPERIMENT_STEPS = 215


def step_robot_agent(
    raw_scene: dict,
    task: dict[str, Any] | str | None,
    runtime_state: dict | None = None,
    agent_id: str = "robot_01",
    agent_model: str = DEFAULT_AGENT_MODEL,
    timeout: int = 30,
    enable_search: bool = False,
    image_path: str | None = None,
    advance_step: bool = True,
    decision_mode: str = DECISION_MODE_LLM,
) -> dict[str, Any]:
    base_scene = normalize_home_scene(copy.deepcopy(raw_scene))
    ensure_scene_robot_stub(base_scene, agent_id)
    ensure_robot_memory(base_scene, agent_id)
    memory = load_robot_memory(base_scene, agent_id)
    observation = build_robot_observation(base_scene, task=task, runtime_state=runtime_state, agent_id=agent_id)
    update_memory_from_observation(memory, observation)
    memory_before = summarize_memory(memory)
    planner_output, reasoning_context, agent_decision = decide_next_action(
        base_scene,
        runtime_state,
        observation,
        memory,
        decision_mode=decision_mode,
        agent_model=agent_model,
        timeout=timeout,
        enable_search=enable_search,
        image_path=image_path,
        memory_summary=memory_before,
    )

    if agent_decision.get("error"):
        action_payload = {"agent": agent_id, "action": None}
        failure_reason = f"invalid_action: {agent_decision.get('error', '')}".strip()
        execution = {
            "ok": False,
            "failed_preconds": [failure_reason] if failure_reason else ["invalid_action"],
            "observation": {},
            "scene": base_scene,
            "runtime_state": runtime_state or build_runtime_state(base_scene),
        }
        execution["agent_action"] = action_payload
        execution["agent_reasoning"] = ""
        execution["agent_raw_response"] = agent_decision.get("raw_response", "")
        execution["agent_observation"] = reasoning_context
        execution["agent_planner"] = planner_output
        execution["agent_memory_before"] = memory_before

        scene_after_action = execution.get("scene") or base_scene
        state_after_action = execution.get("runtime_state")
        execution["scene_after_action"] = copy.deepcopy(scene_after_action)
        execution["runtime_state_after_action"] = copy.deepcopy(state_after_action)

        if advance_step and state_after_action is not None:
            advanced_scene, advanced_state = advance_world_one_step(scene_after_action, state_after_action, agent_id)
            execution["scene"] = advanced_scene
            execution["runtime_state"] = advanced_state
            execution["world_step_advanced"] = True
        else:
            execution["world_step_advanced"] = False

        return finalize_reflection(
            memory=memory,
            agent_id=agent_id,
            action_payload=action_payload,
            agent_reasoning="",
            execution=execution,
            observation=reasoning_context,
        )

    action_payload = {k: v for k, v in agent_decision.items() if k in {"action", "target", "object"}}
    action_payload["agent"] = agent_id
    execution = execute_robot_action(base_scene, action_payload, runtime_state=runtime_state)
    execution["agent_action"] = action_payload
    execution["agent_reasoning"] = agent_decision.get("reasoning", "")
    execution["agent_raw_response"] = agent_decision.get("raw_response", "")
    execution["agent_observation"] = reasoning_context
    execution["agent_planner"] = planner_output
    execution["agent_memory_before"] = memory_before

    scene_after_action = execution.get("scene") or base_scene
    state_after_action = execution.get("runtime_state")
    execution["scene_after_action"] = copy.deepcopy(scene_after_action)
    execution["runtime_state_after_action"] = copy.deepcopy(state_after_action)

    if advance_step and state_after_action is not None:
        advanced_scene, advanced_state = advance_world_one_step(scene_after_action, state_after_action, agent_id)
        execution["scene"] = advanced_scene
        execution["runtime_state"] = advanced_state
        execution["world_step_advanced"] = True
    else:
        execution["world_step_advanced"] = False

    return finalize_reflection(
        memory=memory,
        agent_id=agent_id,
        action_payload=action_payload,
        agent_reasoning=str(agent_decision.get("reasoning") or ""),
        execution=execution,
        observation=reasoning_context,
    )


def _episode_max_steps(scene: dict[str, Any], max_days: int) -> int:
    _ = (scene, max_days)
    return FIXED_EXPERIMENT_STEPS


def run_robot_episode(
    raw_scene: dict,
    task: dict[str, Any] | str | None = None,
    *,
    agent_id: str = "robot_01",
    agent_model: str = DEFAULT_AGENT_MODEL,
    timeout: int = 30,
    enable_search: bool = False,
    image_path: str | None = None,
    max_days: int = 7,
    decision_mode: str = DECISION_MODE_LLM,
    on_step: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    scene = normalize_home_scene(copy.deepcopy(raw_scene))
    ensure_scene_robot_stub(scene, agent_id)
    current_scene = copy.deepcopy(scene)
    current_state: dict[str, Any] | None = None
    replay_steps: list[dict[str, Any]] = []
    max_steps = _episode_max_steps(scene, max_days)
    terminated = False
    termination_reason = ""
    first_below_threshold_step: int | None = None

    for episode_step in range(max_steps):
        result = step_robot_agent(
            current_scene,
            task=task,
            runtime_state=current_state,
            agent_id=agent_id,
            agent_model=agent_model,
            timeout=timeout,
            enable_search=enable_search,
            image_path=image_path,
            advance_step=True,
            decision_mode=decision_mode,
        )
        scene_after = copy.deepcopy(result.get("scene") or current_scene)
        metrics = copy.deepcopy(result.get("scene_metrics") or {})
        world_metrics = metrics.get("world_metrics") or {}
        step_payload = {
            "episode_step": episode_step,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reasoning": result.get("agent_reasoning", ""),
            "reflection": copy.deepcopy(result.get("agent_reflection") or {}),
            "planner": copy.deepcopy(result.get("agent_planner") or {}),
            "action": copy.deepcopy(result.get("agent_action") or {}),
            "ok": bool(result.get("ok", False)),
            "failed_preconds": copy.deepcopy(result.get("failed_preconds") or []),
            "observation": copy.deepcopy(result.get("agent_observation") or {}),
            "memory_before": copy.deepcopy(result.get("agent_memory_before") or {}),
            "memory_after": copy.deepcopy(result.get("agent_memory_after") or {}),
            "event_log": copy.deepcopy(result.get("event_log") or []),
            "scene_metrics": metrics,
            "world_score": float(world_metrics.get("world_score") or 0.0),
            "scene": scene_after,
        }
        replay_steps.append(step_payload)
        if on_step is not None:
            on_step(copy.deepcopy(step_payload))
        current_scene = scene_after
        current_state = copy.deepcopy(result.get("runtime_state"))
        current_world_score = float(world_metrics.get("world_score") or 0.0)
        if first_below_threshold_step is None and current_world_score < GAME_OVER_WORLD_SCORE:
            first_below_threshold_step = int(episode_step)

    if len(replay_steps) >= max_steps:
        terminated = True
        termination_reason = f"fixed_steps_reached_{max_steps}"

    final_metrics = copy.deepcopy(replay_steps[-1]["scene_metrics"]) if replay_steps else evaluate_scene(current_scene)
    return {
        "config": {
            "agent_id": agent_id,
            "agent_model": agent_model,
            "decision_mode": decision_mode,
            "max_days": int(max_days),
            "max_steps": int(max_steps),
            "fixed_experiment_steps": FIXED_EXPERIMENT_STEPS,
            "timeout": int(timeout),
            "game_over_world_score_below": GAME_OVER_WORLD_SCORE,
            "first_below_threshold_step": first_below_threshold_step,
        },
        "task": (
            {"goal": task.strip()} if isinstance(task, str) and task.strip() else {}
        ) if isinstance(task, str) else copy.deepcopy(task or {}),
        "initial_scene_name": str(scene.get("scene_name") or ""),
        "steps": replay_steps,
        "final_scene": current_scene,
        "final_metrics": final_metrics,
        "terminated": terminated,
        "termination_reason": termination_reason,
    }


__all__ = [
    "DECISION_MODE_LLM",
    "DECISION_MODE_PLANNER_ONLY",
    "build_robot_observation",
    "run_robot_episode",
    "step_robot_agent",
]
