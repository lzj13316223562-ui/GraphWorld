from __future__ import annotations

from typing import Any

from .domain_rules import APPLIANCE_CYCLE_STEPS, CLOTH_SEMANTICS, DRYING_RACK_STEPS
from .predicates import mutable_states, node, parent_of, semantic
from .states import DiscreteState


def apply_timed_transitions(state: dict[str, Any], step: int = 0) -> list[str]:
    completed: list[str] = []
    parent_map = state.get("parent_of", {})
    for node_id, item in state.get("nodes", {}).items():
        item_semantic = semantic(item)
        item_states = mutable_states(item)
        if bool(item_states.get(DiscreteState.IS_PRESSED.value, False)):
            item_states[DiscreteState.IS_PRESSED.value] = False
        parent = node(state, str(parent_map.get(node_id) or ""))
        if semantic(parent) == "drying_rack" and bool(item_states.get(DiscreteState.IS_WET.value, False)):
            remaining = int(item_states.get(DiscreteState.CYCLE_REMAINING.value) or DRYING_RACK_STEPS)
            remaining = max(0, remaining - 1)
            item_states[DiscreteState.CYCLE_REMAINING.value] = remaining
            if remaining == 0:
                item_states[DiscreteState.IS_WET.value] = False
                completed.append(node_id)
        if item_semantic not in APPLIANCE_CYCLE_STEPS:
            continue
        if not bool(item_states.get(DiscreteState.IS_ON.value, False)):
            continue
        remaining = int(item_states.get(DiscreteState.CYCLE_REMAINING.value) or APPLIANCE_CYCLE_STEPS[item_semantic])
        remaining = max(0, remaining - 1)
        item_states[DiscreteState.CYCLE_REMAINING.value] = remaining
        if remaining > 0:
            continue
        item_states[DiscreteState.IS_ON.value] = False
        for child_id, child_parent in parent_map.items():
            if child_parent != node_id:
                continue
            child = node(state, child_id)
            child_states = mutable_states(child)
            child_semantic = semantic(child)
            if item_semantic in {"washer", "washing_machine"} and child_semantic in CLOTH_SEMANTICS:
                child_states[DiscreteState.IS_DIRTY.value] = False
                child_states[DiscreteState.IS_WET.value] = True
                child_states[DiscreteState.FOLDED.value] = False
                child_states[DiscreteState.CYCLE_REMAINING.value] = DRYING_RACK_STEPS
            if item_semantic == "dishwasher" and child_semantic in {"bowl", "plate", "cup", "dish", "utensil"}:
                child_states[DiscreteState.IS_DIRTY.value] = False
                if DiscreteState.IS_WET.value in child_states:
                    child_states[DiscreteState.IS_WET.value] = False
        completed.append(node_id)
    return completed


__all__ = ["apply_timed_transitions"]
