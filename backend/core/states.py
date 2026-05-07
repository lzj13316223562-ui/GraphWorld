from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DiscreteState(str, Enum):
    """The discrete state space used by the static core and matrix evaluator."""

    CYCLE_REMAINING = "cycle_remaining"
    FILL_LEVEL = "fill_level"
    FOLDED = "folded"
    IS_BLOCKED = "is_blocked"
    IS_BROKEN = "is_broken"
    IS_BURNT = "is_burnt"
    IS_COOKED = "is_cooked"
    IS_DIRTY = "is_dirty"
    IS_FROZEN = "is_frozen"
    IS_FULL = "is_full"
    IS_ON = "is_on"
    IS_OPEN = "is_open"
    IS_PRESSED = "is_pressed"
    IS_ROTTEN = "is_rotten"
    IS_WET = "is_wet"
    IS_WILTED = "is_wilted"
    TEMPERATURE = "temperature"
    VITALITY = "vitality"


DISCRETE_STATE_SPACE: tuple[str, ...] = tuple(state.value for state in DiscreteState)


TEMPERATURE_VALUES = frozenset({"cold", "room", "warm", "hot"})
NUMERIC_STATES = frozenset(
    {
        DiscreteState.CYCLE_REMAINING.value,
        DiscreteState.FILL_LEVEL.value,
        DiscreteState.VITALITY.value,
    }
)


@dataclass(frozen=True)
class StateSpec:
    name: str
    value_type: str
    applies_to: tuple[str, ...]
    positive_value: object
    worsened_by: tuple[str, ...]
    improved_by: tuple[str, ...]
    downstream_effects: tuple[str, ...]
    score_weight: float = 1.0


def is_discrete_state(name: str) -> bool:
    return str(name or "") in DISCRETE_STATE_SPACE


def normalize_discrete_value(name: str, value: object) -> int | str | None:
    if name == DiscreteState.TEMPERATURE.value:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        return normalized if normalized in TEMPERATURE_VALUES else normalized
    if name in NUMERIC_STATES:
        if value is None:
            return None
        try:
            return round(float(value), 4)
        except (TypeError, ValueError):
            return None
    if value is None:
        return None
    return 1 if bool(value) else 0


STATE_SPECS: dict[str, StateSpec] = {
    DiscreteState.IS_OPEN.value: StateSpec(
        name=DiscreteState.IS_OPEN.value,
        value_type="bool",
        applies_to=("door", "cabinet", "fridge", "drawer", "washer", "microwave"),
        positive_value=False,
        worsened_by=("left_open",),
        improved_by=("close",),
        downstream_effects=("enables containment access when true", "blocks device start when device door is open"),
        score_weight=0.6,
    ),
    DiscreteState.IS_ON.value: StateSpec(
        name=DiscreteState.IS_ON.value,
        value_type="bool",
        applies_to=("stove", "faucet", "washer", "dishwasher", "light", "tv", "microwave"),
        positive_value=False,
        worsened_by=("left_running",),
        improved_by=("press", "cycle_completion"),
        downstream_effects=("starts timed appliance transitions", "can create risk if left on"),
        score_weight=0.8,
    ),
    DiscreteState.IS_PRESSED.value: StateSpec(
        name=DiscreteState.IS_PRESSED.value,
        value_type="bool",
        applies_to=("button", "switch", "knob"),
        positive_value=False,
        worsened_by=("press",),
        improved_by=("cycle_completion",),
        downstream_effects=("propagates state to controlled devices"),
        score_weight=0.2,
    ),
    DiscreteState.CYCLE_REMAINING.value: StateSpec(
        name=DiscreteState.CYCLE_REMAINING.value,
        value_type="number",
        applies_to=("washer", "dishwasher", "microwave"),
        positive_value=0,
        worsened_by=("press_start",),
        improved_by=("timed_transition",),
        downstream_effects=("cycle completion mutates contents"),
        score_weight=0.2,
    ),
    DiscreteState.IS_DIRTY.value: StateSpec(
        name=DiscreteState.IS_DIRTY.value,
        value_type="bool",
        applies_to=("plate", "cup", "table", "clothes", "floor", "toilet", "sink"),
        positive_value=False,
        worsened_by=("use", "eat", "spill", "wear"),
        improved_by=("brush", "cycle_completion"),
        downstream_effects=("blocks clean-clothes human events", "lowers environment state score"),
        score_weight=1.0,
    ),
    DiscreteState.IS_ROTTEN.value: StateSpec(
        name=DiscreteState.IS_ROTTEN.value,
        value_type="bool",
        applies_to=("food", "trash", "organic_item"),
        positive_value=False,
        worsened_by=("time_decay",),
        improved_by=(),
        downstream_effects=("should be moved to trash or removed from living space"),
        score_weight=1.0,
    ),
    DiscreteState.IS_FULL.value: StateSpec(
        name=DiscreteState.IS_FULL.value,
        value_type="bool",
        applies_to=("trash_bin", "basket", "cup", "container"),
        positive_value=False,
        worsened_by=("place", "human_event"),
        improved_by=(),
        downstream_effects=("blocks disposal or filling when true"),
        score_weight=0.7,
    ),
    DiscreteState.FILL_LEVEL.value: StateSpec(
        name=DiscreteState.FILL_LEVEL.value,
        value_type="number",
        applies_to=("trash_bin", "cup", "container"),
        positive_value=0,
        worsened_by=("place", "human_event"),
        improved_by=(),
        downstream_effects=("sets is_full when threshold reached"),
        score_weight=0.5,
    ),
    DiscreteState.IS_WET.value: StateSpec(
        name=DiscreteState.IS_WET.value,
        value_type="bool",
        applies_to=("clothes", "towel", "floor", "cup", "sink_area"),
        positive_value=False,
        worsened_by=("human_event", "cycle_completion"),
        improved_by=("timed_transition",),
        downstream_effects=("blocks folding and wearing for clothes"),
        score_weight=0.8,
    ),
    DiscreteState.TEMPERATURE.value: StateSpec(
        name=DiscreteState.TEMPERATURE.value,
        value_type="enum",
        applies_to=("food",),
        positive_value="room",
        worsened_by=("timed_transition",),
        improved_by=("timed_transition",),
        downstream_effects=("enables cooked/frozen/burnt transitions"),
        score_weight=0.4,
    ),
    DiscreteState.IS_COOKED.value: StateSpec(
        name=DiscreteState.IS_COOKED.value,
        value_type="bool",
        applies_to=("food",),
        positive_value=True,
        worsened_by=("raw_food",),
        improved_by=("cycle_completion",),
        downstream_effects=("enables eating events"),
        score_weight=0.6,
    ),
    DiscreteState.IS_BURNT.value: StateSpec(
        name=DiscreteState.IS_BURNT.value,
        value_type="bool",
        applies_to=("food",),
        positive_value=False,
        worsened_by=("overcook",),
        improved_by=(),
        downstream_effects=("food should be disposed"),
        score_weight=1.0,
    ),
    DiscreteState.IS_FROZEN.value: StateSpec(
        name=DiscreteState.IS_FROZEN.value,
        value_type="bool",
        applies_to=("food",),
        positive_value=False,
        worsened_by=("freeze_when_not_desired",),
        improved_by=("timed_transition",),
        downstream_effects=("blocks immediate eating/cooking"),
        score_weight=0.5,
    ),
    DiscreteState.IS_BROKEN.value: StateSpec(
        name=DiscreteState.IS_BROKEN.value,
        value_type="bool",
        applies_to=("cup", "plate", "laptop", "device"),
        positive_value=False,
        worsened_by=("break",),
        improved_by=(),
        downstream_effects=("blocks normal use"),
        score_weight=1.0,
    ),
    DiscreteState.IS_BLOCKED.value: StateSpec(
        name=DiscreteState.IS_BLOCKED.value,
        value_type="bool",
        applies_to=("door", "path", "container"),
        positive_value=False,
        worsened_by=("obstruct",),
        improved_by=(),
        downstream_effects=("blocks navigation or containment access"),
        score_weight=1.0,
    ),
    DiscreteState.FOLDED.value: StateSpec(
        name=DiscreteState.FOLDED.value,
        value_type="bool",
        applies_to=("clothes", "towel", "blanket"),
        positive_value=True,
        worsened_by=("human_event", "cycle_completion"),
        improved_by=("fold"),
        downstream_effects=("improves storage/order relation score"),
        score_weight=0.6,
    ),
    DiscreteState.IS_WILTED.value: StateSpec(
        name=DiscreteState.IS_WILTED.value,
        value_type="bool",
        applies_to=("plant",),
        positive_value=False,
        worsened_by=("time_without_water",),
        improved_by=(),
        downstream_effects=("lowers plant vitality"),
        score_weight=0.6,
    ),
    DiscreteState.VITALITY.value: StateSpec(
        name=DiscreteState.VITALITY.value,
        value_type="number",
        applies_to=("plant",),
        positive_value=1,
        worsened_by=("time_without_water",),
        improved_by=(),
        downstream_effects=("sets is_wilted when too low"),
        score_weight=0.4,
    ),
}


__all__ = [
    "DISCRETE_STATE_SPACE",
    "DiscreteState",
    "NUMERIC_STATES",
    "STATE_SPECS",
    "StateSpec",
    "TEMPERATURE_VALUES",
    "is_discrete_state",
    "normalize_discrete_value",
]
