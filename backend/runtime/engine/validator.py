from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.core.actions import ActionType


MOVABLE_NODE_TYPES = {"movable_object"}
PLACE_TARGET_TYPES = {"room", "fixed_object", "control_object"}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    failures: tuple[str, ...] = ()

    @property
    def reason(self) -> str:
        return "; ".join(self.failures)


def _node(state: dict[str, Any], node_id: str) -> dict[str, Any]:
    return state.get("nodes", {}).get(node_id) or {}


def _states(node: dict[str, Any]) -> dict[str, Any]:
    return node.get("states") or {}


def _semantic(node: dict[str, Any]) -> str:
    return str(node.get("semantic_type") or "").lower()


def _node_type(node: dict[str, Any]) -> str:
    return str(node.get("node_type") or "").lower()


def _room_of(state: dict[str, Any], node_id: str) -> str:
    return str(state.get("room_of", {}).get(node_id) or "")


def _same_room(state: dict[str, Any], a: str, b: str) -> bool:
    room_a = _room_of(state, a)
    room_b = _room_of(state, b)
    if room_a and room_a == room_b:
        return True
    target = _node(state, b)
    connected_rooms = {str(room_id) for room_id in target.get("connected_rooms") or []}
    return bool(room_a and room_a in connected_rooms)


def _agent_holding(state: dict[str, Any], agent_id: str) -> str:
    parent_of = state.get("parent_of", {})
    relation_of = state.get("relation_of", {})
    for node_id, parent_id in parent_of.items():
        if parent_id == agent_id and relation_of.get(node_id) == "held_by":
            return node_id
    return ""


def _is_open(node: dict[str, Any]) -> bool:
    return bool(_states(node).get("is_open", False))


def _requires_closed_to_start(node: dict[str, Any]) -> bool:
    return _semantic(node) in {"washer", "washing_machine", "dishwasher", "microwave"} and bool(
        node.get("requires_closed_to_start", True)
    )


def _controls_targets(state: dict[str, Any], control_id: str) -> list[str]:
    targets = []
    for edge in state.get("control_edges", []):
        if str(edge.get("relation") or "").lower() != "controls":
            continue
        if str(edge.get("source_id") or "") == control_id:
            targets.append(str(edge.get("target_id") or ""))
    return [target for target in targets if target]


def _device_door_failures(state: dict[str, Any], device_ids: list[str]) -> list[str]:
    failures = []
    for node_id, parent_id in state.get("parent_of", {}).items():
        if parent_id not in device_ids:
            continue
        node = _node(state, node_id)
        if str(node.get("door_kind") or "").lower() != "device":
            continue
        if bool(node.get("requires_closed_to_start", True)) and _is_open(node):
            failures.append(f"device door must be closed before start: {node_id}")
    return failures


def _container_access_failure(state: dict[str, Any], container_id: str) -> str | None:
    container = _node(state, container_id)
    if not container:
        return None
    semantic = _semantic(container)
    if not bool(container.get("blocks_containment")) and semantic not in {
        "fridge",
        "refrigerator",
        "microwave",
        "washer",
        "washing_machine",
        "dishwasher",
        "cabinet",
        "drawer",
    }:
        return None
    if not _is_open(container):
        return f"container is closed: {container_id}"
    return None


def _move_failures(state: dict[str, Any], agent_id: str, target_id: str) -> list[str]:
    failures = []
    target = _node(state, target_id)
    current_room = _room_of(state, agent_id)
    target_type = _node_type(target)
    if target_type == "room":
        if target_id == current_room:
            return [f"agent already in room: {target_id}"]
        adjacent = False
        for edge in state.get("room_edges", []):
            source = str(edge.get("source_id") or "")
            target = str(edge.get("target_id") or "")
            if {source, target} == {current_room, target_id}:
                adjacent = True
                break
        if not adjacent:
            failures.append(f"target room is not adjacent: {current_room}->{target_id}")
            return failures
        for node in state.get("nodes", {}).values():
            if str(node.get("door_kind") or "") != "structural":
                continue
            connected = {str(room_id) for room_id in node.get("connected_rooms") or []}
            if {current_room, target_id}.issubset(connected) and not _is_open(node):
                failures.append(f"room path is blocked by closed door: {current_room}->{target_id}")
                break
        return failures
    if target_type not in {"fixed_object", "control_object"}:
        failures.append("move target should be a room, fixed object, or control object")
    elif not _same_room(state, agent_id, target_id):
        failures.append("target is not in the same room")
    return failures


def validate_action(state: dict[str, Any], action: dict[str, Any]) -> ValidationResult:
    failures: list[str] = []
    action_name = str(action.get("action") or "").lower()
    agent_id = str(action.get("agent") or "robot_01")
    target_id = str(action.get("target") or "")
    object_id = str(action.get("object") or target_id)

    if not action_name:
        return ValidationResult(False, ("missing action",))
    try:
        action_type = ActionType(action_name)
    except ValueError:
        return ValidationResult(False, (f"unsupported action: {action_name}",))

    agent = _node(state, agent_id)
    if not agent:
        failures.append(f"unknown agent: {agent_id}")

    if action_type in {ActionType.MOVE, ActionType.OPEN, ActionType.CLOSE, ActionType.PRESS, ActionType.BRUSH, ActionType.PLACE, ActionType.FOLD}:
        if not target_id or not _node(state, target_id):
            failures.append(f"unknown target: {target_id}")

    if action_type == ActionType.PICK and (not object_id or not _node(state, object_id)):
        failures.append(f"unknown object: {object_id}")

    if failures:
        return ValidationResult(False, tuple(failures))

    if action_type == ActionType.MOVE:
        failures.extend(_move_failures(state, agent_id, target_id))

    elif action_type == ActionType.PICK:
        obj = _node(state, object_id)
        if _node_type(obj) not in MOVABLE_NODE_TYPES:
            failures.append("target is not movable")
        if _agent_holding(state, agent_id):
            failures.append("agent already holds an object")
        if not _same_room(state, agent_id, object_id):
            failures.append("object is not in the same room")
        parent_id = str(state.get("parent_of", {}).get(object_id) or "")
        if parent_id:
            failure = _container_access_failure(state, parent_id)
            if failure:
                failures.append(failure)

    elif action_type == ActionType.PLACE:
        held = str(action.get("object") or _agent_holding(state, agent_id))
        if not held:
            failures.append("agent holds nothing")
        elif state.get("parent_of", {}).get(held) != agent_id:
            failures.append(f"agent is not holding {held}")
        target = _node(state, target_id)
        if _node_type(target) not in PLACE_TARGET_TYPES:
            failures.append("place target should be a room, fixed object, or control object")
        if not _same_room(state, agent_id, target_id):
            failures.append("place target is not in the same room")
        failure = _container_access_failure(state, target_id)
        if failure:
            failures.append(failure)

    elif action_type in {ActionType.OPEN, ActionType.CLOSE, ActionType.PRESS, ActionType.BRUSH, ActionType.FOLD}:
        if not _same_room(state, agent_id, target_id):
            failures.append("target is not in the same room")
        target = _node(state, target_id)
        actions = {str(item).lower() for item in target.get("interactive_actions") or []}
        if action_type.value not in actions:
            failures.append(f"target does not support {action_type.value}: {target_id}")
        if action_type == ActionType.PRESS:
            if _requires_closed_to_start(target) and _is_open(target):
                failures.append(f"device door must be closed before start: {target_id}")
            failures.extend(_device_door_failures(state, [target_id, *_controls_targets(state, target_id)]))
        if action_type == ActionType.FOLD:
            if _semantic(target) not in {"clothes", "towel", "blanket"}:
                failures.append("target is not foldable cloth")
            if bool(_states(target).get("is_wet", False)):
                failures.append("wet cloth cannot be folded")

    return ValidationResult(not failures, tuple(failures))


__all__ = ["ValidationResult", "validate_action"]
