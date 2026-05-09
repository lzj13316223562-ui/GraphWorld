from __future__ import annotations

from typing import Any

from backend.core.actions import ActionType
from backend.runtime.engine import Orchestrator


ACTION_ORDER = tuple(action.value for action in ActionType)


def held_object(orchestrator: Orchestrator, agent_id: str = "robot_01") -> str:
    return orchestrator.graph.held_by(agent_id)


def candidate_payload(
    orchestrator: Orchestrator,
    action: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    validation = orchestrator.robot_actions.validate(action)
    return {
        **action,
        "reason": reason,
        "legal": validation.ok,
        "validation_failures": list(validation.failures),
    }


def candidate_actions(orchestrator: Orchestrator, observation: dict[str, Any], agent_id: str = "robot_01") -> list[dict[str, Any]]:
    graph = orchestrator.graph
    candidates: list[dict[str, Any]] = []
    visible_nodes = [graph.nodes.get(str(item.get("id") or "")) or {} for item in observation.get("nodes") or []]
    visible_ids = {str(node.get("id") or "") for node in visible_nodes if node.get("id")}
    holding = held_object(orchestrator, agent_id)
    for room_id in sorted((observation.get("world_state") or {}).get("visible_rooms") or []):
        if room_id and room_id != graph.room_of.get(agent_id):
            candidate = candidate_payload(
                orchestrator,
                {"agent": agent_id, "action": "move", "target": room_id},
                reason="move to visible room",
            )
            if candidate["legal"]:
                candidates.append(candidate)
    for node_id in sorted(visible_ids):
        item = graph.nodes.get(node_id) or {}
        if not item or node_id == agent_id:
            continue
        states = item.get("states") or {}
        actions = {str(action).lower() for action in item.get("interactive_actions") or []}
        if str(item.get("node_type") or "") in {"fixed_object", "control_object"}:
            candidate = candidate_payload(
                orchestrator,
                {"agent": agent_id, "action": "move", "target": node_id},
                reason="move near visible object",
            )
            if candidate["legal"]:
                candidates.append(candidate)
        for action_name in ACTION_ORDER:
            if action_name == "move":
                continue
            if action_name == "place":
                if not holding:
                    continue
                action = {"agent": agent_id, "action": "place", "target": node_id, "object": holding}
            elif action_name == "pick":
                action = {"agent": agent_id, "action": "pick", "target": node_id, "object": node_id}
            else:
                action = {"agent": agent_id, "action": action_name, "target": node_id}
            reason = f"{action_name} visible object"
            if action_name in actions or action_name in {"move", "place"}:
                if states.get("is_dirty") is True and action_name == "brush":
                    reason = "restore dirty object"
                elif states.get("is_open") is True and action_name == "close":
                    reason = "close open object"
                candidate = candidate_payload(orchestrator, action, reason=reason)
                if candidate["legal"]:
                    candidates.append(candidate)
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = (
            str(candidate.get("action") or ""),
            str(candidate.get("target") or ""),
            str(candidate.get("object") or ""),
        )
        deduped[key] = candidate
    return sorted(
        deduped.values(),
        key=lambda item: (
            not bool(item.get("legal")),
            ACTION_ORDER.index(str(item.get("action") or "")) if str(item.get("action") or "") in ACTION_ORDER else 99,
            str(item.get("target") or ""),
        ),
    )


def plan(memory: dict[str, Any], task: str = "maintain_order") -> list[dict[str, Any]]:
    nodes = memory.get("nodes") or {}
    candidates: list[dict[str, Any]] = []
    for node_id, node in sorted(nodes.items()):
        states = node.get("states") or {}
        if str(node.get("door_kind") or "") in {"structural", "device"} and bool(states.get("is_open", False)):
            candidates.append(
                {
                    "action": "close",
                    "target": node_id,
                    "reason": "close open door",
                    "priority": 10,
                }
            )
    for node_id, node in sorted(nodes.items()):
        if bool((node.get("states") or {}).get("is_dirty", False)):
            candidates.append(
                {
                    "action": "brush",
                    "target": node_id,
                    "reason": "clean dirty object",
                    "priority": 8,
                }
            )
    return candidates


__all__ = ["ACTION_ORDER", "candidate_actions", "candidate_payload", "held_object", "plan"]
