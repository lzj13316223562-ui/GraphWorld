from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any


SCAN_SOURCES = {"scan", "scan_local"}
OBSERVATION_SOURCES = {"observation", "adjacency", "self_position"}


@dataclass
class RobotMemory:
    node: dict[str, dict[str, Any]] = field(default_factory=dict)
    edge: dict[str, dict[str, Any]] = field(default_factory=dict)
    stable_node: dict[str, dict[str, Any]] = field(default_factory=dict)
    stable_edge: dict[str, dict[str, Any]] = field(default_factory=dict)
    decaying_node: dict[str, dict[str, Any]] = field(default_factory=dict)
    decaying_edge: dict[str, dict[str, Any]] = field(default_factory=dict)
    working_memory: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node": copy.deepcopy(self.node),
            "edge": copy.deepcopy(self.edge),
            "stable_node": copy.deepcopy(self.stable_node),
            "stable_edge": copy.deepcopy(self.stable_edge),
            "decaying_node": copy.deepcopy(self.decaying_node),
            "decaying_edge": copy.deepcopy(self.decaying_edge),
            "working_memory": copy.deepcopy(self.working_memory),
        }


def _step_from_observation(observation: dict[str, Any]) -> int:
    return int((observation.get("world") or {}).get("step") or 0)


def _edge_id(source_id: str, relation: str, target_id: str) -> str:
    return f"{source_id}::{relation}::{target_id}"


def _node_payload(
    node: dict[str, Any],
    *,
    step: int,
    room_id: str | None = None,
    source: str = "observation",
    visited: bool | None = None,
) -> dict[str, Any]:
    payload = {
        "id": str(node.get("id") or ""),
        "name": node.get("name"),
        "name_cn": node.get("name_cn"),
        "node_type": node.get("node_type") or node.get("type"),
        "semantic_type": node.get("semantic_type") or node.get("object_type"),
        "parent": node.get("parent") or node.get("parent_id"),
        "states": copy.deepcopy(node.get("states") or {}),
        "interactive_actions": copy.deepcopy(node.get("interactive_actions") or node.get("affordances") or []),
        "layout": copy.deepcopy(node.get("layout") or {}),
        "room_id": room_id or node.get("room_id"),
        "memory_last_observed_step": int(step),
        "memory_source": source,
    }
    if visited is not None:
        payload["memory_visited"] = bool(visited)
    return payload


def _upsert_node(memory: RobotMemory, payload: dict[str, Any]) -> None:
    _upsert_node_to_store(memory.decaying_node, payload)


def _upsert_node_to_store(store: dict[str, dict[str, Any]], payload: dict[str, Any]) -> None:
    node_id = str(payload.get("id") or "")
    if not node_id:
        return
    existing = store.get(node_id) or {}
    merged = copy.deepcopy(existing)
    merged.update(payload)

    existing_states = copy.deepcopy(existing.get("states") or {})
    existing_states.update(copy.deepcopy(payload.get("states") or {}))
    merged["states"] = existing_states

    existing_actions = list(existing.get("interactive_actions") or [])
    next_actions = list(payload.get("interactive_actions") or [])
    if existing_actions or next_actions:
        merged["interactive_actions"] = sorted(set(existing_actions) | set(next_actions))

    existing_source = str(existing.get("memory_source") or "")
    payload_source = str(payload.get("memory_source") or "")
    if existing_source in SCAN_SOURCES and payload_source in OBSERVATION_SOURCES:
        merged["memory_source"] = existing_source

    merged["memory_last_observed_step"] = max(
        int(existing.get("memory_last_observed_step") or 0),
        int(payload.get("memory_last_observed_step") or 0),
    )
    if existing.get("memory_visited") or payload.get("memory_visited"):
        merged["memory_visited"] = True

    store[node_id] = merged


def _upsert_edge(
    memory: RobotMemory,
    source_id: str,
    relation: str,
    target_id: str,
    *,
    step: int,
    source: str = "observation",
) -> None:
    _upsert_edge_to_store(memory.decaying_edge, source_id, relation, target_id, step=step, source=source)


def _upsert_edge_to_store(
    store: dict[str, dict[str, Any]],
    source_id: str,
    relation: str,
    target_id: str,
    *,
    step: int,
    source: str = "observation",
) -> None:
    if not source_id or not relation or not target_id:
        return
    edge_id = _edge_id(str(source_id), str(relation), str(target_id))
    existing = store.get(edge_id) or {}
    merged = copy.deepcopy(existing)
    merged.update(
        {
            "id": edge_id,
            "source_id": str(source_id),
            "target_id": str(target_id),
            "relation": str(relation),
            "memory_last_observed_step": int(step),
            "memory_source": source,
        }
    )
    existing_source = str(existing.get("memory_source") or "")
    if existing_source in SCAN_SOURCES and source in OBSERVATION_SOURCES:
        merged["memory_source"] = existing_source
    merged["memory_last_observed_step"] = max(
        int(existing.get("memory_last_observed_step") or 0),
        int(step),
    )
    store[edge_id] = merged


def _sync_layered_graph(memory: RobotMemory) -> None:
    merged_node: dict[str, dict[str, Any]] = {}
    for store in (memory.stable_node, memory.decaying_node):
        for node in store.values():
            _upsert_node_to_store(merged_node, copy.deepcopy(node))
    for key, value in (memory.working_memory.get("working_nodes") or {}).items():
        _upsert_node_to_store(merged_node, copy.deepcopy(value))
    memory.node = merged_node

    merged_edge: dict[str, dict[str, Any]] = {}
    for store in (memory.stable_edge, memory.decaying_edge):
        for edge in store.values():
            _upsert_edge_to_store(
                merged_edge,
                str(edge.get("source_id") or ""),
                str(edge.get("relation") or ""),
                str(edge.get("target_id") or ""),
                step=int(edge.get("memory_last_observed_step") or 0),
                source=str(edge.get("memory_source") or "observation"),
            )
    for key, value in (memory.working_memory.get("working_edges") or {}).items():
        _upsert_edge_to_store(
            merged_edge,
            str(value.get("source_id") or ""),
            str(value.get("relation") or ""),
            str(value.get("target_id") or ""),
            step=int(value.get("memory_last_observed_step") or 0),
            source=str(value.get("memory_source") or "observation"),
        )
    memory.edge = merged_edge


def _seed_layered_memory(memory: dict[str, Any]) -> None:
    if memory.get("stable_node") is None:
        memory["stable_node"] = {}
    if memory.get("stable_edge") is None:
        memory["stable_edge"] = {}
    if memory.get("decaying_node") is None:
        memory["decaying_node"] = copy.deepcopy(memory.get("node") or {})
    if memory.get("decaying_edge") is None:
        memory["decaying_edge"] = copy.deepcopy(memory.get("edge") or {})
    if memory.get("working_memory") is None:
        memory["working_memory"] = {}
    memory["working_memory"].setdefault("recent_observations", [])
    memory["working_memory"].setdefault("recent_actions", [])
    memory["working_memory"].setdefault("recent_reflections", [])
    memory["working_memory"].setdefault("patterns", [])
    memory["working_memory"].setdefault("experience_summaries", [])
    memory["working_memory"].setdefault("experience_library", {})
    memory["working_memory"].setdefault("working_nodes", {})
    memory["working_memory"].setdefault("working_edges", {})
    memory["working_memory"].setdefault("active_goal", {})
    memory["working_memory"].setdefault(
        "learned_rules",
        {
            "operation_rules": [],
            "world_rules": [],
            "human_rules": [],
        },
    )


def ensure_robot_memory(scene: dict[str, Any], agent_id: str) -> dict[str, Any]:
    scene.setdefault("agent", {})
    scene["agent"].setdefault("id", agent_id)
    memory = scene["agent"].get("memory")
    if not isinstance(memory, dict):
        memory = {}

    if "node" not in memory and "belief_nodes" in memory:
        memory["node"] = copy.deepcopy(memory.get("belief_nodes") or {})
    if "edge" not in memory and "belief_edges" in memory:
        edge_map = {}
        for edge in memory.get("belief_edges") or []:
            source_id = str(edge.get("source_id") or "")
            relation = str(edge.get("relation") or "")
            target_id = str(edge.get("target_id") or "")
            if not source_id or not relation or not target_id:
                continue
            edge_map[_edge_id(source_id, relation, target_id)] = copy.deepcopy(edge)
        memory["edge"] = edge_map

    memory.setdefault("node", {})
    memory.setdefault("edge", {})
    _seed_layered_memory(memory)
    scene["agent"]["memory"] = memory
    return memory


def load_robot_memory(scene: dict[str, Any], agent_id: str) -> RobotMemory:
    memory = ensure_robot_memory(scene, agent_id)
    return RobotMemory(
        node=copy.deepcopy(memory.get("node") or {}),
        edge=copy.deepcopy(memory.get("edge") or {}),
        stable_node=copy.deepcopy(memory.get("stable_node") or {}),
        stable_edge=copy.deepcopy(memory.get("stable_edge") or {}),
        decaying_node=copy.deepcopy(memory.get("decaying_node") or {}),
        decaying_edge=copy.deepcopy(memory.get("decaying_edge") or {}),
        working_memory=copy.deepcopy(memory.get("working_memory") or {}),
    )


def save_robot_memory(scene: dict[str, Any], agent_id: str, memory: RobotMemory) -> None:
    _sync_layered_graph(memory)
    store = ensure_robot_memory(scene, agent_id)
    store.clear()
    store.update(memory.to_dict())


def update_memory_from_observation(memory: RobotMemory, observation: dict[str, Any]) -> None:
    step = _step_from_observation(observation)
    robot = observation.get("robot") or {}
    room_id = str(robot.get("current_room") or "")

    if room_id:
        _upsert_node_to_store(
            memory.stable_node,
            {
                "id": room_id,
                "node_type": "room",
                "semantic_type": "room",
                "room_id": room_id,
                "memory_last_observed_step": step,
                "memory_source": "self_position",
                "memory_visited": True,
            },
        )

    visible_room_ids = {
        str(node.get("id") or "")
        for node in observation.get("visible_nodes") or []
        if str(node.get("node_type") or "").lower() == "room"
    }
    visible_room_ids.discard(room_id)

    for neighbor in robot.get("adjacent_rooms") or []:
        neighbor_id = str(neighbor)
        if neighbor_id not in visible_room_ids:
            continue
        _upsert_node_to_store(
            memory.stable_node,
            {
                "id": neighbor_id,
                "node_type": "room",
                "semantic_type": "room",
                "room_id": neighbor_id,
                "memory_last_observed_step": step,
                "memory_source": "adjacency",
            },
        )
        if room_id:
            _upsert_edge_to_store(memory.stable_edge, room_id, "adjacent_to", neighbor_id, step=step, source="adjacency")
            _upsert_edge_to_store(memory.stable_edge, neighbor_id, "adjacent_to", room_id, step=step, source="adjacency")

    for node in observation.get("visible_nodes") or []:
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        _upsert_node(memory, _node_payload(node, step=step, room_id=room_id, source="observation"))
        parent_id = str(node.get("parent") or "")
        if parent_id:
            _upsert_edge(memory, parent_id, "contains", node_id, step=step, source="observation")

    recent_observations = list(memory.working_memory.get("recent_observations") or [])
    recent_observations.append(
        {
            "step": step,
            "current_room": room_id,
            "visible_ids": [str(node.get("id") or "") for node in observation.get("visible_nodes") or []][:12],
            "world_score": float((observation.get("scores") or {}).get("world_score") or 0.0),
        }
    )
    memory.working_memory["recent_observations"] = recent_observations[-8:]
    _sync_layered_graph(memory)


def remember_scan(memory: RobotMemory, observation: dict[str, Any], *, step: int | None = None) -> None:
    target = (observation or {}).get("target") or {}
    target_id = str(target.get("id") or "")
    if not target_id:
        return

    current_step = int(step if step is not None else target.get("memory_last_observed_step") or 0)
    _upsert_node(
        memory,
        _node_payload(
            target,
            step=current_step,
            room_id=target.get("room_id"),
            source="scan",
        ),
    )

    parent_id = str(target.get("parent_id") or "")
    if parent_id:
        _upsert_edge(memory, parent_id, "contains", target_id, step=current_step, source="scan")

    for controlled in target.get("controls") or []:
        controlled_id = str(controlled or "")
        if controlled_id:
            _upsert_edge_to_store(memory.stable_edge, target_id, "controls", controlled_id, step=current_step, source="scan")

    room_id = str(target.get("room_id") or "")
    for neighbor in (observation or {}).get("local_neighbors") or []:
        neighbor_id = str(neighbor.get("id") or "")
        if not neighbor_id:
            continue
        _upsert_node(
            memory,
            _node_payload(
                {
                    "id": neighbor_id,
                    "name": neighbor.get("name"),
                    "node_type": neighbor.get("type"),
                    "semantic_type": neighbor.get("object_type"),
                    "states": {},
                    "interactive_actions": [],
                    "layout": {},
                    "room_id": room_id,
                },
                step=current_step,
                room_id=room_id,
                source="scan_local",
            ),
        )
        if room_id:
            _upsert_edge(memory, room_id, "contains", neighbor_id, step=current_step, source="scan_local")
    _sync_layered_graph(memory)


def remember_action_result(
    memory: RobotMemory,
    *,
    action: dict[str, Any],
    reasoning: str,
    plan_goal: str = "",
    ok: bool,
    failed_preconds: list[str],
    world_score_before: float,
    world_score_after_action: float,
    world_score_after_world_step: float | None = None,
    observation: dict[str, Any] | None = None,
    step: int = 0,
) -> None:
    # Keep action history as lightweight graph-level metadata on the robot node.
    robot_id = str(action.get("agent") or "robot_01")
    robot_node = copy.deepcopy(memory.node.get(robot_id) or {"id": robot_id, "node_type": "agent", "semantic_type": "robot"})
    history = copy.deepcopy(robot_node.get("memory_recent_actions") or [])
    history.append(
        {
            "action": copy.deepcopy(action),
            "reasoning": reasoning,
            "plan_goal": str(plan_goal or "").strip(),
            "ok": bool(ok),
            "failed_preconds": list(failed_preconds or []),
            "world_score_before": round(float(world_score_before), 4),
            "world_score_after_action": round(float(world_score_after_action), 4),
            "world_score_after_world_step": (
                round(float(world_score_after_world_step), 4)
                if world_score_after_world_step is not None
                else None
            ),
            "step": int(step),
        }
    )
    robot_node["memory_recent_actions"] = history[-8:]
    robot_node["memory_last_observed_step"] = max(int(robot_node.get("memory_last_observed_step") or 0), int(step))
    robot_node.setdefault("memory_source", "self_position")
    memory.working_memory.setdefault("working_nodes", {})[robot_id] = robot_node

    recent_actions = list(memory.working_memory.get("recent_actions") or [])
    recent_actions.append(copy.deepcopy(history[-1]))
    memory.working_memory["recent_actions"] = recent_actions[-8:]

    if observation:
        remember_scan(memory, observation, step=step)
    _sync_layered_graph(memory)


def _target_semantic(memory: RobotMemory, action: dict[str, Any]) -> str:
    target_id = str(action.get("target") or action.get("object") or "")
    if not target_id:
        return ""
    node = memory.node.get(target_id) or memory.decaying_node.get(target_id) or memory.stable_node.get(target_id) or {}
    return str(node.get("semantic_type") or node.get("node_type") or "")


def _experience_outcome(ok: bool, immediate_delta: float, world_delta: float | None) -> str:
    if not ok:
        return "blocked"
    if immediate_delta > 0 and (world_delta or 0.0) >= 0:
        return "helpful"
    if immediate_delta > 0 and (world_delta or 0.0) < 0:
        return "mixed"
    if immediate_delta < 0 and (world_delta or 0.0) >= 0:
        return "recovering"
    if immediate_delta < 0 or (world_delta or 0.0) < 0:
        return "risky"
    return "informative"


def _summarize_experience(
    *,
    memory: RobotMemory,
    action: dict[str, Any],
    ok: bool,
    failed_preconds: list[str],
    immediate_reflection: dict[str, Any],
    world_reflection: dict[str, Any] | None,
    step: int,
) -> dict[str, Any]:
    action_type = str(action.get("action") or "")
    target = str(action.get("target") or action.get("object") or "")
    target_semantic = _target_semantic(memory, action)
    immediate_delta = float(immediate_reflection.get("score_delta") or 0.0)
    world_delta = float((world_reflection or {}).get("score_delta") or 0.0)
    outcome = _experience_outcome(ok, immediate_delta, world_delta if world_reflection is not None else None)

    if not ok:
        summary = f"{action_type} on {target_semantic or target or 'target'} was blocked by unmet preconditions"
        recommendation = "change the local setup or pick a different target before retrying"
    elif outcome == "helpful":
        summary = f"{action_type} on {target_semantic or target or 'target'} was a reliably useful intervention in this context"
        recommendation = "prefer similar interventions when the same issue reappears nearby"
    elif outcome == "mixed":
        summary = f"{action_type} on {target_semantic or target or 'target'} helped immediately but the benefit did not persist after the world advanced"
        recommendation = "use this only with follow-up actions or when the downstream side effects are acceptable"
    elif outcome == "recovering":
        summary = f"{action_type} on {target_semantic or target or 'target'} had an immediate cost but recovered after the world evolved"
        recommendation = "allow for delayed payoff before marking this behavior as bad"
    elif outcome == "risky":
        summary = f"{action_type} on {target_semantic or target or 'target'} tended to hurt the world state"
        recommendation = "deprioritize this move unless it unlocks a stronger follow-up action"
    else:
        summary = f"{action_type} on {target_semantic or target or 'target'} was mainly informative rather than directly impactful"
        recommendation = "treat this as a knowledge-gathering step, not a score-improving intervention"

    tags = [action_type or "unknown_action", target_semantic or "unknown_target", outcome]
    if failed_preconds:
        tags.append("precondition_failure")
    if world_reflection is not None:
        tags.append("world_advanced")
    return {
        "step": int(step),
        "action_type": action_type,
        "target": target,
        "target_semantic": target_semantic,
        "outcome": outcome,
        "summary": summary,
        "recommendation": recommendation,
        "tags": tags,
        "evidence": {
            "ok": bool(ok),
            "failed_preconds": list(failed_preconds or []),
            "immediate_score_delta": round(immediate_delta, 4),
            "world_step_score_delta": round(world_delta, 4) if world_reflection is not None else None,
        },
    }


def _update_experience_library(memory: RobotMemory, summary: dict[str, Any]) -> None:
    key = "|".join(
        [
            str(summary.get("action_type") or ""),
            str(summary.get("target_semantic") or ""),
            str(summary.get("outcome") or ""),
        ]
    )
    library = copy.deepcopy(memory.working_memory.get("experience_library") or {})
    entry = copy.deepcopy(library.get(key) or {})
    count = int(entry.get("count") or 0) + 1
    total_immediate = float(entry.get("total_immediate_score_delta") or 0.0) + float(
        ((summary.get("evidence") or {}).get("immediate_score_delta") or 0.0)
    )
    world_delta = (summary.get("evidence") or {}).get("world_step_score_delta")
    total_world = float(entry.get("total_world_step_score_delta") or 0.0) + float(world_delta or 0.0)
    entry.update(
        {
            "key": key,
            "count": count,
            "last_step": int(summary.get("step") or 0),
            "action_type": str(summary.get("action_type") or ""),
            "target_semantic": str(summary.get("target_semantic") or ""),
            "outcome": str(summary.get("outcome") or ""),
            "summary": str(summary.get("summary") or ""),
            "recommendation": str(summary.get("recommendation") or ""),
            "tags": list(summary.get("tags") or []),
            "total_immediate_score_delta": round(total_immediate, 4),
            "total_world_step_score_delta": round(total_world, 4),
            "avg_immediate_score_delta": round(total_immediate / max(count, 1), 4),
            "avg_world_step_score_delta": round(total_world / max(count, 1), 4),
        }
    )
    library[key] = entry
    memory.working_memory["experience_library"] = library

    summaries = list(memory.working_memory.get("experience_summaries") or [])
    summaries.append(copy.deepcopy(summary))
    memory.working_memory["experience_summaries"] = summaries[-12:]


def _append_rule(memory: RobotMemory, category: str, rule: dict[str, Any]) -> None:
    learned_rules = copy.deepcopy(memory.working_memory.get("learned_rules") or {})
    learned_rules.setdefault("operation_rules", [])
    learned_rules.setdefault("world_rules", [])
    learned_rules.setdefault("human_rules", [])
    bucket = list(learned_rules.get(category) or [])
    signature = str(rule.get("rule") or "").strip()
    if not signature:
        memory.working_memory["learned_rules"] = learned_rules
        return
    bucket = [item for item in bucket if str(item.get("rule") or "").strip() != signature]
    bucket.append(copy.deepcopy(rule))
    learned_rules[category] = bucket[-8:]
    memory.working_memory["learned_rules"] = learned_rules


def _update_learned_rules(memory: RobotMemory, summary: dict[str, Any]) -> None:
    action_type = str(summary.get("action_type") or "").strip()
    target_semantic = str(summary.get("target_semantic") or "").strip()
    target_id = str(summary.get("target") or "").strip()
    outcome = str(summary.get("outcome") or "").strip()
    evidence = copy.deepcopy(summary.get("evidence") or {})
    world_delta = float(evidence.get("world_step_score_delta") or 0.0)

    if action_type and target_semantic:
        if outcome == "beneficial":
            _append_rule(
                memory,
                "operation_rules",
                {
                    "rule": f"{action_type} on {target_semantic} can improve the world when the local state clearly matches the need",
                    "evidence_target": target_id,
                    "confidence": "medium",
                    "source_step": int(summary.get("step") or 0),
                },
            )
        elif outcome == "risky":
            _append_rule(
                memory,
                "operation_rules",
                {
                    "rule": f"{action_type} on {target_semantic} can be harmful when it does not directly reduce the main problem",
                    "evidence_target": target_id,
                    "confidence": "medium",
                    "source_step": int(summary.get("step") or 0),
                },
            )

    if target_semantic in {"milk", "juice", "vegetables", "vegetable", "fruit", "raw_food", "cooked_food"}:
        _append_rule(
            memory,
            "world_rules",
            {
                "rule": "food can slowly become rotten over time, especially when left unresolved",
                "confidence": "high",
                "source_step": int(summary.get("step") or 0),
            },
        )
    if target_semantic in {"toilet", "sink", "cup", "bowl", "plate", "clothes", "shoes"}:
        _append_rule(
            memory,
            "world_rules",
            {
                "rule": "dirty or misplaced daily objects tend to keep lowering cleanliness and order scores until they are directly handled",
                "confidence": "medium",
                "source_step": int(summary.get("step") or 0),
            },
        )
    if target_semantic == "door":
        _append_rule(
            memory,
            "world_rules",
            {
                "rule": "doors left open can keep contributing to small but persistent penalties",
                "confidence": "medium",
                "source_step": int(summary.get("step") or 0),
            },
        )

    _append_rule(
        memory,
        "human_rules",
        {
            "rule": "the resident follows daily routines, so some problems repeat around washing up, meals, leaving home, and returning home",
            "confidence": "medium",
            "source_step": int(summary.get("step") or 0),
        },
    )
    if world_delta < 0 and target_semantic == "toilet":
        _append_rule(
            memory,
            "human_rules",
            {
                "rule": "a locally cleaner object does not always help if more urgent household problems are still unresolved elsewhere",
                "confidence": "medium",
                "source_step": int(summary.get("step") or 0),
            },
        )


def _semantic_of_target(memory: RobotMemory, target_id: str) -> str:
    if not target_id:
        return ""
    node = memory.node.get(target_id) or memory.decaying_node.get(target_id) or memory.stable_node.get(target_id) or {}
    return str(node.get("semantic_type") or node.get("node_type") or "")


def _infer_goal_type(plan_goal: str, action_type: str, target_semantic: str, target_id: str, placement_target_id: str, memory: RobotMemory) -> str:
    plan = str(plan_goal or "").lower()
    placement_semantic = _semantic_of_target(memory, placement_target_id)
    if "rotten" in plan or target_semantic in {"milk", "juice", "vegetables", "vegetable", "fruit", "raw_food", "cooked_food"}:
        return "dispose_rotten_food"
    if "shoe" in plan or target_semantic == "shoes":
        return "return_scattered_shoes"
    if "door" in plan or (target_semantic == "door" and action_type in {"open", "close"}):
        return "close_open_door"
    if "clean" in plan or action_type == "brush" or target_semantic in {"toilet", "sink", "cup", "bowl", "plate", "clothes"}:
        return "clean_dirty_target"
    if action_type == "move" and (target_semantic == "room" or not target_semantic):
        return "explore_room"
    if action_type == "place" and placement_semantic in {"trash_bin", "bin", "basket"}:
        return "dispose_item"
    return "handle_local_object"


def _goal_text(goal_type: str, target_id: str, target_semantic: str) -> str:
    if goal_type == "explore_room":
        return f"explore {target_id or 'a nearby room'}"
    if goal_type == "dispose_rotten_food":
        return f"dispose rotten food {target_id}".strip()
    if goal_type == "return_scattered_shoes":
        return f"return scattered shoes {target_id}".strip()
    if goal_type == "close_open_door":
        return f"close open door {target_id}".strip()
    if goal_type == "clean_dirty_target":
        return f"clean dirty target {target_id or target_semantic}".strip()
    return f"handle {target_id or target_semantic or 'target'}".strip()


def _compact_goal_text(text: str, *, fallback: str = "") -> str:
    raw = " ".join(str(text or "").strip().split())
    if not raw:
        return fallback
    sentence = raw
    for sep in (". ", "; ", " However", " Since", " This action", " This step", " Previous", " previous"):
        idx = sentence.find(sep)
        if idx > 0:
            sentence = sentence[:idx].strip(" .;,:")
            break
    short = sentence.strip(" .;,:")
    if len(short) > 96:
        short = short[:96].rsplit(" ", 1)[0].strip(" .;,:")
    return short or fallback


def _goal_progress_state(
    goal_type: str,
    *,
    action_type: str,
    target_semantic: str,
    target_id: str,
    placement_target_id: str,
    outcome: str,
    recommendation: str,
    memory: RobotMemory,
) -> tuple[str, bool]:
    placement_semantic = _semantic_of_target(memory, placement_target_id)
    if goal_type == "explore_room":
        if action_type == "move":
            return ("entered_room_not_scanned", False)
        if action_type == "scan":
            return ("room_scanned", True)
        return ("exploring_room", False)
    if goal_type == "dispose_rotten_food":
        if action_type == "scan":
            return ("identified_not_picked", False)
        if action_type == "pick":
            return ("holding_rotten_item", False)
        if action_type == "place" and placement_semantic in {"trash_bin", "bin", "basket"}:
            return ("placed_in_trash", True)
        return ("disposal_in_progress", False)
    if goal_type == "return_scattered_shoes":
        if action_type == "scan":
            return ("identified_not_picked", False)
        if action_type == "pick":
            return ("holding_shoes", False)
        if action_type == "place" and placement_target_id == "shoe_rack_entrance":
            return ("returned_to_shoe_rack", True)
        return ("return_in_progress", False)
    if goal_type == "close_open_door":
        if action_type == "close":
            return ("door_closed", True)
        if action_type == "scan":
            return ("door_checked", False)
        return ("door_closure_in_progress", False)
    if goal_type == "clean_dirty_target":
        if action_type == "pick" and target_semantic in {"toilet_brush", "brush", "scrub_brush"}:
            return ("tool_prepared", False)
        if action_type == "brush":
            done = outcome == "helpful" or "prefer similar interventions" in recommendation.lower()
            return ("cleaned_once", done)
        if action_type == "scan":
            return ("identified_not_cleaned", False)
        return ("cleaning_in_progress", False)
    done = outcome == "helpful" and action_type in {"place", "close", "press", "brush"}
    return ("in_progress", done)


def _update_active_goal(memory: RobotMemory, action: dict[str, Any], summary: dict[str, Any], plan_goal: str = "") -> None:
    previous = copy.deepcopy(memory.working_memory.get("active_goal") or {})
    target = str(action.get("target") or action.get("object") or "")
    action_type = str(action.get("action") or "")
    object_id = str(action.get("object") or "")
    placement_target_id = str(action.get("placement_target_id") or "")
    target_semantic = str(summary.get("target_semantic") or "")
    recommendation = str(summary.get("recommendation") or "")
    outcome = str(summary.get("outcome") or "")

    goal_type = _infer_goal_type(plan_goal, action_type, target_semantic, target, placement_target_id, memory)
    goal_target = target or object_id
    progress_state, completed = _goal_progress_state(
        goal_type,
        action_type=action_type,
        target_semantic=target_semantic,
        target_id=goal_target,
        placement_target_id=placement_target_id,
        outcome=outcome,
        recommendation=recommendation,
        memory=memory,
    )
    goal_text = _compact_goal_text(
        str(plan_goal or "").strip(),
        fallback=_goal_text(goal_type, goal_target, target_semantic),
    )

    if previous and str(previous.get("goal_type") or "") == goal_type and not bool(previous.get("completed", False)):
        goal = copy.deepcopy(previous)
    else:
        goal = {}

    goal.update(
        {
            "goal_type": goal_type,
            "goal_text": goal_text,
            "goal_target": goal_target,
            "target_semantic": target_semantic,
            "progress_state": progress_state,
            "completed": bool(completed),
            "last_action_type": action_type,
            "last_result": outcome,
            "last_recommendation": recommendation,
            "status": "completed" if completed else "active",
        }
    )
    memory.working_memory["active_goal"] = goal


def reflect_on_feedback(
    memory: RobotMemory,
    *,
    action: dict[str, Any],
    reasoning: str,
    ok: bool,
    failed_preconds: list[str],
    world_score_before: float,
    world_score_after: float,
    step: int,
    phase: str = "after_action",
) -> dict[str, Any]:
    delta = round(float(world_score_after) - float(world_score_before), 4)
    reflection = {
        "step": int(step),
        "phase": phase,
        "action_type": str(action.get("action") or ""),
        "target": str(action.get("target") or action.get("object") or ""),
        "target_semantic": _target_semantic(memory, action),
        "ok": bool(ok),
        "score_delta": delta,
        "reasoning": reasoning,
        "failed_preconds": list(failed_preconds or []),
    }
    if not ok:
        reflection["lesson"] = "preconditions were not satisfied, so the action path needs adjustment before retry"
    elif delta > 0.0:
        reflection["lesson"] = "this action was beneficial in the current local context"
    elif delta < 0.0:
        reflection["lesson"] = "this action was risky in the current local context"
    else:
        reflection["lesson"] = "this action was mostly neutral and may have served a setup or sensing role"

    recent_reflections = list(memory.working_memory.get("recent_reflections") or [])
    recent_reflections.append(copy.deepcopy(reflection))
    memory.working_memory["recent_reflections"] = recent_reflections[-8:]

    patterns = list(memory.working_memory.get("patterns") or [])
    patterns.append(
        {
            "kind": "reflection_signal",
            "phase": phase,
            "target": reflection["target"],
            "target_semantic": reflection["target_semantic"],
            "action_type": reflection["action_type"],
            "score_delta": delta,
            "step": int(step),
            "lesson": reflection["lesson"],
        }
    )
    memory.working_memory["patterns"] = patterns[-12:]
    return reflection


def consolidate_experience(
    memory: RobotMemory,
    *,
    action: dict[str, Any],
    plan_goal: str = "",
    ok: bool,
    failed_preconds: list[str],
    immediate_reflection: dict[str, Any],
    world_reflection: dict[str, Any] | None,
    step: int,
) -> dict[str, Any]:
    summary = _summarize_experience(
        memory=memory,
        action=action,
        ok=ok,
        failed_preconds=failed_preconds,
        immediate_reflection=immediate_reflection,
        world_reflection=world_reflection,
        step=step,
    )
    _update_experience_library(memory, summary)
    _update_learned_rules(memory, summary)
    _update_active_goal(memory, action, summary, plan_goal=plan_goal)
    return summary


def summarize_memory(memory: RobotMemory) -> dict[str, Any]:
    _sync_layered_graph(memory)
    known_rooms = sorted(
        node_id
        for node_id, node in memory.node.items()
        if str(node.get("node_type") or "") == "room"
    )
    visited_rooms = sorted(
        node_id
        for node_id, node in memory.node.items()
        if str(node.get("node_type") or "") == "room" and bool(node.get("memory_visited"))
    )
    scanned_node_count = sum(
        1
        for node in memory.node.values()
        if str(node.get("memory_source") or "") in SCAN_SOURCES
    )
    known_control_relations: dict[str, list[str]] = {}
    for edge in memory.edge.values():
        if str(edge.get("relation") or "") != "controls":
            continue
        source_id = str(edge.get("source_id") or "")
        target_id = str(edge.get("target_id") or "")
        known_control_relations.setdefault(source_id, []).append(target_id)

    unscanned_known_controls = sorted(
        node_id
        for node_id, node in memory.node.items()
        if str(node.get("semantic_type") or "") in {"button", "knob", "door"}
        and str(node.get("memory_source") or "") not in SCAN_SOURCES
    )

    robot_action_history = []
    preferred_robot_node = memory.node.get("robot_01") or {}
    if str(preferred_robot_node.get("node_type") or "") == "agent":
        robot_action_history = copy.deepcopy(preferred_robot_node.get("memory_recent_actions") or [])
    else:
        for node in memory.node.values():
            if str(node.get("node_type") or "") == "agent":
                robot_action_history = copy.deepcopy(node.get("memory_recent_actions") or [])
                break
    if not robot_action_history:
        robot_action_history = copy.deepcopy(list(memory.working_memory.get("recent_actions") or []))

    recent_reflections = copy.deepcopy(list(memory.working_memory.get("recent_reflections") or [])[-4:])
    experience_summaries = copy.deepcopy(list(memory.working_memory.get("experience_summaries") or [])[-6:])
    recent_attempts: list[dict[str, Any]] = []
    reflection_by_step = {
        int(item.get("step") or 0): item
        for item in recent_reflections
        if int(item.get("step") or 0) > 0
    }
    for action_item in robot_action_history[-4:]:
        action_payload = copy.deepcopy(action_item.get("action") or {})
        step = int(action_item.get("step") or 0)
        recent_attempts.append(
            {
                "step": step,
                "goal_or_reasoning": str(action_item.get("plan_goal") or action_item.get("reasoning") or "").strip(),
                "action_type": str(action_payload.get("action") or ""),
                "target": str(action_payload.get("target") or action_payload.get("object") or ""),
                "object": str(action_payload.get("object") or ""),
                "ok": bool(action_item.get("ok")),
                "failed_preconds": copy.deepcopy(action_item.get("failed_preconds") or []),
                "world_score_before": action_item.get("world_score_before"),
                "world_score_after_action": action_item.get("world_score_after_action"),
                "world_score_after_world_step": action_item.get("world_score_after_world_step"),
                "reflection": copy.deepcopy(reflection_by_step.get(step) or {}),
            }
        )

    active_goal = copy.deepcopy(memory.working_memory.get("active_goal") or {})
    learned_rules = copy.deepcopy(memory.working_memory.get("learned_rules") or {})
    return {
        "graph": {
            "node_count": len(memory.node),
            "edge_count": len(memory.edge),
        },
        "known_rooms": known_rooms,
        "visited_rooms": visited_rooms,
        "unscanned_known_controls": unscanned_known_controls,
        "scanned_node_count": scanned_node_count,
        "known_control_relations": {key: sorted(value) for key, value in known_control_relations.items()},
        "active_goal": {
            "goal_type": str(active_goal.get("goal_type") or "").strip(),
            "goal_text": str(active_goal.get("goal_text") or "").strip(),
            "goal_target": str(active_goal.get("goal_target") or "").strip(),
            "target_semantic": str(active_goal.get("target_semantic") or "").strip(),
            "progress_state": str(active_goal.get("progress_state") or "").strip(),
            "status": str(active_goal.get("status") or ""),
            "last_action_type": str(active_goal.get("last_action_type") or ""),
            "last_result": str(active_goal.get("last_result") or ""),
            "last_recommendation": str(active_goal.get("last_recommendation") or ""),
            "completed": bool(active_goal.get("completed", False)),
        },
        "recent_attempts": recent_attempts[-3:],
        "last_step_feedback": copy.deepcopy(recent_attempts[-1] if recent_attempts else {}),
        "learned_rules": {
            "operation_rules": copy.deepcopy(list(learned_rules.get("operation_rules") or [])[-4:]),
            "world_rules": copy.deepcopy(list(learned_rules.get("world_rules") or [])[-4:]),
            "human_rules": copy.deepcopy(list(learned_rules.get("human_rules") or [])[-4:]),
        },
        "recent_actions": robot_action_history[-3:],
        "recent_reflections": recent_reflections[-2:],
        "experience_summaries": experience_summaries[-3:],
    }


__all__ = [
    "RobotMemory",
    "consolidate_experience",
    "ensure_robot_memory",
    "load_robot_memory",
    "reflect_on_feedback",
    "remember_action_result",
    "remember_scan",
    "save_robot_memory",
    "summarize_memory",
    "update_memory_from_observation",
]
