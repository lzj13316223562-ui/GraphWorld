from __future__ import annotations

import copy
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from torch.utils.tensorboard import SummaryWriter

from backend.replay_store import (
    EXPERIMENT_PURE_HUMAN,
    ReplayStore,
    canonical_run_name,
    experiment_label,
)
from backend.runtime.agent.robot_agent_runtime import FIXED_EXPERIMENT_STEPS
from backend.runtime.agent.robot_executor import execute_robot_action, validate_robot_action
from backend.runtime.agent.robot_memory import (
    RobotMemory,
    load_robot_memory,
    save_robot_memory,
    summarize_memory,
    update_memory_from_observation,
)
from backend.runtime.agent.robot_observation import build_robot_observation, ensure_scene_robot_stub
from backend.runtime.agent.robot_reflation import advance_world_one_step
from backend.runtime.agent.robot_resoning import ALLOWED_ACTIONS
from backend.runtime.engine.state import build_runtime_state, is_room_door_node
from backend.runtime.eval.scene_evaluator import evaluate_scene
from backend.runtime.schema.home_schema import canonical_node_type, canonical_semantic_type, normalize_home_scene, scene_nodes


def _room_nodes(scene: dict[str, Any]) -> list[dict[str, Any]]:
    return [node for node in (scene.get("nodes") or []) if canonical_node_type(node) == "room"]


def _fixed_object_nodes(scene: dict[str, Any]) -> list[dict[str, Any]]:
    return [node for node in (scene.get("nodes") or []) if canonical_node_type(node) == "fixed_object"]


def _spawn_options(scene: dict[str, Any], runtime_state: dict[str, Any]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for room in _room_nodes(scene):
        room_id = str(room.get("id") or "")
        if room_id:
            options.append({"anchor_id": room_id, "room_id": room_id, "anchor_kind": "room"})
    for node in _fixed_object_nodes(scene):
        anchor_id = str(node.get("id") or "")
        room_id = str((runtime_state.get("room_of") or {}).get(anchor_id) or "")
        actions = {str(action).lower() for action in (node.get("interactive_actions") or [])}
        semantic = canonical_semantic_type(node)
        if semantic in {"button", "knob", "faucet", "light", "room_light"}:
            continue
        if semantic == "door" and not is_room_door_node((runtime_state.get("nodes") or {}).get(anchor_id) or {}):
            continue
        if anchor_id and room_id and "move" in actions:
            options.append({"anchor_id": anchor_id, "room_id": room_id, "anchor_kind": "fixed_object"})
    return options


def _edge_category(relation: str) -> tuple[str, str]:
    lowered = str(relation or "").lower()
    if lowered == "controls":
        return ("control", "control_edge")
    if lowered == "adjacent_to":
        return ("structural", "structural_edge")
    if lowered in {"contains", "in", "on", "part_of", "held_by", "worn_by", "at", "near"}:
        return ("containment", "containment_edge")
    return ("runtime", "memory_edge")


def _memory_scene(session: "HumanSession") -> dict[str, Any]:
    raw_nodes = {str(node.get("id") or ""): copy.deepcopy(node) for node in scene_nodes(session.raw_scene) if node.get("id")}
    included_ids = {str(node_id) for node_id in session.robot_memory.node if str(node_id)}
    scene_agent = session.current_scene.get("agent") or {}
    current_room = str((session.runtime_state.get("room_of") or {}).get(session.agent_id) or scene_agent.get("current_room") or "")
    current_anchor = str((session.runtime_state.get("parent_of") or {}).get(session.agent_id) or scene_agent.get("current_anchor") or current_room or "")
    if current_room:
        included_ids.add(current_room)
    if current_anchor:
        included_ids.add(current_anchor)

    room_ids = {
        node_id
        for node_id, node in session.robot_memory.node.items()
        if str((node or {}).get("node_type") or "").lower() == "room"
    }
    for room_id in list(room_ids):
        raw_room = raw_nodes.get(room_id) or {}
        floor_id = str(raw_room.get("parent") or raw_room.get("floor_id") or "")
        if floor_id and floor_id in raw_nodes:
            included_ids.add(floor_id)

    memory_parent_map: dict[str, str] = {}
    memory_edges: list[dict[str, Any]] = []
    for edge in session.robot_memory.edge.values():
        source_id = str(edge.get("source_id") or "")
        target_id = str(edge.get("target_id") or "")
        relation = str(edge.get("relation") or "")
        if not source_id or not target_id or not relation:
            continue
        included_ids.add(source_id)
        included_ids.add(target_id)
        if relation == "contains":
            memory_parent_map[target_id] = source_id
        category, edge_type = _edge_category(relation)
        memory_edges.append(
            {
                "source_id": source_id,
                "target_id": target_id,
                "relation": relation,
                "category": category,
                "edge_type": edge_type,
                "properties": {
                    "memory_source": str(edge.get("memory_source") or ""),
                    "memory_last_observed_step": int(edge.get("memory_last_observed_step") or 0),
                },
            }
        )

    scene_nodes_payload: list[dict[str, Any]] = []
    for node_id in sorted(included_ids):
        raw_node = copy.deepcopy(raw_nodes.get(node_id) or {"id": node_id})
        memory_node = copy.deepcopy(session.robot_memory.node.get(node_id) or {})
        if memory_node:
            raw_node.update(memory_node)
        if node_id in memory_parent_map:
            raw_node["parent"] = memory_parent_map[node_id]
        elif canonical_node_type(raw_node) == "room":
            raw_parent = str((raw_nodes.get(node_id) or {}).get("parent") or (raw_nodes.get(node_id) or {}).get("floor_id") or "")
            if raw_parent and raw_parent in included_ids:
                raw_node["parent"] = raw_parent
        scene_nodes_payload.append(raw_node)

    agent_states = copy.deepcopy(((session.runtime_state.get("nodes") or {}).get(session.agent_id) or {}).get("states") or {})
    scene_payload = {
        "scene_name": session.current_scene.get("scene_name") or session.raw_scene.get("scene_name") or session.scene_id,
        "scene_name_cn": session.current_scene.get("scene_name_cn") or session.raw_scene.get("scene_name_cn") or session.scene_id,
        "agent": {
            "id": session.agent_id,
            "current_room": current_room,
            "current_anchor": current_anchor,
            "inventory": copy.deepcopy((session.current_scene.get("agent") or {}).get("inventory") or []),
            "state": agent_states,
        },
        "world_state": copy.deepcopy(session.current_scene.get("world_state") or {}),
        "nodes": scene_nodes_payload,
        "edges": memory_edges,
    }
    return normalize_home_scene(scene_payload)


def _effect_preview(candidate: dict[str, Any], runtime_state: dict[str, Any]) -> str:
    action_type = str(candidate.get("action_type") or "")
    target_id = str(candidate.get("target_id") or "")
    target = (runtime_state.get("nodes") or {}).get(target_id) or {}
    states = target.get("states") or {}
    if action_type == "move":
        if str(candidate.get("target_semantic") or "") == "room":
            return f"Move to adjacent room: {target_id}"
        return f"Move next to {target_id}"
    if action_type == "pick":
        return f"Pick up {target_id}"
    if action_type == "place":
        held = str(candidate.get("object_id") or "")
        return f"Place {held} onto/into {target_id}"
    if action_type == "brush":
        return f"Brush/clean {target_id}"
    if action_type == "press":
        return f"Press {target_id} to toggle controlled device state"
    if action_type == "open":
        is_open = bool(states.get("is_open", states.get("isOpen", False)))
        return f"{'Close' if is_open else 'Open'} {target_id}"
    if action_type == "close":
        is_open = bool(states.get("is_open", states.get("isOpen", False)))
        return f"{'Close' if is_open else 'Open'} {target_id}"
    return f"Apply {action_type} on {target_id}"


def normalize_action(action_name: str) -> str:
    return str(action_name or "").strip().lower()


def _human_action_candidates(
    raw_scene: dict[str, Any],
    runtime_state: dict[str, Any],
    observation: dict[str, Any],
    agent_id: str,
) -> list[dict[str, Any]]:
    robot = observation.get("robot") or {}
    visible_nodes = list(observation.get("visible_nodes") or [])
    holding = str(robot.get("holding") or "")
    candidates: list[dict[str, Any]] = []
    visible_room_ids = {
        str(node.get("id") or "")
        for node in visible_nodes
        if str(node.get("node_type") or "").lower() == "room"
    }

    for room_id in robot.get("adjacent_rooms") or []:
        if str(room_id) not in visible_room_ids:
            continue
        action = {"agent": agent_id, "action": "move", "target": str(room_id)}
        validated = validate_robot_action(raw_scene, action, runtime_state=runtime_state)
        if validated.get("ok"):
            candidates.append(
                {
                    "action_type": "move",
                    "target_id": str(room_id),
                    "target_semantic": "room",
                    "action_payload": action,
                }
            )

    for node in visible_nodes:
        node_id = str(node.get("id") or "")
        semantic = str(node.get("semantic_type") or "")
        actions = {normalize_action(str(item).lower()) for item in (node.get("interactive_actions") or [])}
        for action_type in actions:
            if action_type not in ALLOWED_ACTIONS or action_type == "place":
                continue
            action = {"agent": agent_id, "action": action_type, "target": node_id}
            if action_type == "pick":
                action["object"] = node_id
            validated = validate_robot_action(raw_scene, action, runtime_state=runtime_state)
            if validated.get("ok"):
                candidates.append(
                    {
                        "action_type": action_type,
                        "target_id": node_id,
                        "target_semantic": semantic,
                        "action_payload": action,
                    }
                )
        if holding and "place" in actions:
            action = {"agent": agent_id, "action": "place", "target": node_id, "object": holding}
            validated = validate_robot_action(raw_scene, action, runtime_state=runtime_state)
            if validated.get("ok"):
                candidates.append(
                    {
                        "action_type": "place",
                        "target_id": node_id,
                        "target_semantic": semantic,
                        "object_id": holding,
                        "placement_target_id": node_id,
                        "action_payload": action,
                    }
                )

    deduped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = (
            str(candidate.get("action_type") or ""),
            str(candidate.get("target_id") or ""),
            str(candidate.get("object_id") or ""),
            str(candidate.get("placement_target_id") or ""),
        )
        deduped[key] = candidate

    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            ["move", "pick", "place", "press", "open", "close", "brush"].index(str(item.get("action_type") or "move")),
            str(item.get("target_id") or ""),
        ),
    )
    for item in ordered:
        item["effect_preview"] = _effect_preview(item, runtime_state)
    return ordered


def _append_log(log_path: Path, message: str) -> None:
    with log_path.open("a", encoding="utf-8") as f:
        f.write(message.rstrip() + "\n")


def _memory_graph_payload(memory: RobotMemory, agent_id: str) -> dict[str, Any]:
    node_ids = {str(node_id) for node_id in memory.node if str(node_id)}
    edge_keys: list[dict[str, str]] = []
    for edge in memory.edge.values():
        source_id = str(edge.get("source_id") or "")
        target_id = str(edge.get("target_id") or "")
        relation = str(edge.get("relation") or "")
        if not source_id or not target_id or not relation:
            continue
        node_ids.add(source_id)
        node_ids.add(target_id)
        edge_keys.append(
            {
                "source_id": source_id,
                "target_id": target_id,
                "relation": relation,
                "memory_source": str(edge.get("memory_source") or ""),
                "memory_last_observed_step": int(edge.get("memory_last_observed_step") or 0),
            }
        )
    if agent_id:
        node_ids.add(agent_id)
    return {
        "node_ids": sorted(node_ids),
        "edges": edge_keys,
        "summary": summarize_memory(memory),
    }


@dataclass
class HumanSession:
    session_id: str
    replay_id: str
    scene_id: str
    agent_id: str
    raw_scene: dict[str, Any]
    current_scene: dict[str, Any]
    runtime_state: dict[str, Any]
    robot_memory: RobotMemory
    log_path: Path
    run_dir: Path
    writer: SummaryWriter
    steps: list[dict[str, Any]] = field(default_factory=list)
    terminated: bool = False
    termination_reason: str = ""


class HumanSessionStore:
    def __init__(self, replay_store: ReplayStore) -> None:
        self.replays = replay_store
        self.sessions: dict[str, HumanSession] = {}

    def _make_summary(self, session: HumanSession) -> dict[str, Any]:
        final_metrics = evaluate_scene(session.current_scene)
        final_world = float(((final_metrics.get("world_metrics") or {}).get("world_score") or 0.0))
        run_name = canonical_run_name(session.scene_id, EXPERIMENT_PURE_HUMAN, "human_player")
        return {
            "agent_id": session.agent_id,
            "agent_model": "human_player",
            "experiment_type": EXPERIMENT_PURE_HUMAN,
            "experiment_label": experiment_label(EXPERIMENT_PURE_HUMAN, "human_player"),
            "run_name": run_name,
            "log_path": str(session.log_path),
            "max_days": 1,
            "step_count": len(session.steps),
            "terminated": session.terminated,
            "termination_reason": session.termination_reason,
            "final_world_score": final_world,
            "tensorboard_log_dir": str(session.run_dir),
        }

    def _current_preview_step(self, session: HumanSession) -> dict[str, Any]:
        observation = build_robot_observation(
            session.current_scene,
            task=None,
            runtime_state=session.runtime_state,
            agent_id=session.agent_id,
        )
        update_memory_from_observation(session.robot_memory, observation)
        save_robot_memory(session.current_scene, session.agent_id, session.robot_memory)
        metrics = evaluate_scene(session.current_scene)
        current_index = max(0, len(session.steps))
        return {
            "episode_step": current_index,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reasoning": "human_pending_action",
            "planner": {"mode": "pure_human"},
            "action": {"agent": session.agent_id, "action": "noop"},
            "ok": True,
            "failed_preconds": [],
            "observation": observation,
            "memory_before": {},
            "memory_after": {},
            "event_log": copy.deepcopy((session.current_scene.get("world_state") or {}).get("event_log") or []),
            "scene_metrics": metrics,
            "world_score": float(((metrics.get("world_metrics") or {}).get("world_score") or 0.0)),
            "scene": copy.deepcopy(session.current_scene),
            "memory_scene": _memory_scene(session),
        }

    def _session_payload(self, session: HumanSession, *, validation_error: str = "") -> dict[str, Any]:
        current_step = session.steps[-1] if session.steps else self._current_preview_step(session)
        observation = current_step.get("observation") or {}
        candidates = _human_action_candidates(
            session.current_scene,
            session.runtime_state,
            observation,
            session.agent_id,
        )
        return {
            "session_id": session.session_id,
            "replay_id": session.replay_id,
            "scene_id": session.scene_id,
            "summary": self._make_summary(session),
            "terminated": session.terminated,
            "validation_error": validation_error,
            "max_steps": FIXED_EXPERIMENT_STEPS,
            "memory_graph": _memory_graph_payload(session.robot_memory, session.agent_id),
            "current_step": current_step,
            "action_candidates": candidates,
        }

    def start_session(self, scene_id: str, raw_scene: dict[str, Any], agent_id: str = "robot_01") -> dict[str, Any]:
        scene = normalize_home_scene(copy.deepcopy(raw_scene))
        ensure_scene_robot_stub(scene, agent_id)
        runtime_state = build_runtime_state(scene)
        spawn_options = _spawn_options(scene, runtime_state)
        start_choice = random.choice(spawn_options) if spawn_options else {
            "anchor_id": scene.get("agent", {}).get("current_room") or "",
            "room_id": scene.get("agent", {}).get("current_room") or "",
            "anchor_kind": "room",
        }
        start_room = str(start_choice.get("room_id") or "")
        start_anchor = str(start_choice.get("anchor_id") or start_room or "")
        scene.setdefault("agent", {})
        scene["agent"]["id"] = agent_id
        scene["agent"]["current_room"] = start_room
        scene["agent"]["current_anchor"] = start_anchor
        scene["agent"]["inventory"] = []
        runtime_state = build_runtime_state(scene)
        robot_memory = load_robot_memory(scene, agent_id)

        replay_id = self.replays._next_replay_id()
        session_id = replay_id
        log_path = self.replays._log_path(replay_id)
        run_dir = self.replays._tensorboard_run_dir(replay_id, scene_id, EXPERIMENT_PURE_HUMAN, "human_player")
        run_dir.mkdir(parents=True, exist_ok=True)
        writer = SummaryWriter(log_dir=str(run_dir))
        self.replays._write_tensorboard_metadata(
            writer,
            replay_id=replay_id,
            scene_id=scene_id,
            experiment_type=EXPERIMENT_PURE_HUMAN,
            agent_model="human_player",
            task=None,
        )
        _append_log(log_path, f"[ReplayStart] replay_id={replay_id} scene_id={scene_id} experiment_type=pure_human agent_model=human_player")
        _append_log(log_path, f"[HumanStart] session_id={session_id} spawn_room={start_room} spawn_anchor={start_anchor}")
        session = HumanSession(
            session_id=session_id,
            replay_id=replay_id,
            scene_id=scene_id,
            agent_id=agent_id,
            raw_scene=copy.deepcopy(scene),
            current_scene=copy.deepcopy(scene),
            runtime_state=runtime_state,
            robot_memory=robot_memory,
            log_path=log_path,
            run_dir=run_dir,
            writer=writer,
        )
        self.sessions[session_id] = session
        return self._session_payload(session)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        return self._session_payload(session)

    def apply_action(self, session_id: str, action_payload: dict[str, Any]) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        if session.terminated:
            return self._session_payload(session, validation_error="session already terminated")

        action = {
            "agent": session.agent_id,
            "action": str(action_payload.get("action_type") or action_payload.get("action") or "").strip(),
            "target": str(action_payload.get("target_id") or action_payload.get("target") or "").strip(),
        }
        if action_payload.get("object_id"):
            action["object"] = str(action_payload.get("object_id"))
        if action_payload.get("placement_target_id"):
            action["target"] = str(action_payload.get("placement_target_id"))

        validated = validate_robot_action(session.current_scene, action, runtime_state=session.runtime_state)
        if not validated.get("ok"):
            return self._session_payload(
                session,
                validation_error="; ".join(str(x) for x in (validated.get("failed_preconds") or [])),
            )

        before_observation = build_robot_observation(
            session.current_scene,
            task=None,
            runtime_state=session.runtime_state,
            agent_id=session.agent_id,
        )
        execution = execute_robot_action(session.current_scene, action, runtime_state=session.runtime_state)
        scene_after_action = execution.get("scene") or session.current_scene
        state_after_action = execution.get("runtime_state") or session.runtime_state
        advanced_scene, advanced_state = advance_world_one_step(scene_after_action, state_after_action, session.agent_id)
        session.current_scene = copy.deepcopy(advanced_scene)
        session.runtime_state = copy.deepcopy(advanced_state)
        after_observation = build_robot_observation(
            session.current_scene,
            task=None,
            runtime_state=session.runtime_state,
            agent_id=session.agent_id,
        )
        update_memory_from_observation(session.robot_memory, before_observation)
        update_memory_from_observation(session.robot_memory, after_observation)
        save_robot_memory(session.current_scene, session.agent_id, session.robot_memory)
        metrics = evaluate_scene(session.current_scene)
        world_metrics = metrics.get("world_metrics") or {}

        step_index = len(session.steps)
        step_payload = {
            "episode_step": step_index,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reasoning": f"human_selected: {action.get('action')} {action.get('target')}".strip(),
            "planner": {"mode": "pure_human"},
            "action": copy.deepcopy(action),
            "ok": bool(execution.get("ok", False)),
            "failed_preconds": copy.deepcopy(execution.get("failed_preconds") or []),
            "observation": after_observation,
            "observation_before": before_observation,
            "memory_before": {},
            "memory_after": summarize_memory(session.robot_memory),
            "event_log": copy.deepcopy(execution.get("event_log") or []),
            "scene_metrics": copy.deepcopy(metrics),
            "world_score": float(world_metrics.get("world_score") or 0.0),
            "scene": copy.deepcopy(session.current_scene),
            "memory_scene": _memory_scene(session),
        }
        session.steps.append(step_payload)
        self.replays._write_tensorboard_step(session.writer, step_payload)
        self.replays._persist_live_step(session.replay_id, step_payload)
        _append_log(
            session.log_path,
            f"[HumanStep] step={step_index} action={action.get('action')} target={action.get('target')} ok={bool(execution.get('ok', False))} world={float(world_metrics.get('world_score') or 0.0):.4f}",
        )

        if len(session.steps) >= FIXED_EXPERIMENT_STEPS:
            self.end_session(session_id, reason=f"fixed_steps_reached_{FIXED_EXPERIMENT_STEPS}")
        return self._session_payload(session)

    def end_session(self, session_id: str, reason: str = "human_stopped") -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        if session.terminated:
            return self._session_payload(session)
        session.terminated = True
        session.termination_reason = reason
        summary = self._make_summary(session)
        self.replays._write_tensorboard_summary(
            session.writer,
            summary=summary,
            scene_id=session.scene_id,
            experiment_type=EXPERIMENT_PURE_HUMAN,
            agent_model="human_player",
        )
        session.writer.flush()
        session.writer.close()
        run = {
            "config": {
                "agent_id": session.agent_id,
                "agent_model": "human_player",
                "decision_mode": "pure_human",
                "max_days": 1,
                "max_steps": FIXED_EXPERIMENT_STEPS,
                "fixed_experiment_steps": FIXED_EXPERIMENT_STEPS,
                "timeout": 0,
            },
            "task": {},
            "initial_scene_name": str(session.raw_scene.get("scene_name") or ""),
            "steps": session.steps,
            "final_scene": copy.deepcopy(session.current_scene),
            "final_metrics": evaluate_scene(session.current_scene),
            "terminated": True,
            "termination_reason": reason,
        }
        payload = {
            "replay_id": session.replay_id,
            "scene_id": session.scene_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "summary": summary,
            "run": copy.deepcopy(run),
        }
        self.replays._write_replay_outputs(
            replay_id=session.replay_id,
            scene_id=session.scene_id,
            payload=payload,
            run=run,
            normalized_experiment=EXPERIMENT_PURE_HUMAN,
            agent_model="human_player",
            run_dir=session.run_dir,
        )
        _append_log(session.log_path, f"[ReplayEnd] replay_id={session.replay_id} reason={reason} steps={len(session.steps)}")
        return self._session_payload(session)
