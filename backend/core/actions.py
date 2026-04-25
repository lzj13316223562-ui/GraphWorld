from __future__ import annotations

from enum import Enum
from dataclasses import dataclass
from typing import Dict


class ActionType(str, Enum):
    MOVE = "move"
    PICK = "pick"
    PLACE = "place"
    PRESS = "press"
    SCAN = "scan"
    OPEN = "open"
    CLOSE = "close"
    BRUSH = "brush"

    # Deferred actions kept out of the current runtime on purpose:
    # TOGGLE, GRASP, RELEASE, PLACE_ON, PLACE_IN,
    # MOVE_TO_ROOM, MOVE_TO_FLOOR, APPROACH_OBJECT, COOK

@dataclass(frozen=True)
class ActionSpec:
    action_type: ActionType
    category: str
    params: tuple[str, ...]
    description: str
    mutates_edges: bool
    mutates_states: bool
    effect_summary: tuple[str, ...]



ACTION_SPECS: Dict[ActionType, ActionSpec] = {
    ActionType.PICK: ActionSpec(
        action_type=ActionType.PICK,
        category="manipulation",
        params=("agent", "object"),
        description="Detach a movable object from its current parent and attach it to the agent.",
        mutates_edges=True,
        mutates_states=True,
        effect_summary=("remove(object -> parent)", "add(object -> agent, held_by)"),
    ),
    ActionType.PLACE: ActionSpec(
        action_type=ActionType.PLACE,
        category="manipulation",
        params=("agent", "object", "target"),
        description="Detach a held object from the agent and place it on or in a target node.",
        mutates_edges=True,
        mutates_states=True,
        effect_summary=("remove(object -> agent, held_by)", "add(object -> target, in/on)"),
    ),
    ActionType.MOVE: ActionSpec(
        action_type=ActionType.MOVE,
        category="navigation",
        params=("agent", "target"),
        description="Move the agent to a room or fixture node.",
        mutates_edges=True,
        mutates_states=True,
        effect_summary=("remove(agent -> current_parent)", "add(agent -> target, at/in)"),
    ),
    ActionType.SCAN: ActionSpec(
        action_type=ActionType.SCAN,
        category="observation",
        params=("agent", "target"),
        description="Observe a node and read its current states, relations, and local neighborhood.",
        mutates_edges=False,
        mutates_states=False,
        effect_summary=("return(target.states, target.relations, target.affordances)",),
    ),
    ActionType.PRESS: ActionSpec(
        action_type=ActionType.PRESS,
        category="manipulation",
        params=("agent", "target"),
        description="Press a control-like node such as a button, switch, or faucet.",
        mutates_edges=False,
        mutates_states=True,
        effect_summary=("toggle/control target state", "possibly propagate to controlled object"),
    ),
    ActionType.OPEN: ActionSpec(
        action_type=ActionType.OPEN,
        category="manipulation",
        params=("agent", "target"),
        description="Open an openable node such as a door, drawer, cabinet, or appliance door.",
        mutates_edges=False,
        mutates_states=True,
        effect_summary=("set is_open = True when applicable", "or set opened = True"),
    ),
    ActionType.CLOSE: ActionSpec(
        action_type=ActionType.CLOSE,
        category="manipulation",
        params=("agent", "target"),
        description="Close a closeable node such as a door, drawer, cabinet, or appliance door.",
        mutates_edges=False,
        mutates_states=True,
        effect_summary=("set is_open = False when applicable", "or set closed = True"),
    ),
    ActionType.BRUSH: ActionSpec(
        action_type=ActionType.BRUSH,
        category="manipulation",
        params=("agent", "target"),
        description="Brush or scrub a reachable surface/object to change its surface condition.",
        mutates_edges=False,
        mutates_states=True,
        effect_summary=("set brushed = True", "possibly reduce dirty/particles on target surface"),
    ),
    #折叠
}


def action_spec(action_type: ActionType | str) -> ActionSpec:
    normalized = ActionType(action_type)
    return ACTION_SPECS[normalized]
