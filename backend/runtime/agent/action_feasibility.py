from __future__ import annotations

from dataclasses import dataclass

from backend.core.actions import ActionType
from ..schema.home_schema import canonical_node_type, canonical_semantic_type


PRESSABLE_KEYWORDS = {"button", "switch", "panel", "keypad", "faucet"}
SCANNABLE_KEYWORDS = {"label", "barcode", "scanner", "screen", "display"}
RECEPTACLE_KEYWORDS = {"bin", "trash", "basket", "rack", "drawer", "fridge", "washer", "dishwasher"}
BRUSHABLE_KEYWORDS = {"sink", "counter", "toilet", "floor", "wall", "mirror", "curtain", "dispenser", "table", "desk"}


@dataclass(frozen=True)
class ActionFeasibility:
    allowed: bool
    reason: str


def _node_text(node: dict) -> str:
    return " ".join(
        str(node.get(key) or "")
        for key in ("id", "name", "name_cn", "semantic_type", "object_type")
    ).lower()


def _affordance_set(node: dict) -> set[str]:
    actions = {str(item).lower() for item in node.get("interactive_actions") or []}
    semantic = canonical_semantic_type(node)
    if semantic in RECEPTACLE_KEYWORDS:
        actions.add("container")
    return actions


def _is_movable(node: dict) -> bool:
    return canonical_node_type(node) in {"movable_object", "agent"}


def _is_container_like(node: dict) -> bool:
    text = _node_text(node)
    affordances = _affordance_set(node)
    return "container" in affordances or any(keyword in text for keyword in RECEPTACLE_KEYWORDS)


def _is_pressable(node: dict) -> bool:
    text = _node_text(node)
    affordances = _affordance_set(node)
    return "toggleable" in affordances or "controls_water" in affordances or any(keyword in text for keyword in PRESSABLE_KEYWORDS)


def _is_openable(node: dict) -> bool:
    affordances = _affordance_set(node)
    return bool({"openable", "closeable", "movable", "open"} & affordances)


def _is_closable(node: dict) -> bool:
    affordances = _affordance_set(node)
    return bool({"openable", "closeable", "movable", "toggleable", "close"} & affordances)


def _is_scannable(node: dict) -> bool:
    text = _node_text(node)
    affordances = _affordance_set(node)
    return "writeable" in affordances or any(keyword in text for keyword in SCANNABLE_KEYWORDS)


def _is_brushable(node: dict) -> bool:
    text = _node_text(node)
    affordances = _affordance_set(node)
    return bool({"brushable", "cleanable", "surface"} & affordances) or any(keyword in text for keyword in BRUSHABLE_KEYWORDS)


def _agent_holding(state: dict, agent_id: str) -> list[str]:
    held = []
    for node_id, parent_id in state.get("parent_of", {}).items():
        node = state.get("nodes", {}).get(node_id) or {}
        relation = ((node.get("runtime") or {}).get("relation")) or ""
        if parent_id == agent_id and relation == "held_by":
            held.append(node_id)
    return held


def is_action_feasible(state: dict, action_type: ActionType | str, agent_id: str, target_id: str) -> ActionFeasibility:
    action = ActionType(action_type)
    nodes = state.get("nodes", {})
    agent = nodes.get(agent_id)
    target = nodes.get(target_id)
    if not agent:
      return ActionFeasibility(False, f"Unknown agent: {agent_id}")
    if not target:
      return ActionFeasibility(False, f"Unknown target: {target_id}")

    if action == ActionType.PICK:
        if not _is_movable(target):
            return ActionFeasibility(False, "Target is not movable.")
        if _agent_holding(state, agent_id):
            return ActionFeasibility(False, "Agent is already holding an object.")
        return ActionFeasibility(True, "Movable object can be picked.")

    if action == ActionType.PLACE:
        if not _agent_holding(state, agent_id):
            return ActionFeasibility(False, "Agent is not holding any object.")
        if _is_movable(target):
            return ActionFeasibility(False, "Place target should be a room or fixture, not another movable.")
        return ActionFeasibility(True, "Held object can be placed on the target.")

    if action == ActionType.MOVE:
        target_type = canonical_node_type(target)
        if target_type not in {"room", "fixed_object"}:
            return ActionFeasibility(False, "Move target should be a room or fixture.")
        return ActionFeasibility(True, "Agent can move to the target.")

    if action == ActionType.SCAN:
        return ActionFeasibility(True, "Scanning is always allowed.")

    if action == ActionType.PRESS:
        return ActionFeasibility(_is_pressable(target), "Target is pressable." if _is_pressable(target) else "Target is not pressable.")

    if action == ActionType.OPEN:
        return ActionFeasibility(_is_openable(target), "Target is openable." if _is_openable(target) else "Target is not openable.")

    if action == ActionType.CLOSE:
        return ActionFeasibility(_is_closable(target), "Target is closable." if _is_closable(target) else "Target is not closable.")

    if action == ActionType.BRUSH:
        return ActionFeasibility(_is_brushable(target), "Target is brushable." if _is_brushable(target) else "Target is not brushable.")

    return ActionFeasibility(False, f"Unsupported action: {action}")


def available_actions_for_node(state: dict, agent_id: str, target_id: str) -> list[ActionType]:
    available: list[ActionType] = []
    for action in ActionType:
        if is_action_feasible(state, action, agent_id, target_id).allowed:
            available.append(action)
    return available
