from __future__ import annotations

import copy
from typing import Any

from backend.core.actions import ActionType
from ..engine.events import log_event, move_item, set_node_state
from ..engine.state import build_runtime_state, connected_rooms_for_door_node, is_room_door_node
from ..schema.home_schema import canonical_node_type, canonical_semantic_type, normalize_home_scene, set_scene_graph


RUNTIME_RELATIONS = {"in", "on", "held_by", "worn_by", "at", "near"}
CONTAINER_HINTS = {"container", "drawer", "fridge", "cabinet", "washer", "dishwasher", "bin", "basket", "box"}
SUPPORT_HINTS = {"support_surface", "placeable_on", "surface", "counter", "table", "desk", "shelf", "bed", "chair"}
BRUSH_TOOLS = {"toilet_brush", "brush", "cloth", "broom", "mop", "scrub_brush"}
DIRECT_DROP_TARGETS = {"trash_bin", "bin", "basket"}


def _ensure_scene_agent_stub(scene: dict, agent_id: str) -> None:
    scene.setdefault("agent", {})
    scene["agent"].setdefault("id", agent_id)
    if scene["agent"].get("current_room"):
        scene["agent"].setdefault("current_anchor", scene["agent"].get("current_room"))
        scene["agent"].setdefault("inventory", [])
        return
    first_room = next(
        (str(node.get("id")) for node in scene.get("nodes", []) if canonical_node_type(node) == "room"),
        "",
    )
    if first_room:
        scene["agent"]["current_room"] = first_room
        scene["agent"]["current_anchor"] = first_room
    scene["agent"].setdefault("inventory", [])


def _ensure_robot_agent_node(state: dict, raw_scene: dict, agent_id: str) -> None:
    if agent_id in state["nodes"]:
        return

    raw_agent = copy.deepcopy((raw_scene.get("agent") or {}))
    current_room = str(raw_agent.get("current_room") or "")
    current_anchor = str(raw_agent.get("current_anchor") or current_room or "")
    inventory = list(raw_agent.get("inventory") or [])
    parent_id = current_anchor if current_anchor in state["nodes"] else current_room
    relation = "at" if parent_id == current_room else "near"
    node = {
        "id": agent_id,
        "name": str(raw_agent.get("name") or "Robot"),
        "name_cn": str(raw_agent.get("name_cn") or "机器人"),
        "node_type": "agent",
        "semantic_type": "robot",
        "mobility": "agent",
        "property": {"appearance": "", "physical": "", "operation": ""},
        "affordance_count": 0,
        "parent": parent_id or None,
        "child": [],
        "interactive_actions": [],
        "states": copy.deepcopy(raw_agent.get("state") or {}),
        "runtime": {"relation": relation if parent_id else "near"},
    }
    node["states"].setdefault("holding", inventory[0] if inventory else None)
    node["states"].setdefault("handempty", not inventory)
    state["nodes"][agent_id] = node
    if parent_id:
        state["parent_of"][agent_id] = parent_id
    if current_room:
        state["room_of"][agent_id] = current_room


def _node_text(node: dict) -> str:
    return " ".join(
        str(node.get(key) or "")
        for key in ("id", "name", "name_cn", "semantic_type", "object_type", "node_type")
    ).lower()


def _affordances(node: dict) -> set[str]:
    return {str(item).lower() for item in (node.get("interactive_actions") or [])}


def _normalize_action_name(action_name: str) -> str:
    return str(action_name or "").strip().lower()


def _node_states(node: dict) -> dict:
    return node.setdefault("states", {})


def _room_of(state: dict, node_id: str) -> str:
    return str(state.get("room_of", {}).get(node_id) or "")


def _agent_holding(state: dict, agent_id: str) -> list[str]:
    held = []
    for node_id, parent_id in state.get("parent_of", {}).items():
        node = state.get("nodes", {}).get(node_id) or {}
        relation = str(((node.get("runtime") or {}).get("relation")) or "")
        if parent_id == agent_id and relation == "held_by":
            held.append(node_id)
    return held


def _holding_item(state: dict, agent_id: str) -> str | None:
    held = _agent_holding(state, agent_id)
    return held[0] if held else None


def _is_room(node: dict) -> bool:
    return canonical_node_type(node) == "room"


def _is_container_like(node: dict) -> bool:
    text = _node_text(node)
    semantic = canonical_semantic_type(node)
    return semantic in CONTAINER_HINTS or any(h in text for h in CONTAINER_HINTS)


def _is_support_like(node: dict) -> bool:
    text = _node_text(node)
    semantic = canonical_semantic_type(node)
    return semantic in SUPPORT_HINTS or any(h in text for h in SUPPORT_HINTS)


def _is_open(node: dict) -> bool:
    states = node.get("states") or {}
    if "isOpen" in states:
        return bool(states["isOpen"])
    if "is_open" in states:
        return bool(states["is_open"])
    return False


def _is_same_room(state: dict, a: str, b: str) -> bool:
    node_a = state.get("nodes", {}).get(a) or {}
    node_b = state.get("nodes", {}).get(b) or {}
    room_a = _room_of(state, a)
    room_b = _room_of(state, b)
    if is_room_door_node(node_a) and room_b:
        return room_b in connected_rooms_for_door_node(node_a)
    if is_room_door_node(node_b) and room_a:
        return room_a in connected_rooms_for_door_node(node_b)
    return bool(room_a) and room_a == room_b


def _agent_anchor(state: dict, agent_id: str) -> str:
    return str(state.get("parent_of", {}).get(agent_id) or _room_of(state, agent_id) or "")


def _is_at_interaction_target(state: dict, agent_id: str, target_id: str) -> bool:
    return bool(target_id and _agent_anchor(state, agent_id) == target_id)


def _open_room_doors_in_room(state: dict, room_id: str) -> list[str]:
    door_ids: list[str] = []
    for node_id, node in state.get("nodes", {}).items():
        if canonical_semantic_type(node) != "door":
            continue
        if is_room_door_node(node):
            if room_id in connected_rooms_for_door_node(node) and _is_open(node):
                door_ids.append(node_id)
            continue
        if _room_of(state, node_id) != room_id:
            continue
        parent_id = str(state.get("parent_of", {}).get(node_id) or "")
        parent = state.get("nodes", {}).get(parent_id) or {}
        if _is_room(parent) and _is_open(node):
            door_ids.append(node_id)
    return sorted(set(door_ids))


def _held_brush_tool(state: dict, agent_id: str, target_id: str) -> str | None:
    target = state["nodes"].get(target_id) or {}
    target_semantic = canonical_semantic_type(target)
    allowed = {"toilet_brush", "brush", "cloth", "broom", "mop", "scrub_brush"}
    if target_semantic == "toilet":
        allowed = {"toilet_brush", "brush", "scrub_brush"}
    for node_id in _agent_holding(state, agent_id):
        node = state["nodes"].get(node_id) or {}
        if canonical_semantic_type(node) in allowed:
            return node_id
    return None


def _set_bool_state(node: dict, canonical: str, value: bool) -> None:
    states = _node_states(node)
    key_map = {
        "is_open": "is_open",
        "is_on": "is_on",
        "is_pressed": "is_pressed",
        "dirty": "is_dirty",
        "has_particles": "has_particles",
        "scanned": "scanned",
        "brushed": "brushed",
        "pushed": "pushed",
        "pulled": "pulled",
    }
    states[key_map.get(canonical, canonical)] = value


def _set_agent_holding(state: dict, agent_id: str, object_id: str | None) -> None:
    agent = state["nodes"].get(agent_id)
    if not agent:
        return
    set_node_state(state, agent_id, holding=object_id, handempty=object_id is None)


def _target_snapshot(state: dict, node_id: str) -> dict[str, Any] | None:
    node = state["nodes"].get(node_id)
    if not node:
        return None
    outgoing_controls = []
    for edge in state.get("control_edges", []):
        if str(edge.get("source_id") or "") == node_id:
            outgoing_controls.append(str(edge.get("target_id") or ""))
    return {
        "id": node_id,
        "name": node.get("name"),
        "type": node.get("node_type"),
        "object_type": node.get("semantic_type"),
        "room_id": _room_of(state, node_id),
        "parent_id": state.get("parent_of", {}).get(node_id),
        "relation": ((node.get("runtime") or {}).get("relation")) or "",
        "affordances": list(node.get("interactive_actions") or []),
        "states": copy.deepcopy(node.get("states") or {}),
        "controls": outgoing_controls,
    }


def _scan_observation(state: dict, target_id: str) -> dict[str, Any]:
    target = _target_snapshot(state, target_id)
    if target is None:
        return {"target": None}

    room_id = target["room_id"]
    local_neighbors = []
    for node_id, node in state["nodes"].items():
        if node_id == target_id:
            continue
        if _room_of(state, node_id) == room_id:
            local_neighbors.append(
                {
                    "id": node_id,
                    "name": node.get("name"),
                    "type": node.get("node_type"),
                    "object_type": node.get("semantic_type"),
                    "relation": ((node.get("runtime") or {}).get("relation")) or "",
                }
            )
    return {
        "target": target,
        "local_neighbors": local_neighbors[:24],
    }


def _state_diff(before: dict, after: dict) -> dict[str, Any]:
    changes = {
        "parent_changes": [],
        "room_changes": [],
        "state_changes": [],
    }

    node_ids = sorted(set(before["nodes"]) | set(after["nodes"]))
    for node_id in node_ids:
        before_parent = before.get("parent_of", {}).get(node_id)
        after_parent = after.get("parent_of", {}).get(node_id)
        if before_parent != after_parent:
            changes["parent_changes"].append(
                {"node_id": node_id, "before": before_parent, "after": after_parent}
            )

        before_room = before.get("room_of", {}).get(node_id)
        after_room = after.get("room_of", {}).get(node_id)
        if before_room != after_room:
            changes["room_changes"].append(
                {"node_id": node_id, "before": before_room, "after": after_room}
            )

        before_states = (before["nodes"].get(node_id) or {}).get("states") or {}
        after_states = (after["nodes"].get(node_id) or {}).get("states") or {}
        state_keys = sorted(set(before_states) | set(after_states))
        for key in state_keys:
            if before_states.get(key) != after_states.get(key):
                changes["state_changes"].append(
                    {
                        "node_id": node_id,
                        "state": key,
                        "before": before_states.get(key),
                        "after": after_states.get(key),
                    }
                )

    return changes


def _validate_runtime_invariants(state: dict, agent_id: str) -> list[str]:
    failed = []
    held = _agent_holding(state, agent_id)
    agent = state["nodes"].get(agent_id) or {}
    agent_states = agent.get("states") or {}
    if len(held) > 1:
        failed.append(f"{agent_id} holds multiple objects: {held}")
    if held and bool(agent_states.get("handempty")):
        failed.append(f"{agent_id} is handempty but holding {held[0]}")
    if not held and agent_states.get("holding") not in {None, ""}:
        failed.append(f"{agent_id} holding state is stale: {agent_states.get('holding')}")
    for obj_id in held:
        for other_id, parent_id in state.get("parent_of", {}).items():
            if other_id == obj_id:
                continue
            if parent_id == obj_id:
                continue
        if state.get("parent_of", {}).get(obj_id) != agent_id:
            failed.append(f"{obj_id} holding edge is inconsistent")
    return failed


def _require(condition: bool, message: str, failed: list[str]) -> None:
    if not condition:
        failed.append(message)


def _has_affordance(state: dict, node_id: str, action_name: str) -> bool:
    node = state["nodes"].get(node_id) or {}
    affordances = _affordances(node)
    normalized = _normalize_action_name(action_name)
    if normalized in affordances:
        return True
    if normalized == "open":
        return bool({"open", "close"} & affordances)
    if normalized == "close":
        return bool({"open", "close"} & affordances)
    return False


def _preconditions_for_pick(state: dict, agent_id: str, object_id: str) -> list[str]:
    failed: list[str] = []
    node = state["nodes"].get(object_id) or {}
    _require(bool(node), f"unknown object: {object_id}", failed)
    if failed:
        return failed
    _require(_has_affordance(state, object_id, "pick"), f"target does not support pick: {object_id}", failed)
    _require(not _agent_holding(state, agent_id), "agent already holding an object", failed)
    _require(_is_same_room(state, agent_id, object_id), "object not reachable in current room", failed)
    at_object = _is_at_interaction_target(state, agent_id, object_id)
    parent_id = str(state.get("parent_of", {}).get(object_id) or "")
    at_parent = bool(parent_id) and _is_at_interaction_target(state, agent_id, parent_id)
    _require(
        at_object or at_parent,
        f"agent must move next to target before pick: {object_id}",
        failed,
    )
    if parent_id:
        parent = state["nodes"].get(parent_id) or {}
        if _is_container_like(parent):
            _require(_is_open(parent), f"container {parent_id} is not open", failed)
    return failed


def _preconditions_for_place(state: dict, agent_id: str, object_id: str, target_id: str) -> list[str]:
    failed: list[str] = []
    target = state["nodes"].get(target_id) or {}
    _require(bool(target), f"unknown target: {target_id}", failed)
    _require(_holding_item(state, agent_id) == object_id, f"agent is not holding {object_id}", failed)
    _require(_is_same_room(state, agent_id, target_id), "target not reachable in current room", failed)
    _require(_is_at_interaction_target(state, agent_id, target_id), f"agent must move next to target before place: {target_id}", failed)
    _require(_has_affordance(state, target_id, "place"), f"target does not support place: {target_id}", failed)
    if target and _is_container_like(target) and canonical_semantic_type(target) not in DIRECT_DROP_TARGETS:
        _require(_is_open(target), f"container {target_id} is not open", failed)
    return failed


def _preconditions_for_move(state: dict, agent_id: str, target_id: str) -> list[str]:
    failed: list[str] = []
    target = state["nodes"].get(target_id) or {}
    _require(bool(target), f"unknown target: {target_id}", failed)
    if failed:
        return failed
    _require(_has_affordance(state, target_id, "move"), f"target does not support move: {target_id}", failed)
    _require(canonical_semantic_type(target) != "floor", "move target should not be a floor node", failed)
    current_room = _room_of(state, agent_id)
    if _is_room(target):
        if current_room == target_id:
            failed.append(f"agent already in room: {target_id}")
            return failed
        adjacent = False
        for edge in state.get("structural_edges", []):
            if str(edge.get("relation") or "").lower() != "adjacent_to":
                continue
            source = str(edge.get("source_id") or "")
            dest = str(edge.get("target_id") or "")
            if {source, dest} == {current_room, target_id}:
                adjacent = True
                break
        _require(adjacent, f"room not reachable from current room: {target_id}", failed)
        open_doors = _open_room_doors_in_room(state, current_room)
        _require(bool(open_doors), f"room door must be open before moving to room: {target_id}", failed)
        _require(
            _agent_anchor(state, agent_id) in open_doors,
            f"agent must move to an open room door before entering room: {target_id}",
            failed,
        )
    else:
        _require(_is_same_room(state, agent_id, target_id), "target not reachable in current room", failed)
        if _agent_anchor(state, agent_id) == target_id:
            failed.append(f"agent already next to target: {target_id}")
    return failed


def _preconditions_for_same_room_target(state: dict, agent_id: str, target_id: str, action_name: str) -> list[str]:
    failed: list[str] = []
    target = state["nodes"].get(target_id) or {}
    _require(bool(target), f"unknown target: {target_id}", failed)
    if target:
        _require(_has_affordance(state, target_id, action_name), f"target does not support {action_name}: {target_id}", failed)
        _require(_is_same_room(state, agent_id, target_id), "target not reachable in current room", failed)
        _require(
            _is_at_interaction_target(state, agent_id, target_id),
            f"agent must move next to target before {action_name}: {target_id}",
            failed,
        )
        normalized_action = _normalize_action_name(action_name)
        if normalized_action == "brush":
            _require(
                bool(_held_brush_tool(state, agent_id, target_id)),
                f"brush requires holding a cleaning tool for target: {target_id}",
                failed,
            )
    return failed


def _preconditions_for_scan(state: dict, agent_id: str, target_id: str) -> list[str]:
    failed: list[str] = []
    target = state["nodes"].get(target_id) or {}
    _require(bool(target), f"unknown target: {target_id}", failed)
    if not target:
        return failed
    _require(_has_affordance(state, target_id, "scan"), f"target does not support scan: {target_id}", failed)
    if _is_same_room(state, agent_id, target_id):
        return failed
    current_room = _room_of(state, agent_id)
    if _is_room(target):
        adjacent = any(
            str(edge.get("relation") or "").lower() == "adjacent_to"
            and {str(edge.get("source_id") or ""), str(edge.get("target_id") or "")} == {current_room, target_id}
            for edge in state.get("structural_edges", [])
        )
        _require(adjacent, "scan target room is not visible from current room", failed)
        open_door_in_current_room = any(
            canonical_semantic_type(node) == "door"
            and (
                (is_room_door_node(node) and current_room in connected_rooms_for_door_node(node))
                or (_room_of(state, node_id) == current_room)
            )
            and _is_open(node)
            for node_id, node in state.get("nodes", {}).items()
        )
        _require(open_door_in_current_room, "scan target room requires an open door from current room", failed)
        return failed
    failed.append("target not reachable in current room")
    return failed


def _toggle_controlled_targets(state: dict, control_id: str) -> list[str]:
    changed: list[str] = []
    for edge in state.get("control_edges", []):
        relation = str(edge.get("relation") or "").lower()
        source = str(edge.get("source_id") or "")
        target_id = str(edge.get("target_id") or "")
        if relation != "controls" or source != control_id or target_id not in state["nodes"]:
            continue
        target = state["nodes"][target_id]
        target_states = target.get("states") or {}
        if "is_on" in target_states or "isOn" in target_states:
            current = bool(target_states.get("is_on", target_states.get("isOn", False)))
            _set_bool_state(target, "is_on", not current)
            changed.append(target_id)
        elif "is_open" in target_states or "isOpen" in target_states:
            current = bool(target_states.get("is_open", target_states.get("isOpen", False)))
            _set_bool_state(target, "is_open", not current)
            changed.append(target_id)
        else:
            set_node_state(state, target_id, activated=True)
            changed.append(target_id)
    return changed


def _apply_move(state: dict, agent_id: str, target_id: str) -> None:
    target = state["nodes"][target_id]
    if _is_room(target):
        move_item(state, agent_id, target_id, "at")
    elif is_room_door_node(target):
        current_room = _room_of(state, agent_id)
        move_item(state, agent_id, target_id, "near")
        if current_room:
            state["room_of"][agent_id] = current_room
    else:
        move_item(state, agent_id, target_id, "near")


def _apply_pick(state: dict, agent_id: str, object_id: str) -> None:
    object_room = _room_of(state, object_id)
    if state.get("parent_of", {}).get(agent_id) == object_id and object_room:
        move_item(state, agent_id, object_room, "at")
    move_item(state, object_id, agent_id, "held_by")
    set_node_state(state, object_id, heldBy=agent_id, held_by=agent_id)
    _set_agent_holding(state, agent_id, object_id)


def _apply_place(state: dict, agent_id: str, object_id: str, target_id: str) -> str:
    target = state["nodes"][target_id]
    relation = "in" if _is_room(target) or _is_container_like(target) else "on"
    move_item(state, object_id, target_id, relation)
    if canonical_semantic_type(target) in DIRECT_DROP_TARGETS:
        target_states = target.setdefault("states", {})
        fill_level = min(1.0, round(float(target_states.get("fill_level", 0.0)) + 0.22, 2))
        target_states["fill_level"] = fill_level
        target_states["is_full"] = fill_level >= 0.75
    set_node_state(state, object_id, heldBy=None, held_by=None)
    _set_agent_holding(state, agent_id, None)
    return relation


def _apply_press(state: dict, target_id: str) -> list[str]:
    target = state["nodes"][target_id]
    _set_bool_state(target, "is_pressed", True)
    return _toggle_controlled_targets(state, target_id)


def _apply_scan(state: dict, target_id: str) -> None:
    target = state["nodes"][target_id]
    _set_bool_state(target, "scanned", True)


def _apply_open(state: dict, target_id: str) -> None:
    target = state["nodes"][target_id]
    _set_bool_state(target, "opened", True)
    if "is_open" in (target.get("states") or {}) or "isOpen" in (target.get("states") or {}):
        _set_bool_state(target, "is_open", True)
    parent_id = state.get("parent_of", {}).get(target_id)
    parent = state["nodes"].get(parent_id) if parent_id else None
    if canonical_semantic_type(target) == "door" and parent and _is_container_like(parent):
        _set_bool_state(parent, "is_open", True)


def _apply_close(state: dict, target_id: str) -> None:
    target = state["nodes"][target_id]
    _set_bool_state(target, "closed", True)
    if is_room_door_node(target):
        _set_bool_state(target, "is_open", False)
        return
    parent_id = state.get("parent_of", {}).get(target_id)
    parent = state["nodes"].get(parent_id) if parent_id else None
    if canonical_semantic_type(target) == "door" and parent and _is_room(parent):
        _set_bool_state(target, "is_open", True)
        return
    if "is_open" in (target.get("states") or {}) or "isOpen" in (target.get("states") or {}):
        _set_bool_state(target, "is_open", False)
    if canonical_semantic_type(target) == "door" and parent and _is_container_like(parent):
        _set_bool_state(parent, "is_open", False)


def _apply_brush(state: dict, target_id: str) -> None:
    target = state["nodes"][target_id]
    _set_bool_state(target, "brushed", True)
    if "dirty" in (target.get("states") or {}) or "is_dirty" in (target.get("states") or {}):
        _set_bool_state(target, "dirty", False)
    if "has_particles" in (target.get("states") or {}) or "hasParticles" in (target.get("states") or {}):
        _set_bool_state(target, "has_particles", False)


def _preconditions(state: dict, action_type: ActionType, agent_id: str, action: dict[str, Any]) -> list[str]:
    if action_type == ActionType.MOVE:
        return _preconditions_for_move(state, agent_id, str(action.get("target") or ""))
    if action_type == ActionType.PICK:
        return _preconditions_for_pick(state, agent_id, str(action.get("object") or action.get("target") or ""))
    if action_type == ActionType.PLACE:
        return _preconditions_for_place(
            state,
            agent_id,
            str(action.get("object") or ""),
            str(action.get("target") or ""),
        )
    if action_type == ActionType.SCAN:
        return _preconditions_for_scan(state, agent_id, str(action.get("target") or ""))
    if action_type in {ActionType.PRESS, ActionType.OPEN, ActionType.CLOSE, ActionType.BRUSH}:
        return _preconditions_for_same_room_target(
            state,
            agent_id,
            str(action.get("target") or ""),
            action_type.value,
        )
    return [f"unsupported action: {action_type.value}"]


def _apply_action(state: dict, action_type: ActionType, agent_id: str, action: dict[str, Any]) -> dict[str, Any]:
    target_id = str(action.get("target") or "")
    object_id = str(action.get("object") or "")
    detail = ""
    observation: dict[str, Any] = {}

    if action_type == ActionType.MOVE:
        _apply_move(state, agent_id, target_id)
        detail = f"{agent_id} moved to {target_id}"
    elif action_type == ActionType.PICK:
        object_id = object_id or target_id
        _apply_pick(state, agent_id, object_id)
        detail = f"{agent_id} picked {object_id}"
        target_id = object_id
    elif action_type == ActionType.PLACE:
        relation = _apply_place(state, agent_id, object_id, target_id)
        detail = f"{agent_id} placed {object_id} {relation} {target_id}"
    elif action_type == ActionType.PRESS:
        changed = _apply_press(state, target_id)
        detail = f"{agent_id} pressed {target_id}"
        if changed:
            detail += f" and affected {', '.join(changed)}"
    elif action_type == ActionType.SCAN:
        _apply_scan(state, target_id)
        detail = f"{agent_id} scanned {target_id}"
        observation = _scan_observation(state, target_id)
    elif action_type == ActionType.OPEN:
        _apply_open(state, target_id)
        detail = f"{agent_id} opened {target_id}"
    elif action_type == ActionType.CLOSE:
        _apply_close(state, target_id)
        detail = f"{agent_id} closed {target_id}"
    elif action_type == ActionType.BRUSH:
        _apply_brush(state, target_id)
        detail = f"{agent_id} brushed {target_id}"
    else:
        raise ValueError(f"unsupported action: {action_type.value}")

    return {"detail": detail, "observation": observation}


def _dynamic_edges_from_state(state: dict) -> list[dict[str, Any]]:
    edges = []
    nodes = state["nodes"]
    for node_id, parent_id in state["parent_of"].items():
        if parent_id == "outside_home" or node_id not in nodes or parent_id not in nodes:
            continue
        node = nodes[node_id]
        parent = nodes[parent_id]
        relation = str(((node.get("runtime") or {}).get("relation")) or "in")
        parent_type = canonical_node_type(parent)
        if parent_type == "room" and relation not in {"held_by", "worn_by", "at"}:
            relation = "in"

        if relation in {"near", "at"}:
            category = "spatial"
            edge_type = "spatial_edge"
        elif relation in {"inside_room", "part_of"}:
            category = "structural"
            edge_type = "structural_edge"
        else:
            category = "containment"
            edge_type = "containment_edge"

        edges.append(
            {
                "source_id": parent_id,
                "target_id": node_id,
                "edge_type": edge_type,
                "relation": relation,
                "category": category,
                "properties": {"runtime": True},
            }
        )
    return edges


def _state_to_scene(raw_scene: dict, state: dict, agent_id: str) -> dict[str, Any]:
    updated = copy.deepcopy(raw_scene)
    set_scene_graph(
        updated,
        list(state["nodes"].values()),
        state["structural_edges"] + state["control_edges"] + _dynamic_edges_from_state(state),
    )
    agent_node = state["nodes"].get(agent_id) or {}
    updated["agent"] = {
        "id": agent_id,
        "name": agent_node.get("name", agent_id),
        "type": "agent",
        "properties": copy.deepcopy(agent_node.get("property") or {}),
        "current_room": _room_of(state, agent_id),
        "current_anchor": state.get("parent_of", {}).get(agent_id),
        "inventory": _agent_holding(state, agent_id),
        "state": copy.deepcopy(agent_node.get("states") or {}),
    }
    updated.setdefault("world_state", {})
    updated["world_state"]["event_log"] = copy.deepcopy(state.get("logs") or [])
    return updated


def execute_robot_action(raw_scene: dict, action: dict[str, Any], runtime_state: dict | None = None) -> dict[str, Any]:
    scene = normalize_home_scene(copy.deepcopy(raw_scene))
    agent_id = str(action.get("agent") or (scene.get("agent") or {}).get("id") or "robot_01")
    _ensure_scene_agent_stub(scene, agent_id)
    state = copy.deepcopy(runtime_state) if runtime_state is not None else build_runtime_state(scene)

    _ensure_robot_agent_node(state, scene, agent_id)
    before = copy.deepcopy(state)

    action_raw = _normalize_action_name(str(action.get("action") or action.get("action_type") or "").lower())
    try:
        action_type = ActionType(action_raw)
    except ValueError:
        return {
            "ok": False,
            "failed_preconds": [f"unsupported action: {action_raw}"],
            "state_diff": {"parent_changes": [], "room_changes": [], "state_changes": []},
            "observation": {
                "agent_id": agent_id,
                "current_room": _room_of(state, agent_id),
                "holding": _holding_item(state, agent_id),
            },
            "event_log": copy.deepcopy(state.get("logs") or []),
            "runtime_state": state,
            "scene": _state_to_scene(scene, state, agent_id),
        }
    failed = _preconditions(state, action_type, agent_id, action)
    if failed:
        return {
            "ok": False,
            "failed_preconds": failed,
            "state_diff": {"parent_changes": [], "room_changes": [], "state_changes": []},
            "observation": {
                "agent_id": agent_id,
                "current_room": _room_of(state, agent_id),
                "holding": _holding_item(state, agent_id),
            },
            "event_log": copy.deepcopy(state.get("logs") or []),
            "runtime_state": state,
            "scene": _state_to_scene(scene, state, agent_id),
        }

    payload = _apply_action(state, action_type, agent_id, action)
    step = int((scene.get("world_state") or {}).get("step") or 0)
    log_event(state, step, action_type.value, payload["detail"])

    invariant_errors = _validate_runtime_invariants(state, agent_id)
    if invariant_errors:
        return {
            "ok": False,
            "failed_preconds": invariant_errors,
            "state_diff": {"parent_changes": [], "room_changes": [], "state_changes": []},
            "observation": payload.get("observation") or {},
            "event_log": copy.deepcopy(before.get("logs") or []),
            "runtime_state": before,
            "scene": _state_to_scene(scene, before, agent_id),
        }

    observation = payload.get("observation") or {}
    observation.setdefault("agent_id", agent_id)
    observation.setdefault("current_room", _room_of(state, agent_id))
    observation.setdefault("current_anchor", _agent_anchor(state, agent_id))
    observation.setdefault("holding", _holding_item(state, agent_id))
    if "target" not in observation and action.get("target"):
        observation["target"] = _target_snapshot(state, str(action.get("target")))

    return {
        "ok": True,
        "failed_preconds": [],
        "state_diff": _state_diff(before, state),
        "observation": observation,
        "event_log": copy.deepcopy(state.get("logs") or []),
        "runtime_state": state,
        "scene": _state_to_scene(scene, state, agent_id),
    }


def validate_robot_action(raw_scene: dict, action: dict[str, Any], runtime_state: dict | None = None) -> dict[str, Any]:
    scene = normalize_home_scene(copy.deepcopy(raw_scene))
    agent_id = str(action.get("agent") or (scene.get("agent") or {}).get("id") or "robot_01")
    _ensure_scene_agent_stub(scene, agent_id)
    state = copy.deepcopy(runtime_state) if runtime_state is not None else build_runtime_state(scene)

    _ensure_robot_agent_node(state, scene, agent_id)

    action_raw = _normalize_action_name(str(action.get("action") or action.get("action_type") or "").lower())
    try:
        action_type = ActionType(action_raw)
    except ValueError:
        return {
            "ok": False,
            "failed_preconds": [f"unsupported action: {action_raw}"],
            "agent_id": agent_id,
        }

    failed = _preconditions(state, action_type, agent_id, action)
    return {
        "ok": not failed,
        "failed_preconds": failed,
        "agent_id": agent_id,
    }
