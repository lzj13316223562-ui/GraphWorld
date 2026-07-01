from __future__ import annotations

import copy
from typing import Any

from backend.runtime.scene_utils import node, room_of
from backend.runtime.agent.maintenance_goals import (
    HOSPITAL_CLEAN_SKILLS,
    HOSPITAL_RETURN_SKILLS,
    dispose_food_phase,
    empty_cup_phase,
    first_node_by_semantic,
    first_node_by_semantic_near,
    global_restore_goal,
    laundry_phase,
    visible_dispose_food_goal,
    visible_empty_cup_goal,
    visible_laundry_goal,
    visible_restore_goal,
)

def candidate_goal_options(
    scene: dict[str, Any],
    baseline: dict[str, Any],
    observation: dict[str, Any],
    robot_id: str,
    step: int,
    claimed_goal_nodes: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    claimed_goal_nodes = claimed_goal_nodes or set()
    goals: list[dict[str, Any] | None] = [
        global_restore_goal(scene, baseline, robot_id, step),
        visible_dispose_food_goal(observation, scene, step, robot_id, baseline),
        visible_empty_cup_goal(observation, scene, step),
        visible_laundry_goal(observation, scene, step),
        visible_restore_goal(observation, baseline, step),
    ]
    options: dict[str, dict[str, Any]] = {}
    for goal in goals:
        if not goal or goal_conflicts_with_claims(goal, claimed_goal_nodes):
            continue
        refreshed = refresh_active_goal_snapshot(goal, scene, robot_id)
        if not active_goal_ids_valid(refreshed, scene):
            continue
        task = str(refreshed.get("task") or "")
        if task and task not in options:
            options[task] = refreshed
    return options


def next_room_toward(scene: dict[str, Any], start_room: str, target_room: str) -> str:
    if not start_room or not target_room or start_room == target_room:
        return ""
    graph: dict[str, set[str]] = {}
    for edge in scene.get("edges") or []:
        relation = str(edge.get("relation") or "").lower()
        if relation not in {"connected", "connected_to", "next_to", "neighbour"}:
            continue
        source = str(edge.get("source_id") or "")
        target = str(edge.get("target_id") or "")
        if source and target:
            graph.setdefault(source, set()).add(target)
            graph.setdefault(target, set()).add(source)
    queue: list[tuple[str, list[str]]] = [(start_room, [start_room])]
    seen = {start_room}
    while queue:
        room_id, path = queue.pop(0)
        for neighbor in sorted(graph.get(room_id, ())):
            if neighbor in seen:
                continue
            next_path = [*path, neighbor]
            if neighbor == target_room:
                return next_path[1] if len(next_path) > 1 else ""
            seen.add(neighbor)
            queue.append((neighbor, next_path))
    return ""


def refresh_active_goal_snapshot(goal: dict[str, Any], scene: dict[str, Any], robot_id: str) -> dict[str, Any]:
    updated = copy.deepcopy(goal)
    object_id = str(updated.get("object") or "")
    object_node = node(scene, object_id) or {}
    robot_node = node(scene, robot_id) or {}
    target_id = str(updated.get("target") or "")
    skill = str(updated.get("skill") or "")
    destination_room_override = ""
    if str(updated.get("type") or "") == "skill" and skill == "dispose_food":
        trash_bin = str(updated.get("trash_bin") or first_node_by_semantic_near(scene, {"trash_bin"}, preferred_room=room_of(scene, object_id)))
        garbage_station = str(updated.get("garbage_station") or first_node_by_semantic(scene, {"garbage_station"}))
        updated["trash_bin"] = trash_bin
        updated["garbage_station"] = garbage_station
        updated["target"] = garbage_station
        trash_bin_home = str(updated.get("trash_bin_home") or (node(scene, trash_bin) or {}).get("parent") or "")
        updated["trash_bin_home"] = trash_bin_home
        updated["phase"] = dispose_food_phase(scene, object_id, trash_bin, robot_id, trash_bin_home)
        phase = str(updated.get("phase") or "")
        target_by_phase = {
            "collect_food": trash_bin,
            "take_bin": trash_bin,
            "dump_bin": garbage_station,
            "return_bin": trash_bin_home,
        }
        target_id = target_by_phase.get(phase, garbage_station)
        if phase == "collect_food":
            destination_room_override = room_of(scene, trash_bin) if str(object_node.get("parent") or "") == robot_id else room_of(scene, object_id)
        elif phase == "take_bin":
            destination_room_override = room_of(scene, trash_bin)
        elif phase == "dump_bin":
            destination_room_override = room_of(scene, garbage_station)
        elif phase == "return_bin":
            destination_room_override = room_of(scene, trash_bin_home)
    if str(updated.get("type") or "") == "skill" and skill == "empty_cup":
        sink = str(updated.get("sink") or first_node_by_semantic_near(scene, {"sink"}, preferred_room=room_of(scene, object_id)))
        updated["sink"] = sink
        updated["target"] = sink
        updated["phase"] = empty_cup_phase(scene, object_id)
        target_id = sink
        if str(object_node.get("parent") or "") == robot_id:
            destination_room_override = room_of(scene, sink)
    if str(updated.get("type") or "") == "skill" and skill == "laundry_clothes":
        washer = str(updated.get("washer") or first_node_by_semantic(scene, {"washer", "washing_machine"}))
        drying_rack = str(updated.get("drying_rack") or first_node_by_semantic(scene, {"drying_rack"}))
        wardrobe = str(updated.get("wardrobe") or first_node_by_semantic(scene, {"cabinet"}, room="bedroom") or first_node_by_semantic(scene, {"wardrobe"}, room="bedroom"))
        updated["washer"] = washer
        updated["washer_button"] = str(updated.get("washer_button") or f"{washer}_button")
        updated["drying_rack"] = drying_rack
        updated["wardrobe"] = wardrobe
        updated["target"] = wardrobe
        updated["phase"] = laundry_phase(scene, object_id, washer, wardrobe)
        target_by_phase = {
            "wash_load": washer,
            "start_washer": washer,
            "washing_wait": washer,
            "dry": drying_rack,
            "fold": object_id,
            "store": wardrobe,
        }
        target_id = target_by_phase.get(str(updated.get("phase") or ""), wardrobe)
    if str(updated.get("type") or "") == "skill" and skill in HOSPITAL_RETURN_SKILLS:
        target_id = str(updated.get("target") or "")
        updated["phase"] = "done" if object_node and str(object_node.get("parent") or "") == target_id else "return_item"
        if str(object_node.get("parent") or "") == robot_id:
            destination_room_override = room_of(scene, target_id)
    if str(updated.get("type") or "") == "skill" and skill in HOSPITAL_CLEAN_SKILLS:
        target_id = str(updated.get("target") or object_id)
        target_node = node(scene, target_id) or {}
        target_states = target_node.get("states") or {}
        updated["phase"] = (
            "clean_surface"
            if target_states.get("is_dirty") is True
            else "done"
        )
        destination_room_override = room_of(scene, target_id)
    updated["object_parent"] = str(object_node.get("parent") or "")
    updated["object_room"] = room_of(scene, object_id)
    updated["target_room"] = room_of(scene, target_id)
    updated["robot_parent"] = str(robot_node.get("parent") or "")
    updated["robot_room"] = room_of(scene, robot_id)
    destination_room = destination_room_override or (updated["target_room"] if updated["object_parent"] == robot_id else updated["object_room"])
    updated["next_room"] = next_room_toward(scene, updated["robot_room"], destination_room)
    return updated


def active_goal_ids_valid(goal: dict[str, Any] | None, scene: dict[str, Any]) -> bool:
    if not goal:
        return False
    node_ids = {str(item.get("id") or "") for item in scene.get("nodes") or [] if item.get("id")}
    fields = ("object", "target", "food_home", "trash_bin", "trash_bin_home", "garbage_station", "sink", "washer", "drying_rack", "wardrobe")
    return all(str(goal.get(field) or "") in node_ids for field in fields if goal.get(field))


def active_goal_completed(goal: dict[str, Any] | None, scene: dict[str, Any]) -> bool:
    if not goal:
        return False
    if not active_goal_ids_valid(goal, scene):
        return True
    object_node = node(scene, str(goal.get("object") or "")) or {}
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") == "laundry_clothes":
        states = object_node.get("states") or {}
        return bool(
            object_node
            and str(object_node.get("parent") or "") == str(goal.get("wardrobe") or goal.get("target") or "")
            and states.get("is_dirty") is False
            and states.get("is_wet") is False
            and states.get("folded") is True
        )
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") == "dispose_food":
        states = object_node.get("states") or {}
        trash_bin_node = node(scene, str(goal.get("trash_bin") or "")) or {}
        return bool(
            object_node
            and str(object_node.get("parent") or "") == str(goal.get("food_home") or "")
            and str(trash_bin_node.get("parent") or "") == str(goal.get("trash_bin_home") or "")
            and states.get("is_rotten") is False
            and states.get("is_burnt") is False
        )
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") == "empty_cup":
        states = object_node.get("states") or {}
        return bool(object_node and float(states.get("fill_level") or 0.0) <= 0.0 and states.get("is_full") is not True)
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") in HOSPITAL_RETURN_SKILLS:
        return bool(object_node and str(object_node.get("parent") or "") == str(goal.get("target") or ""))
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") in HOSPITAL_CLEAN_SKILLS:
        target_node = node(scene, str(goal.get("target") or goal.get("object") or "")) or {}
        states = target_node.get("states") or {}
        return bool(target_node and states.get("is_dirty") is not True)
    return bool(object_node and str(object_node.get("parent") or "") == str(goal.get("target") or ""))


def active_goal_claims(goal: dict[str, Any] | None) -> set[str]:
    if not goal:
        return set()
    claims = {str(goal.get("object") or "")}
    skill = str(goal.get("skill") or "")
    if skill == "dispose_food":
        claims.add(str(goal.get("trash_bin") or ""))
    if skill == "empty_cup":
        claims.add(str(goal.get("sink") or goal.get("target") or ""))
    if skill == "laundry_clothes":
        claims.add(str(goal.get("washer") or ""))
        claims.add(str(goal.get("drying_rack") or ""))
        claims.add(str(goal.get("wardrobe") or goal.get("target") or ""))
    if skill in HOSPITAL_RETURN_SKILLS | HOSPITAL_CLEAN_SKILLS:
        claims.add(str(goal.get("target") or ""))
    if str(goal.get("type") or "") == "restore_initial_position":
        claims.add(str(goal.get("target") or ""))
    return {claim for claim in claims if claim}


def goal_conflicts_with_claims(goal: dict[str, Any] | None, claimed: set[str]) -> bool:
    if not goal:
        return False
    return bool(active_goal_claims(goal) & claimed)


def update_active_goal(
    goal: dict[str, Any] | None,
    scene: dict[str, Any],
    robot_id: str,
    action: dict[str, Any],
    action_result: dict[str, Any],
    step: int,
    *,
    max_stale_steps: int = 12,
) -> dict[str, Any] | None:
    if not goal:
        return None
    if active_goal_completed(goal, scene):
        return None
    before_object_parent = str(goal.get("object_parent") or "")
    before_robot_parent = str(goal.get("robot_parent") or "")
    before_robot_room = str(goal.get("robot_room") or "")
    updated = refresh_active_goal_snapshot(goal, scene, robot_id)
    if not active_goal_ids_valid(updated, scene):
        return None
    meaningful_action = str(action.get("action") or "") in {"pick", "place", "brush", "dump", "fold", "press"}
    action_ok = bool(action_result.get("ok", action.get("legal", True)))
    progressed = (
        str(updated.get("object_parent") or "") != before_object_parent
        or str(updated.get("robot_parent") or "") != before_robot_parent
        or str(updated.get("robot_room") or "") != before_robot_room
        or (action_ok and meaningful_action)
    )
    if progressed:
        updated["last_progress_step"] = step
        updated["steps_without_progress"] = 0
    else:
        updated["steps_without_progress"] = int(updated.get("steps_without_progress") or 0) + 1
    if int(updated.get("steps_without_progress") or 0) >= max_stale_steps:
        return None
    return updated
