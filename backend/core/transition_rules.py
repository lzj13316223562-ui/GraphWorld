from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict

from .actions import ActionType
from .states import DiscreteState


Condition = Callable[[Dict[str, Any]], bool]
Effect = Callable[[Dict[str, Any]], None]


APPLIANCE_CYCLE_STEPS: dict[str, int] = {
    "washer": 3,
    "washing_machine": 3,
    "dishwasher": 3,
    "microwave": 2,
    "coffee_machine": 2,
    "coffee_maker": 2,
}

DRYING_RACK_STEPS = 3


@dataclass(frozen=True)
class RuleContext:
    state: dict[str, Any]
    actor_id: str
    target_id: str
    object_id: str = ""
    step: int = 0

    @property
    def target(self) -> dict[str, Any]:
        return self.state.get("nodes", {}).get(self.target_id) or {}

    @property
    def target_states(self) -> dict[str, Any]:
        return self.target.setdefault("states", {})


@dataclass(frozen=True)
class TransitionRule:
    name: str
    action: ActionType
    preconditions: tuple[Callable[[RuleContext], str | None], ...] = ()
    effects: tuple[Callable[[RuleContext], None], ...] = ()
    description: str = ""

    def failures(self, ctx: RuleContext) -> list[str]:
        return [failure for check in self.preconditions if (failure := check(ctx))]

    def apply(self, ctx: RuleContext) -> list[str]:
        failures = self.failures(ctx)
        if failures:
            return failures
        for effect in self.effects:
            effect(ctx)
        return []


@dataclass(frozen=True)
class StateInfluence:
    state_name: DiscreteState
    owner_semantic_types: frozenset[str]
    affects: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class TransitionScoringRule:
    trigger: str
    positive_changes: tuple[str, ...]
    negative_changes: tuple[str, ...]
    relation_preferences: tuple[str, ...]
    description: str


def _semantic(node: dict[str, Any]) -> str:
    return str(node.get("semantic_type") or node.get("object_type") or "").strip().lower()


def _node(state: dict[str, Any], node_id: str) -> dict[str, Any]:
    return state.get("nodes", {}).get(node_id) or {}


def _states(node: dict[str, Any]) -> dict[str, Any]:
    return node.setdefault("states", {})


def _parent_of(state: dict[str, Any], node_id: str) -> str:
    return str(state.get("parent_of", {}).get(node_id) or _node(state, node_id).get("parent") or "")


def _is_open(node: dict[str, Any]) -> bool:
    return bool((node.get("states") or {}).get(DiscreteState.IS_OPEN.value, False))


def _same_room(state: dict[str, Any], a: str, b: str) -> bool:
    room_of = state.get("room_of", {})
    actor_room = str(room_of.get(a) or "")
    if actor_room and actor_room == str(room_of.get(b) or ""):
        return True
    target = _node(state, b)
    connected_rooms = {str(room_id) for room_id in target.get("connected_rooms") or []}
    return bool(actor_room and actor_room in connected_rooms)


def _controlled_targets(state: dict[str, Any], control_id: str) -> list[str]:
    targets: list[str] = []
    for edge in state.get("control_edges", []):
        if str(edge.get("relation") or "").lower() != "controls":
            continue
        if str(edge.get("source_id") or "") == control_id:
            target_id = str(edge.get("target_id") or "")
            if target_id and target_id in state.get("nodes", {}):
                targets.append(target_id)
    return targets


def require_target_exists(ctx: RuleContext) -> str | None:
    return None if ctx.target else f"unknown target: {ctx.target_id}"


def require_same_room(ctx: RuleContext) -> str | None:
    if ctx.actor_id == ctx.target_id:
        return None
    return None if _same_room(ctx.state, ctx.actor_id, ctx.target_id) else "target is not in the same room"


def require_container_open_for_pick(ctx: RuleContext) -> str | None:
    parent = _node(ctx.state, _parent_of(ctx.state, ctx.object_id or ctx.target_id))
    parent_semantic = _semantic(parent)
    if bool(parent.get("blocks_containment")) or parent_semantic in {"fridge", "refrigerator", "microwave", "washer", "washing_machine", "dishwasher", "cabinet", "drawer"}:
        return None if _is_open(parent) else f"container is closed: {_parent_of(ctx.state, ctx.object_id or ctx.target_id)}"
    return None


def require_container_open_for_place(ctx: RuleContext) -> str | None:
    target_semantic = _semantic(ctx.target)
    if bool(ctx.target.get("blocks_containment")) or target_semantic in {"fridge", "refrigerator", "microwave", "washer", "washing_machine", "dishwasher", "cabinet", "drawer"}:
        return None if _is_open(ctx.target) else f"container is closed: {ctx.target_id}"
    return None


def require_device_doors_closed_for_press(ctx: RuleContext) -> str | None:
    if _semantic(ctx.target) in APPLIANCE_CYCLE_STEPS and bool(ctx.target.get("requires_closed_to_start", True)) and _is_open(ctx.target):
        return f"device door must be closed before start: {ctx.target_id}"
    target_ids = [ctx.target_id, *_controlled_targets(ctx.state, ctx.target_id)]
    parent_of = ctx.state.get("parent_of", {})
    for node_id, parent_id in parent_of.items():
        if parent_id not in target_ids:
            continue
        node = _node(ctx.state, node_id)
        if str(node.get("door_kind") or "").lower() != "device":
            continue
        if bool(node.get("requires_closed_to_start", True)) and _is_open(node):
            return f"device door must be closed before start: {node_id}"
    return None


def effect_open(ctx: RuleContext) -> None:
    ctx.target_states[DiscreteState.IS_OPEN.value] = True
    parent_id = _parent_of(ctx.state, ctx.target_id)
    parent = _node(ctx.state, parent_id)
    if str(ctx.target.get("door_kind") or "") == "device" and parent:
        _states(parent)[DiscreteState.IS_OPEN.value] = True
    for node_id, node_parent_id in ctx.state.get("parent_of", {}).items():
        if node_parent_id != ctx.target_id:
            continue
        node = _node(ctx.state, node_id)
        if str(node.get("door_kind") or "") == "device":
            _states(node)[DiscreteState.IS_OPEN.value] = True


def effect_close(ctx: RuleContext) -> None:
    ctx.target_states[DiscreteState.IS_OPEN.value] = False
    parent_id = _parent_of(ctx.state, ctx.target_id)
    parent = _node(ctx.state, parent_id)
    if str(ctx.target.get("door_kind") or "") == "device" and parent:
        _states(parent)[DiscreteState.IS_OPEN.value] = False
    for node_id, node_parent_id in ctx.state.get("parent_of", {}).items():
        if node_parent_id != ctx.target_id:
            continue
        node = _node(ctx.state, node_id)
        if str(node.get("door_kind") or "") == "device":
            _states(node)[DiscreteState.IS_OPEN.value] = False


def effect_press(ctx: RuleContext) -> None:
    ctx.target_states[DiscreteState.IS_PRESSED.value] = True
    target_semantic = _semantic(ctx.target)
    if target_semantic in APPLIANCE_CYCLE_STEPS:
        ctx.target_states[DiscreteState.IS_ON.value] = True
        ctx.target_states["cycle_remaining"] = APPLIANCE_CYCLE_STEPS[target_semantic]
    controlled_targets = _controlled_targets(ctx.state, ctx.target_id)
    for target_id in controlled_targets:
        controlled = _node(ctx.state, target_id)
        states = _states(controlled)
        semantic = _semantic(controlled)
        duration = APPLIANCE_CYCLE_STEPS.get(semantic)
        if duration:
            states[DiscreteState.IS_ON.value] = True
            states["cycle_remaining"] = duration
        elif DiscreteState.IS_ON.value in states:
            states[DiscreteState.IS_ON.value] = not bool(states.get(DiscreteState.IS_ON.value, False))
    if target_semantic not in APPLIANCE_CYCLE_STEPS and DiscreteState.IS_ON.value in ctx.target_states:
        ctx.target_states[DiscreteState.IS_ON.value] = not bool(ctx.target_states.get(DiscreteState.IS_ON.value, False))


def effect_brush(ctx: RuleContext) -> None:
    ctx.target_states[DiscreteState.IS_DIRTY.value] = False
    if "is_clean" in ctx.target_states:
        ctx.target_states["is_clean"] = True
    semantic = _semantic(ctx.target)
    if semantic in {"sink", "trash_bin", "bin", "basket", "container"}:
        if DiscreteState.FILL_LEVEL.value in ctx.target_states:
            ctx.target_states[DiscreteState.FILL_LEVEL.value] = 0.0
        if DiscreteState.IS_FULL.value in ctx.target_states:
            ctx.target_states[DiscreteState.IS_FULL.value] = False
    if semantic in {"shoes", "shoe"}:
        ctx.target_states["scattered"] = False
    ctx.target_states.pop("misplaced_near", None)


def require_foldable_and_dry(ctx: RuleContext) -> str | None:
    if _semantic(ctx.target) not in {"clothes", "towel", "blanket"}:
        return "target is not foldable cloth"
    if bool(ctx.target_states.get(DiscreteState.IS_WET.value, False)):
        return "wet cloth cannot be folded"
    return None


def effect_fold(ctx: RuleContext) -> None:
    ctx.target_states[DiscreteState.FOLDED.value] = True


ACTION_TRANSITION_RULES: dict[ActionType, TransitionRule] = {
    ActionType.OPEN: TransitionRule(
        name="open_target",
        action=ActionType.OPEN,
        preconditions=(require_target_exists, require_same_room),
        effects=(effect_open,),
        description="Open room doors, device doors, elevator doors, drawers, and cabinets.",
    ),
    ActionType.CLOSE: TransitionRule(
        name="close_target",
        action=ActionType.CLOSE,
        preconditions=(require_target_exists, require_same_room),
        effects=(effect_close,),
        description="Close an openable control object or container door.",
    ),
    ActionType.PRESS: TransitionRule(
        name="press_control",
        action=ActionType.PRESS,
        preconditions=(require_target_exists, require_same_room, require_device_doors_closed_for_press),
        effects=(effect_press,),
        description="Press a button-like control and propagate its effect to controlled devices.",
    ),
    ActionType.BRUSH: TransitionRule(
        name="brush_clean",
        action=ActionType.BRUSH,
        preconditions=(require_target_exists, require_same_room),
        effects=(effect_brush,),
        description="Clean a brushable target.",
    ),
    ActionType.FOLD: TransitionRule(
        name="fold_cloth",
        action=ActionType.FOLD,
        preconditions=(require_target_exists, require_same_room, require_foldable_and_dry),
        effects=(effect_fold,),
        description="Fold dry clothes, towels, or blankets.",
    ),
}


STATE_INFLUENCES: tuple[StateInfluence, ...] = (
    StateInfluence(
        state_name=DiscreteState.IS_OPEN,
        owner_semantic_types=frozenset({"door"}),
        affects=("visibility", "navigation"),
        description="A closed structural door blocks one-step movement and direct visibility into the next room.",
    ),
    StateInfluence(
        state_name=DiscreteState.IS_OPEN,
        owner_semantic_types=frozenset({"door"}),
        affects=("containment_access", "visibility", "start_mutex"),
        description="A device door blocks picking from, placing into, and seeing inside the device; it must be closed before the device starts.",
    ),
    StateInfluence(
        state_name=DiscreteState.IS_PRESSED,
        owner_semantic_types=frozenset({"button", "switch"}),
        affects=("controlled_target_state",),
        description="A pressed control can start or toggle devices connected by controls edges.",
    ),
    StateInfluence(
        state_name=DiscreteState.IS_ON,
        owner_semantic_types=frozenset({"washer", "washing_machine", "dishwasher", "microwave", "coffee_machine", "coffee_maker"}),
        affects=("delayed_cycle_completion",),
        description="Running devices count down cycle_remaining and apply completion effects when the cycle ends.",
    ),
)


TRANSITION_SCORING_RULES: tuple[TransitionScoringRule, ...] = (
    TransitionScoringRule(
        trigger="human_wears_or_uses_clothes",
        positive_changes=(),
        negative_changes=("clothes.is_dirty false->true", "clothes.folded true->false"),
        relation_preferences=("dirty clothes should move toward washer",),
        description="Human use can legitimately make clothes dirty; this is environmental load, not robot improvement.",
    ),
    TransitionScoringRule(
        trigger="washer_cycle_complete",
        positive_changes=("clothes.is_dirty true->false",),
        negative_changes=("clothes.is_wet false->true", "clothes.folded true->false"),
        relation_preferences=("wet clothes should leave washer and move to drying_rack",),
        description="Washing cleans clothes but creates a wet follow-up obligation.",
    ),
    TransitionScoringRule(
        trigger="timed_drying_on_rack",
        positive_changes=("clothes.is_wet true->false",),
        negative_changes=(),
        relation_preferences=("dry clothes should be folded and stored in wardrobe",),
        description="Drying rack resolves wetness over time when wet cloth is placed on it.",
    ),
    TransitionScoringRule(
        trigger="fold",
        positive_changes=("clothes.folded false->true",),
        negative_changes=(),
        relation_preferences=("folded clothes should be in wardrobe",),
        description="Folding improves order after clothes are dry.",
    ),
    TransitionScoringRule(
        trigger="store_in_wardrobe",
        positive_changes=(),
        negative_changes=(),
        relation_preferences=("folded clean dry clothes in wardrobe is preferred",),
        description="Correct final relation improves relation/order score even when states do not change.",
    ),
)


def apply_action_transition(
    state: dict[str, Any],
    action: ActionType | str,
    actor_id: str,
    target_id: str,
    *,
    object_id: str = "",
    step: int = 0,
) -> list[str]:
    action_type = ActionType(action)
    rule = ACTION_TRANSITION_RULES.get(action_type)
    if not rule:
        return []
    return rule.apply(RuleContext(state=state, actor_id=actor_id, target_id=target_id, object_id=object_id, step=step))


def apply_timed_transitions(state: dict[str, Any], step: int = 0) -> list[str]:
    completed: list[str] = []
    parent_of = state.get("parent_of", {})
    for node_id, node in state.get("nodes", {}).items():
        semantic = _semantic(node)
        states = _states(node)
        if bool(states.get(DiscreteState.IS_PRESSED.value, False)):
            states[DiscreteState.IS_PRESSED.value] = False
        parent = _node(state, str(parent_of.get(node_id) or ""))
        if _semantic(parent) == "drying_rack" and bool(states.get(DiscreteState.IS_WET.value, False)):
            remaining = int(states.get("dry_remaining") or DRYING_RACK_STEPS)
            remaining = max(0, remaining - 1)
            states["dry_remaining"] = remaining
            if remaining == 0:
                states[DiscreteState.IS_WET.value] = False
                completed.append(node_id)
        if semantic not in APPLIANCE_CYCLE_STEPS:
            continue
        if not bool(states.get(DiscreteState.IS_ON.value, False)):
            continue
        remaining = int(states.get("cycle_remaining") or APPLIANCE_CYCLE_STEPS[semantic])
        remaining = max(0, remaining - 1)
        states["cycle_remaining"] = remaining
        if remaining > 0:
            continue
        states[DiscreteState.IS_ON.value] = False
        for child_id, parent_id in parent_of.items():
            if parent_id != node_id:
                continue
            child = _node(state, child_id)
            child_states = _states(child)
            if semantic in {"washer", "washing_machine"} and _semantic(child) in {"clothes", "towel", "blanket"}:
                child_states[DiscreteState.IS_DIRTY.value] = False
                child_states[DiscreteState.IS_WET.value] = True
                child_states[DiscreteState.FOLDED.value] = False
                child_states["dry_remaining"] = DRYING_RACK_STEPS
            if semantic == "dishwasher" and _semantic(child) in {"bowl", "plate", "cup", "dish", "utensil"}:
                child_states[DiscreteState.IS_DIRTY.value] = False
                if "is_clean" in child_states:
                    child_states["is_clean"] = True
                if DiscreteState.IS_WET.value in child_states:
                    child_states[DiscreteState.IS_WET.value] = False
        completed.append(node_id)
    return completed


__all__ = [
    "ACTION_TRANSITION_RULES",
    "APPLIANCE_CYCLE_STEPS",
    "DRYING_RACK_STEPS",
    "STATE_INFLUENCES",
    "TRANSITION_SCORING_RULES",
    "RuleContext",
    "StateInfluence",
    "TransitionRule",
    "TransitionScoringRule",
    "apply_action_transition",
    "apply_timed_transitions",
]
