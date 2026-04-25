from __future__ import annotations

import copy
from typing import Any

from ..engine.state import build_runtime_state
from .robot_executor import validate_robot_action
from .robot_executor import execute_robot_action
from .robot_planner import (
    ACTION_EFFECTS,
    ALLOWED_ACTIONS,
    default_direct_action,
    default_high_level_plan,
    query_direct_action,
)


DECISION_MODE_LLM = "llm"
DECISION_MODE_PLANNER_ONLY = "planner_only"
EXPLORATION_ACTIONS = {"move", "scan", "press", "open", "close"}
INTERVENTION_ACTIONS = {"brush", "pick", "place", "close", "press", "open"}
ISSUE_ACTION_BONUS = {
    ("rotten", "pick"): 5.0,
    ("dirty", "brush"): 4.5,
    ("open", "close"): 4.0,
    ("risk_on", "press"): 4.5,
    ("misplaced", "pick"): 3.5,
    ("misplaced", "place"): 4.5,
}


def planning_observation_from_memory(observation: dict[str, Any], memory, memory_summary: dict[str, Any]) -> dict[str, Any]:
    planning_observation = copy.deepcopy(observation)
    planning_observation["compressed_observation"] = {
        "world": {
            "step": (observation.get("world") or {}).get("step"),
            "clock": (observation.get("world") or {}).get("clock"),
            "day_phase": (observation.get("world") or {}).get("day_phase"),
            "weather": (observation.get("world") or {}).get("weather"),
            "world_score": (observation.get("scores") or {}).get("world_score"),
            "human_score": (observation.get("scores") or {}).get("human_score"),
        },
        "robot": {
            "id": (observation.get("robot") or {}).get("id"),
            "current_room": (observation.get("robot") or {}).get("current_room"),
            "holding": (observation.get("robot") or {}).get("holding"),
        },
        "current_room_objects": [
            {
                "id": node.get("id"),
                "semantic_type": node.get("semantic_type"),
                "issue_tags": _issue_tags(node),
            }
            for node in list(observation.get("visible_nodes") or [])[:12]
        ],
        "adjacent_rooms": list((observation.get("robot") or {}).get("adjacent_rooms") or []),
        "recent_memory": {
            "active_goal": copy.deepcopy(memory_summary.get("active_goal") or {}),
            "recent_attempts": copy.deepcopy(list(memory_summary.get("recent_attempts") or [])[-3:]),
            "last_step_feedback": copy.deepcopy(memory_summary.get("last_step_feedback") or {}),
            "learned_rules": copy.deepcopy(memory_summary.get("learned_rules") or {}),
        },
    }
    planning_observation["planning_strategy"] = {
        "source": "simple_local_first",
        "current_room": str((observation.get("robot") or {}).get("current_room") or ""),
        "selected_visible_node_count": len(list(observation.get("visible_nodes") or [])),
    }
    return planning_observation


def _belief_confidence(node_or_edge: dict[str, Any], current_step: int) -> float:
    last_step = int(node_or_edge.get("memory_last_observed_step") or 0)
    source = str(node_or_edge.get("memory_source") or "")
    age = max(0, current_step - last_step)
    if source in {"self_position", "adjacency"}:
        base = 0.98
        decay = 0.005
    elif source in {"scan", "scan_local"}:
        base = 0.96
        decay = 0.015
    else:
        base = 0.92
        decay = 0.02
    confidence = max(0.2, base - age * decay)
    return round(confidence, 3)


def _belief_graph_snapshot(observation: dict[str, Any], memory, memory_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    current_step = int((observation.get("world") or {}).get("step") or 0)
    current_room = str((observation.get("robot") or {}).get("current_room") or "")
    adjacent_rooms = [str(room_id) for room_id in ((observation.get("robot") or {}).get("adjacent_rooms") or []) if room_id]
    active_goal = copy.deepcopy((memory_summary or {}).get("active_goal") or {})
    goal_target = str(active_goal.get("goal_target") or "")

    visible_ids = {
        str(node.get("id") or "")
        for node in (observation.get("visible_nodes") or [])
        if str(node.get("id") or "")
    }

    room_nodes: dict[str, dict[str, Any]] = {}
    object_nodes: dict[str, dict[str, Any]] = {}
    for node_id, node in sorted((memory.node or {}).items()):
        entry = {
            "id": node_id,
            "node_type": str(node.get("node_type") or ""),
            "semantic_type": str(node.get("semantic_type") or ""),
            "room_id": str(node.get("room_id") or ""),
            "states": copy.deepcopy(node.get("states") or {}),
            "interactive_actions": list(node.get("interactive_actions") or []),
            "last_observed_step": int(node.get("memory_last_observed_step") or 0),
            "confidence": _belief_confidence(node, current_step),
        }
        if entry["node_type"] == "room":
            room_nodes[node_id] = entry
        elif entry["node_type"] != "agent":
            object_nodes[node_id] = entry

    selected_object_ids: set[str] = set()

    def _add_object(node_id: str) -> None:
        if node_id and node_id in object_nodes:
            selected_object_ids.add(node_id)

    # Layer 1: keep the current room local graph in full.
    for node_id, node in object_nodes.items():
        if str(node.get("room_id") or "") == current_room:
            _add_object(node_id)

    # Layer 2: for adjacent rooms, keep only the most relevant objects.
    def _object_priority(node: dict[str, Any]) -> tuple[int, float, int, str]:
        issue_count = len(_issue_tags(node))
        is_goal = 1 if goal_target and str(node.get("id") or "") == goal_target else 0
        is_recent = 1 if current_step - int(node.get("last_observed_step") or 0) <= 2 else 0
        is_visible = 1 if str(node.get("id") or "") in visible_ids else 0
        return (
            issue_count + is_goal + is_recent + is_visible,
            float(node.get("confidence") or 0.0),
            -int(node.get("last_observed_step") or 0),
            str(node.get("id") or ""),
        )

    for room_id in adjacent_rooms:
        room_objects = [
            node for node in object_nodes.values()
            if str(node.get("room_id") or "") == room_id
        ]
        room_objects.sort(key=_object_priority, reverse=True)
        for node in room_objects[:4]:
            _add_object(str(node.get("id") or ""))

    # Layer 3: keep globally recent/high-confidence/goal objects.
    extra_candidates = list(object_nodes.values())
    extra_candidates.sort(key=_object_priority, reverse=True)
    for node in extra_candidates:
        if len(selected_object_ids) >= 20:
            break
        if (
            str(node.get("id") or "") == goal_target
            or len(_issue_tags(node)) > 0
            or current_step - int(node.get("last_observed_step") or 0) <= 1
            or float(node.get("confidence") or 0.0) >= 0.95
        ):
            _add_object(str(node.get("id") or ""))

    selected_room_ids: set[str] = set()
    if current_room:
        selected_room_ids.add(current_room)
    selected_room_ids.update(adjacent_rooms)
    if goal_target and goal_target in object_nodes:
        goal_room = str(object_nodes[goal_target].get("room_id") or "")
        if goal_room:
            selected_room_ids.add(goal_room)
    for node_id in selected_object_ids:
        room_id = str(object_nodes[node_id].get("room_id") or "")
        if room_id:
            selected_room_ids.add(room_id)

    rooms = [room_nodes[room_id] for room_id in sorted(selected_room_ids) if room_id in room_nodes]
    objects = [object_nodes[node_id] for node_id in sorted(selected_object_ids)]

    relations: list[dict[str, Any]] = []
    for edge in sorted((memory.edge or {}).values(), key=lambda item: (str(item.get("relation") or ""), str(item.get("source_id") or ""), str(item.get("target_id") or ""))):
        relation = str(edge.get("relation") or "")
        if relation not in {"adjacent_to", "contains", "controls"}:
            continue
        source_id = str(edge.get("source_id") or "")
        target_id = str(edge.get("target_id") or "")
        if relation == "adjacent_to":
            if source_id not in selected_room_ids or target_id not in selected_room_ids:
                continue
        elif relation == "contains":
            source_ok = source_id in selected_room_ids or source_id in selected_object_ids
            target_ok = target_id in selected_object_ids or target_id in selected_room_ids
            if not (source_ok and target_ok):
                continue
        elif relation == "controls":
            if source_id not in selected_object_ids or target_id not in selected_object_ids:
                continue
        relations.append(
            {
                "source_id": source_id,
                "relation": relation,
                "target_id": target_id,
                "last_observed_step": int(edge.get("memory_last_observed_step") or 0),
                "confidence": _belief_confidence(edge, current_step),
            }
        )

    return {
        "world": {
            "step": (observation.get("compressed_observation") or {}).get("world", {}).get("step"),
            "clock": (observation.get("compressed_observation") or {}).get("world", {}).get("clock"),
            "world_score": (observation.get("compressed_observation") or {}).get("world", {}).get("world_score"),
            "human_score": (observation.get("compressed_observation") or {}).get("world", {}).get("human_score"),
        },
        "robot": {
            "id": (observation.get("compressed_observation") or {}).get("robot", {}).get("id"),
            "current_room": current_room,
            "holding": (observation.get("compressed_observation") or {}).get("robot", {}).get("holding"),
        },
        "rooms": rooms[:6],
        "objects": objects[:20],
        "relations": relations[:48],
    }


def _recent_action_key(action: dict[str, Any]) -> tuple[str, str, str]:
    payload = action.get("action") or {}
    return (
        str(payload.get("action") or payload.get("action_type") or ""),
        str(payload.get("target") or payload.get("object") or ""),
        str(payload.get("placement_target_id") or payload.get("placement_target") or ""),
    )


def _recent_action_outcome(action: dict[str, Any]) -> str:
    return str(action.get("outcome") or action.get("experience_outcome") or "").strip().lower()


def _recent_action_delta(action: dict[str, Any]) -> float:
    after = action.get("world_score_after")
    before = action.get("world_score_before")
    if after is None or before is None:
        return 0.0
    return float(after) - float(before)


def _grounded_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("action_type") or ""),
        str(candidate.get("target_id") or candidate.get("object_id") or ""),
        str(candidate.get("placement_target_id") or ""),
    )


def _is_stuck_repeating(candidate: dict[str, Any], recent_actions: list[dict[str, Any]]) -> bool:
    comparable = [item for item in recent_actions[-12:] if _recent_action_key(item) == _grounded_key(candidate)]
    if len(comparable) < 2:
        return False
    recent_tail = comparable[-4:]
    risky_or_blocked = sum(_recent_action_outcome(item) in {"risky", "blocked"} for item in recent_tail)
    non_positive = sum(_recent_action_delta(item) <= 0.0 for item in recent_tail)
    if risky_or_blocked >= 2:
        return True
    if len(recent_tail) >= 3 and non_positive == len(recent_tail):
        return True
    return False


def _issue_tags(node: dict[str, Any]) -> list[str]:
    states = node.get("states") or {}
    semantic = str(node.get("semantic_type") or "")
    tags: list[str] = []
    if bool(states.get("is_rotten")):
        tags.append("rotten")
    if bool(states.get("is_dirty")) or float(states.get("cleanliness", 1.0)) < 0.5:
        tags.append("dirty")
    if bool(states.get("is_open")) and semantic == "door":
        tags.append("open")
    if bool(states.get("is_on")) and semantic in {"stove", "faucet", "washer", "washing_machine", "microwave", "dishwasher"}:
        tags.append("risk_on")
    if states.get("misplaced_near") or states.get("scattered"):
        tags.append("misplaced")
    return tags


def _preferred_issue_actions(node: dict[str, Any]) -> list[str]:
    preferred: list[str] = []
    for tag in _issue_tags(node):
        if tag == "rotten":
            preferred.append("pick")
        elif tag == "dirty":
            preferred.append("brush")
        elif tag == "open":
            preferred.append("close")
        elif tag == "risk_on":
            preferred.append("press")
        elif tag == "misplaced":
            preferred.append("pick")
    deduped: list[str] = []
    for action_type in preferred:
        if action_type not in deduped:
            deduped.append(action_type)
    return deduped


def _memory_issue_nodes(memory, room_ids: set[str], visible_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node_id, node in (memory.node or {}).items():
        if not node_id or node_id in visible_by_id:
            continue
        if str(node.get("room_id") or "") not in room_ids:
            continue
        issue_tags = _issue_tags(node)
        if not issue_tags:
            continue
        payload = {
            "id": node.get("id"),
            "name": node.get("name"),
            "name_cn": node.get("name_cn"),
            "node_type": node.get("node_type"),
            "semantic_type": node.get("semantic_type"),
            "parent": node.get("parent"),
            "states": copy.deepcopy(node.get("states") or {}),
            "interactive_actions": list(node.get("interactive_actions") or []),
            "room_id": node.get("room_id"),
            "issue_tags": issue_tags,
        }
        if payload["id"] and payload["id"] not in seen:
            seen.add(str(payload["id"]))
            candidates.append(payload)
    return candidates


def _memory_room_issue_hints(memory, known_rooms: list[str], current_room: str) -> list[dict[str, Any]]:
    room_counts: dict[str, dict[str, Any]] = {}
    for node in (memory.node or {}).values():
        room_id = str(node.get("room_id") or "")
        if not room_id or room_id == current_room:
            continue
        issue_tags = _issue_tags(node)
        if not issue_tags:
            continue
        entry = room_counts.setdefault(
            room_id,
            {"room_id": room_id, "issue_count": 0, "issue_tags": [], "example_targets": []},
        )
        entry["issue_count"] += len(issue_tags)
        for tag in issue_tags:
            if tag not in entry["issue_tags"]:
                entry["issue_tags"].append(tag)
        target_id = str(node.get("id") or "")
        if target_id and len(entry["example_targets"]) < 4 and target_id not in entry["example_targets"]:
            entry["example_targets"].append(target_id)

    ordered = sorted(
        room_counts.values(),
        key=lambda item: (int(item.get("issue_count") or 0), str(item.get("room_id") or "") in known_rooms),
        reverse=True,
    )
    return ordered[:6]


def _blocked_issue_intents(
    raw_scene: dict[str, Any],
    runtime_state: dict | None,
    issue_nodes: list[dict[str, Any]],
    agent_id: str,
) -> list[dict[str, Any]]:
    blocked: list[dict[str, Any]] = []
    for node in issue_nodes:
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        for action_type in _preferred_issue_actions(node):
            payload = {"agent": agent_id, "action": action_type, "target": node_id}
            if action_type == "pick":
                payload["object"] = node_id
            validated = validate_robot_action(raw_scene, payload, runtime_state=runtime_state)
            if validated.get("ok"):
                continue
            blocked.append(
                {
                    "target_id": node_id,
                    "target_semantic": str(node.get("semantic_type") or ""),
                    "issue_tags": list(node.get("issue_tags") or _issue_tags(node)),
                    "desired_action": action_type,
                    "action_payload": payload,
                    "failed_preconds": list(validated.get("failed_preconds") or []),
                }
            )
    return blocked


def _is_direct_issue_intervention(candidate: dict[str, Any]) -> bool:
    action_type = str(candidate.get("action_type") or "")
    for tag in candidate.get("issue_tags") or []:
        if ISSUE_ACTION_BONUS.get((tag, action_type), 0.0) > 0.0:
            return True
    return False


def _candidate_follow_up_issue_targets(
    raw_scene: dict[str, Any],
    runtime_state: dict | None,
    candidate: dict[str, Any],
    blocked_intents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not blocked_intents:
        return []
    execution = execute_robot_action(raw_scene, copy.deepcopy(candidate.get("action_payload") or {}), runtime_state=runtime_state)
    if not execution.get("ok"):
        return []
    simulated_state = execution.get("runtime_state")
    enabled: list[dict[str, Any]] = []
    for blocked in blocked_intents:
        validated = validate_robot_action(raw_scene, copy.deepcopy(blocked.get("action_payload") or {}), runtime_state=simulated_state)
        if not validated.get("ok"):
            continue
        enabled.append(
            {
                "target_id": blocked.get("target_id"),
                "target_semantic": blocked.get("target_semantic"),
                "desired_action": blocked.get("desired_action"),
                "issue_tags": copy.deepcopy(blocked.get("issue_tags") or []),
            }
        )
    return enabled


def _legal_action_space(
    raw_scene: dict[str, Any],
    runtime_state: dict | None,
    observation: dict[str, Any],
    memory_summary: dict[str, Any],
    memory,
    agent_id: str,
) -> list[dict[str, Any]]:
    robot = observation.get("robot") or {}
    visible_nodes = list(observation.get("visible_nodes") or [])
    visible_by_id = {str(node.get("id") or ""): node for node in visible_nodes if node.get("id")}
    current_room = str(robot.get("current_room") or "")
    holding = str(robot.get("holding") or "")
    candidates: list[dict[str, Any]] = []
    state = copy.deepcopy(runtime_state) if runtime_state is not None else build_runtime_state(copy.deepcopy(raw_scene))

    for room_id in robot.get("adjacent_rooms") or []:
        action = {"agent": agent_id, "action": "move", "target": str(room_id)}
        validated = validate_robot_action(raw_scene, action, runtime_state=runtime_state)
        if not validated.get("ok"):
            continue
        candidates.append(
            {
                "action_type": "move",
                "target_id": str(room_id),
                "target_semantic": "room",
                "issue_tags": [],
                "action_payload": action,
            }
        )

    current_and_adjacent_rooms = {current_room}
    current_and_adjacent_rooms.update(str(room_id) for room_id in (robot.get("adjacent_rooms") or []) if room_id)
    issue_nodes = list(visible_nodes)
    issue_nodes.extend(_memory_issue_nodes(memory, current_and_adjacent_rooms, visible_by_id))

    for node in visible_nodes:
        node_id = str(node.get("id") or "")
        actions = {str(item).lower() for item in (node.get("interactive_actions") or [])}
        issue_tags = _issue_tags(node)
        semantic = str(node.get("semantic_type") or "")
        for action_type in actions:
            if action_type not in ALLOWED_ACTIONS or action_type == "place":
                continue
            action = {"agent": agent_id, "action": action_type, "target": node_id}
            if action_type == "pick":
                action["object"] = node_id
            validated = validate_robot_action(raw_scene, action, runtime_state=runtime_state)
            if not validated.get("ok"):
                continue
            candidates.append(
                {
                    "action_type": action_type,
                    "target_id": node_id,
                    "target_semantic": semantic,
                    "issue_tags": issue_tags,
                    "action_payload": action,
                }
            )

        if holding and "place" in actions:
            action = {"agent": agent_id, "action": "place", "object": holding, "target": node_id}
            validated = validate_robot_action(raw_scene, action, runtime_state=runtime_state)
            if not validated.get("ok"):
                continue
            candidates.append(
                {
                    "action_type": "place",
                    "object_id": holding,
                    "placement_target_id": node_id,
                    "target_id": node_id,
                    "target_semantic": semantic,
                    "issue_tags": issue_tags,
                    "action_payload": action,
                }
            )

    for node in issue_nodes:
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        actions = {str(item).lower() for item in (node.get("interactive_actions") or [])}
        issue_tags = list(node.get("issue_tags") or _issue_tags(node))
        semantic = str(node.get("semantic_type") or "")
        for action_type in _preferred_issue_actions(node):
            if action_type not in actions or action_type not in ALLOWED_ACTIONS or action_type == "place":
                continue
            action = {"agent": agent_id, "action": action_type, "target": node_id}
            if action_type == "pick":
                action["object"] = node_id
            validated = validate_robot_action(raw_scene, action, runtime_state=runtime_state)
            if not validated.get("ok"):
                continue
            candidates.append(
                {
                    "action_type": action_type,
                    "target_id": node_id,
                    "target_semantic": semantic,
                    "issue_tags": issue_tags,
                    "action_payload": action,
                    "candidate_source": "memory_issue",
                }
            )

    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    recent_actions = list(memory_summary.get("recent_actions") or [])
    for candidate in candidates:
        if _is_stuck_repeating(candidate, recent_actions):
            continue
        key = _grounded_key(candidate)
        deduped[key] = candidate

    def _sort_key(candidate: dict[str, Any]) -> tuple[int, int, str, str]:
        action_type = str(candidate.get("action_type") or "")
        issue_count = len(candidate.get("issue_tags") or [])
        if issue_count > 0:
            priority = 0
        elif action_type == "move" and str(candidate.get("target_semantic") or "") == "room":
            priority = 1
        elif action_type in {"close", "press", "brush", "pick", "place", "open"}:
            priority = 2
        else:
            priority = 3
        return (priority, -issue_count, action_type, str(candidate.get("target_id") or ""))

    return sorted(deduped.values(), key=_sort_key)


def retrieved_memory(observation: dict[str, Any], memory, memory_summary: dict[str, Any]) -> dict[str, Any]:
    current_room = str((observation.get("robot") or {}).get("current_room") or "")
    known_rooms = list(memory_summary.get("known_rooms") or [])
    room_facts: list[dict[str, Any]] = []
    if current_room:
        for edge in (memory.edge or {}).values():
            if str(edge.get("source_id") or "") == current_room or str(edge.get("target_id") or "") == current_room:
                relation = str(edge.get("relation") or "")
                if relation in {"adjacent_to", "contains", "controls"}:
                    room_facts.append(
                        {
                            "source_id": edge.get("source_id"),
                            "relation": relation,
                            "target_id": edge.get("target_id"),
                        }
                    )
            if len(room_facts) >= 4:
                break

    learned_rules = copy.deepcopy(memory_summary.get("learned_rules") or {})
    return {
        "room_facts": room_facts[:2],
        "active_goal": {
            "goal_type": str(((memory_summary.get("active_goal") or {}).get("goal_type") or "")).strip(),
            "goal_text": str(((memory_summary.get("active_goal") or {}).get("goal_text") or "")).strip(),
            "goal_target": str(((memory_summary.get("active_goal") or {}).get("goal_target") or "")).strip(),
            "progress_state": str(((memory_summary.get("active_goal") or {}).get("progress_state") or "")).strip(),
            "completed": bool((memory_summary.get("active_goal") or {}).get("completed", False)),
        },
        "recent_attempts": [
            {
                "action_type": str(item.get("action_type") or ""),
                "target": str(item.get("target") or ""),
                "ok": bool(item.get("ok")),
            }
            for item in list(memory_summary.get("recent_attempts") or [])[-1:]
        ],
        "last_step_feedback": {
            "action_type": str(((memory_summary.get("last_step_feedback") or {}).get("action_type") or "")).strip(),
            "target": str(((memory_summary.get("last_step_feedback") or {}).get("target") or "")).strip(),
            "ok": bool((memory_summary.get("last_step_feedback") or {}).get("ok")),
            "score_became_better": bool((memory_summary.get("last_step_feedback") or {}).get("score_became_better")),
        },
        "learned_rules": {
            "operation_rules": copy.deepcopy(list(learned_rules.get("operation_rules") or [])[-2:]),
            "world_rules": copy.deepcopy(list(learned_rules.get("world_rules") or [])[-1:]),
            "human_rules": copy.deepcopy(list(learned_rules.get("human_rules") or [])[-1:]),
        },
        "recent_ineffective_actions": [
            {
                "action_type": str(item.get("action_type") or ""),
                "target": str(item.get("target") or ""),
                "reason": "repeated_ineffective" if bool(item.get("repeated_ineffective")) else "score_not_improving",
            }
            for item in list(memory_summary.get("recent_reflections") or [])[-1:]
            if bool(item.get("repeated_ineffective")) or float(item.get("score_delta") or 0.0) <= 0.0
        ],
        "room_issue_hints": _memory_room_issue_hints(memory, known_rooms, current_room),
    }


def intent_packet(observation: dict[str, Any], memory_summary: dict[str, Any], retrieved: dict[str, Any]) -> dict[str, Any]:
    _ = retrieved
    active_goal = copy.deepcopy(memory_summary.get("active_goal") or {})
    last_step_feedback = copy.deepcopy(memory_summary.get("last_step_feedback") or {})
    return {
        "current_state_graph": {},
        "current_focus": {
            "goal_text": str(active_goal.get("goal_text") or "").strip(),
            "goal_type": str(active_goal.get("goal_type") or "").strip(),
            "goal_target": str(active_goal.get("goal_target") or "").strip(),
            "status": str(active_goal.get("status") or "").strip(),
            "last_action": str(last_step_feedback.get("action_type") or "").strip(),
            "last_action_result": str((last_step_feedback.get("reflection") or {}).get("lesson") or active_goal.get("last_result") or "").strip(),
        },
        "action_candidates": [],
    }


def _compact_legal_action_space(action_space: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in action_space[:12]:
        compact.append(
            {
                "action_type": item.get("action_type"),
                "target_id": item.get("target_id"),
                "object_id": item.get("object_id"),
                "placement_target_id": item.get("placement_target_id"),
            }
        )
    return compact


def _review_previous_goal(memory_summary: dict[str, Any]) -> dict[str, Any]:
    last_feedback = copy.deepcopy(memory_summary.get("last_step_feedback") or {})
    active_goal = copy.deepcopy(memory_summary.get("active_goal") or {})
    if not last_feedback:
        return {
            "has_previous_goal": False,
            "goal_completed": False,
            "recommended_focus": "explore",
            "next_goal": "",
            "why": "no previous step memory yet",
        }

    goal_text = str(active_goal.get("goal_text") or last_feedback.get("goal_or_reasoning") or "").strip()
    reflection = copy.deepcopy(last_feedback.get("reflection") or {})
    ok = bool(last_feedback.get("ok"))
    score_after_world = last_feedback.get("world_score_after_world_step")
    score_before = last_feedback.get("world_score_before")
    score_delta = None
    if score_after_world is not None and score_before is not None:
        score_delta = round(float(score_after_world) - float(score_before), 4)
    resolved_count = int(reflection.get("resolved_issue_count") or 0)
    repeated_ineffective = bool(reflection.get("repeated_ineffective"))
    goal_completed = bool(active_goal.get("completed")) or resolved_count > 0 or (ok and score_delta is not None and score_delta > 0.02)

    if goal_completed:
        recommended_focus = "verify"
        next_goal = "verify whether the previous improvement holds, then pick the next urgent task"
        why = "previous step improved the situation enough to treat the current subgoal as tentatively completed"
    elif not ok or repeated_ineffective:
        recommended_focus = "recover"
        next_goal = "change tactic or target because the previous plan did not work"
        why = "previous step failed or repeated without helping"
    else:
        recommended_focus = "support"
        next_goal = goal_text or "continue the previous useful subgoal"
        why = "previous step was not clearly bad, so continuing or tightening the same goal is reasonable"

    return {
        "has_previous_goal": True,
        "goal_text": goal_text,
        "goal_type": str(active_goal.get("goal_type") or ""),
        "goal_target": str(active_goal.get("goal_target") or ""),
        "progress_state": str(active_goal.get("progress_state") or ""),
        "goal_completed": goal_completed,
        "recommended_focus": recommended_focus,
        "next_goal": next_goal[:48],
        "score_delta_from_previous_goal": score_delta,
        "previous_action_type": str(last_feedback.get("action_type") or ""),
        "previous_target": str(last_feedback.get("target") or ""),
        "why": why[:48],
    }


def _normalize_direct_decision(decision: dict[str, Any]) -> dict[str, Any]:
    action_type = str(decision.get("action") or decision.get("action_type") or "").strip().lower()
    target = str(decision.get("target") or decision.get("target_id") or "").strip()
    object_id = str(decision.get("object") or decision.get("object_id") or "").strip()
    placement_target_id = str(decision.get("placement_target_id") or "").strip()
    normalized = {
        "reasoning": str(decision.get("reasoning") or "").strip(),
        "action": action_type,
        "target": placement_target_id or target,
        "raw_response": str(decision.get("raw_response") or ""),
        "grounding": {"selected": None, "candidates": []},
    }
    if object_id:
        normalized["object"] = object_id
    return normalized


def _legal_action_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(item.get("action_type") or item.get("action") or ""),
        str(item.get("target_id") or ""),
        str(item.get("object_id") or ""),
        str(item.get("placement_target_id") or ""),
    )


def _decision_matches_legal_action(decision: dict[str, Any], action_space: list[dict[str, Any]]) -> bool:
    candidate_key = (
        str(decision.get("action") or ""),
        str(decision.get("target") or ""),
        str(decision.get("object") or ""),
        str(decision.get("target") if str(decision.get("action") or "") == "place" else ""),
    )
    for item in action_space:
        placement_target_id = str(item.get("placement_target_id") or "")
        legal_key = (
            str(item.get("action_type") or ""),
            str(placement_target_id or item.get("target_id") or ""),
            str(item.get("object_id") or ""),
            placement_target_id if str(item.get("action_type") or "") == "place" else "",
        )
        if candidate_key == legal_key:
            return True
    return False


def _candidate_score(
    candidate: dict[str, Any],
    plan: dict[str, Any],
    observation: dict[str, Any],
    recent_actions: list[dict[str, Any]],
) -> float:
    action_type = str(candidate.get("action_type") or "")
    target_id = str(candidate.get("target_id") or candidate.get("object_id") or "")
    semantic = str(candidate.get("target_semantic") or "")
    score = 0.0
    local_issue_exists = any(_issue_tags(node) for node in (observation.get("visible_nodes") or []))
    direct_issue_fix = _is_direct_issue_intervention(candidate)
    focus = str(plan.get("focus") or "")

    if direct_issue_fix:
        score += 16.0
    if focus in {"intervene", "recover", "support"} and action_type == "move":
        score -= 4.0

    if local_issue_exists:
        if direct_issue_fix:
            score += 8.0
        elif action_type == "scan":
            score += 2.0
        elif action_type == "move":
            score -= 6.0
        else:
            score -= 2.0
    else:
        if action_type == "move" and semantic == "room":
            score += 14.0
        elif action_type == "scan":
            score += 4.0
        elif action_type in {"pick", "place", "brush", "press", "close", "open"}:
            score -= 1.0

    target_ids = list(plan.get("target_ids") or [])
    if target_id in target_ids:
        score += 2.0

    preferred = list(plan.get("preferred_action_types") or [])
    if action_type in preferred:
        score += max(0.0, 3.0 - preferred.index(action_type) * 0.5)

    if _is_stuck_repeating(candidate, recent_actions):
        score -= 5.0
    return score


def ground_high_level_plan(
    plan: dict[str, Any],
    action_space: list[dict[str, Any]],
    observation: dict[str, Any],
    memory_summary: dict[str, Any],
) -> dict[str, Any]:
    if not action_space:
        return {
            "error": "no legal grounded actions available",
            "reasoning": str(plan.get("intent") or ""),
            "grounding": {"candidates": [], "selected": None},
        }

    scored: list[dict[str, Any]] = []
    recent_actions = list(memory_summary.get("recent_actions") or [])
    for candidate in action_space:
        enriched = copy.deepcopy(candidate)
        enriched["grounding_score"] = round(_candidate_score(candidate, plan, observation, recent_actions), 4)
        scored.append(enriched)
    scored.sort(key=lambda item: (float(item.get("grounding_score") or 0.0), str(item.get("action_type") or "")), reverse=True)

    selected = scored[0]
    action_payload = copy.deepcopy(selected.get("action_payload") or {})
    decision: dict[str, Any] = {
        "reasoning": str(plan.get("intent") or plan.get("reasoning") or "").strip(),
        "action": str(action_payload.get("action") or ""),
        "target": str(action_payload.get("target") or ""),
        "raw_response": str(plan.get("raw_response") or ""),
        "grounding": {
            "selected": {
                "action_type": selected.get("action_type"),
                "target_id": selected.get("target_id"),
                "object_id": selected.get("object_id"),
                "placement_target_id": selected.get("placement_target_id"),
                "target_semantic": selected.get("target_semantic"),
                "issue_tags": copy.deepcopy(selected.get("issue_tags") or []),
                "grounding_score": selected.get("grounding_score"),
            },
            "candidates": [
                {
                    "action_type": item.get("action_type"),
                    "target_id": item.get("target_id"),
                    "object_id": item.get("object_id"),
                    "placement_target_id": item.get("placement_target_id"),
                    "target_semantic": item.get("target_semantic"),
                    "issue_tags": copy.deepcopy(item.get("issue_tags") or []),
                    "grounding_score": item.get("grounding_score"),
                }
                for item in scored[:8]
            ],
        },
    }
    if action_payload.get("object"):
        decision["object"] = str(action_payload.get("object"))
    return decision


def planner_only_decision(
    observation: dict[str, Any],
    memory_summary: dict[str, Any],
    action_space: list[dict[str, Any]],
    packet: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = default_high_level_plan(packet)
    decision = ground_high_level_plan(plan, action_space, observation, memory_summary)
    return plan, decision


def build_reasoning_context(
    observation: dict[str, Any],
    memory_summary: dict[str, Any],
    planner_output: dict[str, Any],
    retrieved: dict[str, Any],
    packet: dict[str, Any],
    action_space: list[dict[str, Any]],
    grounding: dict[str, Any],
) -> dict[str, Any]:
    enriched = dict(observation)
    enriched["memory"] = memory_summary
    enriched["planner"] = planner_output
    enriched["retrieved_memory"] = retrieved
    enriched["decision_packet"] = packet
    enriched["action_space"] = copy.deepcopy(action_space[:12])
    enriched["grounding"] = copy.deepcopy(grounding)
    return enriched


def decide_next_action(
    raw_scene: dict[str, Any],
    runtime_state: dict | None,
    observation: dict[str, Any],
    memory,
    *,
    decision_mode: str,
    agent_model: str,
    timeout: int,
    enable_search: bool,
    image_path: str | None,
    memory_summary: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    planning_observation = planning_observation_from_memory(observation, memory, memory_summary)
    retrieved = retrieved_memory(planning_observation, memory, memory_summary)
    packet = intent_packet(planning_observation, memory_summary, retrieved)
    packet["current_state_graph"] = _belief_graph_snapshot(planning_observation, memory)
    action_space = _legal_action_space(
        raw_scene,
        runtime_state,
        planning_observation,
        memory_summary,
        memory,
        str((planning_observation.get("robot") or {}).get("id") or "robot_01"),
    )
    packet["action_candidates"] = _compact_legal_action_space(action_space)

    if decision_mode == DECISION_MODE_PLANNER_ONLY:
        planner_output, decision = planner_only_decision(planning_observation, memory_summary, action_space, packet)
    else:
        planner_output = {
            "mode": "single_inference",
            "reasoning": "",
            "current_goal": "",
            "source": "llm_single_step",
        }
        direct_output = query_direct_action(
            packet,
            agent_model=agent_model,
            timeout=timeout,
            enable_search=enable_search,
            image_path=image_path,
        )
        if direct_output.get("error"):
            fallback = default_direct_action(packet)
            fallback["fallback_reason"] = direct_output.get("error")
            direct_output = fallback
        decision = _normalize_direct_decision(direct_output)
        planner_output["reasoning"] = str(direct_output.get("reasoning") or "")
        planner_output["current_goal"] = str(direct_output.get("current_goal") or "")
        planner_output["direct_action"] = copy.deepcopy(direct_output)
        if not _decision_matches_legal_action(decision, action_space):
            retry_packet = copy.deepcopy(packet)
            retry_packet["validation_error"] = "previous action was not in action_candidates; choose an exact legal action now"
            retry_packet["previous_invalid_action"] = {
                "action_type": decision.get("action"),
                "target_id": decision.get("target"),
                "object_id": decision.get("object", ""),
            }
            retry_output = query_direct_action(
                retry_packet,
                agent_model=agent_model,
                timeout=timeout,
                enable_search=enable_search,
                image_path=image_path,
            )
            if not retry_output.get("error"):
                retry_decision = _normalize_direct_decision(retry_output)
                if _decision_matches_legal_action(retry_decision, action_space):
                    direct_output = retry_output
                    decision = retry_decision
            if not _decision_matches_legal_action(decision, action_space):
                fallback = default_direct_action(packet)
                fallback["fallback_reason"] = "llm_selected_illegal_action_twice"
                direct_output = fallback
                decision = _normalize_direct_decision(direct_output)
            planner_output["direct_action"] = copy.deepcopy(direct_output)
            planner_output["reasoning"] = str(direct_output.get("reasoning") or planner_output.get("reasoning") or "")
            planner_output["current_goal"] = str(direct_output.get("current_goal") or planner_output.get("current_goal") or "")

    reasoning_context = build_reasoning_context(
        planning_observation,
        memory_summary,
        planner_output,
        retrieved,
        packet,
        action_space,
        decision.get("grounding") or {},
    )
    return planner_output, reasoning_context, decision


__all__ = [
    "DECISION_MODE_LLM",
    "DECISION_MODE_PLANNER_ONLY",
    "build_reasoning_context",
    "decide_next_action",
    "intent_packet",
    "planner_only_decision",
    "planning_observation_from_memory",
    "retrieved_memory",
]
