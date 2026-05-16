from __future__ import annotations

from typing import Any

from .domain_rules import APPLIANCE_CYCLE_STEPS, CLOTH_SEMANTICS, DUMP_RULES, SURFACE_SEMANTICS
from .predicates import (
    children_of,
    controlled_targets,
    holding,
    is_container_door,
    mutable_states,
    node,
    node_type,
    parent_of,
    semantic,
)
from .states import DiscreteState


def move_node(state: dict[str, Any], node_id: str, parent_id: str, relation: str) -> None:
    item = node(state, node_id)
    if not item:
        return
    item["parent"] = parent_id
    item["runtime_relation"] = relation
    state.setdefault("parent_of", {})[node_id] = parent_id
    state.setdefault("relation_of", {})[node_id] = relation
    parent = node(state, parent_id)
    state.setdefault("room_of", {})[node_id] = parent_id if node_type(parent) == "room" else str(state.get("room_of", {}).get(parent_id) or "")


def open_target(state: dict[str, Any], target_id: str) -> None:
    target = node(state, target_id)
    target_states = mutable_states(target)
    target_states[DiscreteState.IS_OPEN.value] = True
    parent = node(state, parent_of(state, target_id))
    if parent and (str(target.get("door_kind") or "").lower() == "device" or is_container_door(state, target_id)):
        mutable_states(parent)[DiscreteState.IS_OPEN.value] = True
    for child_id, child_parent in state.get("parent_of", {}).items():
        if child_parent != target_id:
            continue
        child = node(state, child_id)
        if str(child.get("door_kind") or "") == "device":
            mutable_states(child)[DiscreteState.IS_OPEN.value] = True


def close_target(state: dict[str, Any], target_id: str) -> None:
    target = node(state, target_id)
    target_states = mutable_states(target)
    target_states[DiscreteState.IS_OPEN.value] = False
    parent = node(state, parent_of(state, target_id))
    if parent and (str(target.get("door_kind") or "").lower() == "device" or is_container_door(state, target_id)):
        mutable_states(parent)[DiscreteState.IS_OPEN.value] = False
    for child_id, child_parent in state.get("parent_of", {}).items():
        if child_parent != target_id:
            continue
        child = node(state, child_id)
        if str(child.get("door_kind") or "") == "device":
            mutable_states(child)[DiscreteState.IS_OPEN.value] = False


def press_target(state: dict[str, Any], target_id: str) -> None:
    target = node(state, target_id)
    target_states = mutable_states(target)
    target_states[DiscreteState.IS_PRESSED.value] = True
    target_semantic = semantic(target)
    if target_semantic in APPLIANCE_CYCLE_STEPS:
        target_states[DiscreteState.IS_ON.value] = True
        target_states[DiscreteState.CYCLE_REMAINING.value] = APPLIANCE_CYCLE_STEPS[target_semantic]
    for controlled_id in controlled_targets(state, target_id):
        controlled = node(state, controlled_id)
        controlled_states = mutable_states(controlled)
        controlled_semantic = semantic(controlled)
        duration = APPLIANCE_CYCLE_STEPS.get(controlled_semantic)
        if duration:
            controlled_states[DiscreteState.IS_ON.value] = True
            controlled_states[DiscreteState.CYCLE_REMAINING.value] = duration
        elif DiscreteState.IS_ON.value in controlled_states:
            controlled_states[DiscreteState.IS_ON.value] = not bool(controlled_states.get(DiscreteState.IS_ON.value, False))
    if target_semantic not in APPLIANCE_CYCLE_STEPS and DiscreteState.IS_ON.value in target_states:
        target_states[DiscreteState.IS_ON.value] = not bool(target_states.get(DiscreteState.IS_ON.value, False))


def brush_target(state: dict[str, Any], target_id: str) -> None:
    target = node(state, target_id)
    if semantic(target) in CLOTH_SEMANTICS:
        return
    target_states = mutable_states(target)
    target_states[DiscreteState.IS_DIRTY.value] = False
    if semantic(target) in {"sink", "trash_bin", "bin", "basket", "container"}:
        if DiscreteState.FILL_LEVEL.value in target_states:
            target_states[DiscreteState.FILL_LEVEL.value] = 0.0
        if DiscreteState.IS_FULL.value in target_states:
            target_states[DiscreteState.IS_FULL.value] = False


def fold_target(state: dict[str, Any], target_id: str) -> None:
    mutable_states(node(state, target_id))[DiscreteState.FOLDED.value] = True


def place_relation_for_target(target: dict[str, Any]) -> str:
    return "on" if semantic(target) in SURFACE_SEMANTICS else "in"


def dump_held_container(state: dict[str, Any], actor_id: str, target_id: str) -> None:
    held_id = holding(state, actor_id)
    held = node(state, held_id)
    rule = DUMP_RULES.get(semantic(held))
    if not rule:
        return
    if rule.effect == "empty_trash_bin":
        for child_id in list(children_of(state, held_id)):
            child = node(state, child_id)
            child_states = mutable_states(child)
            child_states["is_rotten"] = False
            child_states["is_burnt"] = False
            if semantic(child) == "food":
                fridge_id = next(
                    (
                        node_id
                        for node_id, item in state.get("nodes", {}).items()
                        if semantic(item) in {"refrigerator", "fridge"}
                    ),
                    "",
                )
                move_node(state, child_id, fridge_id or target_id, "in")
            else:
                move_node(state, child_id, target_id, "in")
        mutable_states(held)[DiscreteState.IS_DIRTY.value] = False
    elif rule.effect == "empty_fill_level":
        held_states = mutable_states(held)
        held_states[DiscreteState.FILL_LEVEL.value] = 0.0
        held_states[DiscreteState.IS_FULL.value] = False


__all__ = [
    "brush_target",
    "close_target",
    "dump_held_container",
    "fold_target",
    "move_node",
    "open_target",
    "place_relation_for_target",
    "press_target",
]
