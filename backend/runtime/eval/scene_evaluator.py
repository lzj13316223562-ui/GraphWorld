from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass
from typing import Any

from ..engine.engine import _dynamic_edges
from ..engine.state import build_runtime_state, connected_rooms_for_door_node
from ..schema.home_schema import (
    canonical_node_type,
    canonical_semantic_class,
    canonical_semantic_type,
    normalize_home_scene,
    scene_edges,
    scene_nodes,
    set_scene_graph,
)
from ..world.environment import apply_environment_step, ensure_world_environment
from ..world.npc_runtime import apply_npc_routines
from ..world.rules import apply_runtime_rules
from .score_config import (
    FINAL_SCORE_WEIGHTS,
    HUMAN_SCORE_WEIGHTS,
    STATE_PENALTIES,
    STRUCTURE_PENALTIES,
    TREND_WINDOW_STEPS,
    WORLD_SCORE_WEIGHTS,
)


OPENABLE_TYPES = {"door", "window", "wardrobe", "drawer", "cabinet", "fridge", "microwave", "washer", "dishwasher"}
FOOD_TYPES = {"vegetable", "fruit", "yogurt", "drink", "milk", "juice", "raw_food", "cooked_food"}
DIRTY_STATE_TYPES = {"toilet", "bowl", "plate", "cup", "sink", "clothes", "shoes"}
RISK_ACTIVE_TYPES = {"stove", "faucet", "washer", "microwave", "dishwasher"}
LOW_RISK_HOURS = (8 * 60, 18 * 60)
HOSPITAL_PUBLIC_ROOMS = {"entrance", "lobby", "registration", "waiting_area", "triage", "corridor_main"}
HOSPITAL_SEMI_PRIVATE_ROOMS = {"staff_room", "treatment_room", "outpatient_clinic_1", "payment"}
HOSPITAL_SENSITIVE_ROOMS = {"pharmacy"}

STRUCTURE_ALLOWED_ROOMS: dict[str, set[str]] = {
    "shoes": {"entrance", "outside_home"},
    "clothes": {"bedroom", "bathroom"},
    "socks": {"bedroom", "bathroom"},
    "towel": {"bedroom", "bathroom"},
    "toothbrush": {"bathroom"},
    "cup": {"bathroom", "kitchen", "living_room"},
    "bowl": {"kitchen", "living_room", "dishwasher"},
    "plate": {"kitchen", "living_room", "dishwasher"},
}

STRUCTURE_ALLOWED_PARENTS: dict[str, set[str]] = {
    "shoes": {"shoe_rack_entrance", "human_resident", "outside_home", "living_room"},
    "clothes": {"wardrobe_bedroom", "human_resident", "bathroom", "washer_bathroom"},
    "bowl": {"dishwasher_kitchen", "coffee_table_living_room", "kitchen", "human_resident"},
    "cup": {"sink_bathroom", "faucet_bathroom", "coffee_table_living_room", "human_resident"},
    "toothbrush": {"sink_bathroom", "faucet_bathroom", "human_resident"},
    "refrigerated_medicine": {"medicine_fridge_pharmacy"},
    "syringe": {"treatment_room", "pharmacy", "medical_cart_treatment_room"},
}


@dataclass
class SceneContext:
    raw_scene: dict[str, Any]
    scene: dict[str, Any]
    scene_type: str
    nodes: dict[str, dict[str, Any]]
    edges: list[dict[str, Any]]
    room_of: dict[str, str]
    parent_of: dict[str, str]
    rooms: dict[str, dict[str, Any]]
    agents: dict[str, dict[str, Any]]
    current_structure_records: list[dict[str, Any]]
    current_state_records: list[dict[str, Any]]
    trend_snapshots: list[dict[str, Any]]


def _states(node: dict[str, Any]) -> dict[str, Any]:
    return node.get("states") or {}


def _scene_type(scene: dict[str, Any]) -> str:
    world = scene.get("world_state") or {}
    name = str(world.get("scene_name") or scene.get("scene_name") or "").lower()
    if "hospital" in name:
        return "hospital"
    return "home"


def _is_daytime_low_risk(scene: dict[str, Any]) -> bool:
    world = scene.get("world_state") or {}
    minute = int(world.get("time_min") or 0) % (24 * 60)
    start, end = LOW_RISK_HOURS
    return start <= minute < end


def _relation(node: dict[str, Any]) -> str:
    return str((node.get("runtime") or {}).get("relation") or "")


def _clip_score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _weighted_score(parts: dict[str, float], weights: dict[str, float]) -> float:
    total = 0.0
    for key, weight in weights.items():
        total += float(parts.get(key, 0.0)) * float(weight)
    return _clip_score(total)


def _temperature_comfort_score(temp_c: float) -> float:
    temp_c = float(temp_c)
    if 20.0 <= temp_c <= 26.0:
        return 1.0
    if temp_c < 20.0:
        return _clip_score(1.0 - ((20.0 - temp_c) / 12.0))
    return _clip_score(1.0 - ((temp_c - 26.0) / 12.0))


def _fresh_food_score(ctx: SceneContext) -> float:
    total = 0
    fresh = 0
    for node in ctx.nodes.values():
        if canonical_semantic_type(node) not in FOOD_TYPES:
            continue
        total += 1
        states = _states(node)
        if not bool(states.get("is_rotten", False)) and float(states.get("freshness", 1.0)) >= 0.35:
            fresh += 1
    if total == 0:
        return 0.7
    return _clip_score(fresh / total)


def _state_to_scene(raw_scene: dict[str, Any], state: dict) -> dict[str, Any]:
    scene = copy.deepcopy(raw_scene)
    set_scene_graph(
        scene,
        list(state["nodes"].values()),
        state["structural_edges"] + state["control_edges"] + _dynamic_edges(state),
    )
    scene.setdefault("world_state", {})
    scene["world_state"].update(copy.deepcopy(state.get("world_state") or {}))
    scene["world_state"]["event_log"] = state["logs"][-16:]
    scene["world_state"]["step"] = int(state.get("world_state", {}).get("step") or scene["world_state"].get("step") or 0)
    scene["world_state"]["time_min"] = int(state.get("world_state", {}).get("time_min") or scene["world_state"].get("time_min") or 0)
    return scene


def _build_context(raw_scene: dict[str, Any]) -> SceneContext:
    normalized = normalize_home_scene(copy.deepcopy(raw_scene))
    world_state = normalized.setdefault("world_state", {})
    ensure_world_environment(world_state)
    target_step = int(world_state.get("step") or 0)
    base_time_min = int(world_state.get("time_min") or 0)
    base_day = int(world_state.get("day") or 1)
    minutes_per_step = max(1, int(world_state.get("minutes_per_step") or 10))
    state = build_runtime_state(normalized)
    ensure_world_environment(state.setdefault("world_state", {}))
    current_structure_records: list[dict[str, Any]] = []
    current_state_records: list[dict[str, Any]] = []
    trend_snapshots: list[dict[str, Any]] = []

    for step in range(target_step + 1):
        absolute_time = base_time_min + step * minutes_per_step
        state["world_state"]["day"] = base_day + (absolute_time // (24 * 60))
        state["world_state"]["time_min"] = absolute_time % (24 * 60)
        state["world_state"]["minutes_per_step"] = minutes_per_step
        ensure_world_environment(state["world_state"])
        apply_npc_routines(state, step)
        apply_runtime_rules(state, step)
        apply_environment_step(state, step)
        current_structure_records = _structure_issue_records(state)
        current_state_records = _state_issue_records(state)
        trend_snapshots.append(
            {
                "step": step,
                "structure_count": len(current_structure_records),
                "state_count": len(current_state_records),
                "active_issue_count": len(current_structure_records) + len(current_state_records),
            }
        )

    state["world_state"]["step"] = target_step
    scene = _state_to_scene(normalized, state)
    nodes = {str(node["id"]): node for node in scene_nodes(scene) if node.get("id")}
    edges = [edge for edge in scene_edges(scene) if edge.get("source_id") and edge.get("target_id")]
    rooms = {nid: node for nid, node in nodes.items() if canonical_node_type(node) == "room"}
    agents = {nid: node for nid, node in nodes.items() if canonical_node_type(node) == "agent"}
    parent_of: dict[str, str] = {}
    room_of: dict[str, str] = {}

    for edge in edges:
        source = str(edge.get("source_id") or "")
        target = str(edge.get("target_id") or "")
        relation = str(edge.get("relation") or "").lower()
        if relation in {"inside_room", "in", "on", "held_by", "worn_by", "at", "near", "part_of"}:
            parent_of[target] = source

    for node_id in nodes:
        current = node_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            node = nodes.get(current) or {}
            if canonical_node_type(node) == "room":
                room_of[node_id] = current
                break
            current = parent_of.get(current, "")

    return SceneContext(
        raw_scene=normalized,
        scene=scene,
        scene_type=_scene_type(scene),
        nodes=nodes,
        edges=edges,
        room_of=room_of,
        parent_of=parent_of,
        rooms=rooms,
        agents=agents,
        current_structure_records=current_structure_records,
        current_state_records=current_state_records,
        trend_snapshots=trend_snapshots,
    )


def _structure_issue_records(state: dict) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    nodes = state.get("nodes", {})
    parent_of = state.get("parent_of", {})
    room_of = state.get("room_of", {})
    parent_counts: Counter[str] = Counter()

    for node_id, node in nodes.items():
        if canonical_node_type(node) != "movable_object":
            continue
        semantic = canonical_semantic_type(node)
        parent_id = parent_of.get(node_id, "")
        room_id = room_of.get(node_id, "")
        if parent_id:
            parent_counts[parent_id] += 1

        allowed_rooms = STRUCTURE_ALLOWED_ROOMS.get(semantic)
        if allowed_rooms and room_id and room_id not in allowed_rooms:
            records.append({
                "bucket": "structure",
                "kind": "misplaced_room",
                "key": f"{node_id}:misplaced_room",
                "message": f"{node_id} is in {room_id}, outside allowed rooms",
            })

        allowed_parents = STRUCTURE_ALLOWED_PARENTS.get(semantic)
        if allowed_parents and parent_id and parent_id not in allowed_parents:
            records.append({
                "bucket": "structure",
                "kind": "misplaced_parent",
                "key": f"{node_id}:misplaced_parent",
                "message": f"{node_id} is attached to {parent_id}, outside allowed parents",
            })

        states = _states(node)
        if bool(states.get("scattered", False)):
            records.append({
                "bucket": "structure",
                "kind": "scattered",
                "key": f"{node_id}:scattered",
                "message": f"{node_id} is scattered",
            })

        misplaced_near = str(states.get("misplaced_near") or "")
        if misplaced_near:
            records.append({
                "bucket": "structure",
                "kind": "misplaced_near",
                "key": f"{node_id}:misplaced_near:{misplaced_near}",
                "message": f"{node_id} is misplaced near {misplaced_near}",
            })

    for parent_id, count in parent_counts.items():
        parent = nodes.get(parent_id) or {}
        limit = int(parent.get("affordance_count") or 0)
        if limit > 0 and count > limit:
            records.append({
                "bucket": "structure",
                "kind": "over_capacity",
                "key": f"{parent_id}:over_capacity",
                "message": f"{parent_id} exceeds carrying capacity",
            })

    return records


def _state_issue_records(state: dict) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    nodes = state.get("nodes", {})

    for node_id, node in nodes.items():
        semantic = canonical_semantic_type(node)
        semantic_class = canonical_semantic_class(node)
        states = _states(node)

        if bool(states.get("is_dirty", False)):
            records.append({
                "bucket": "state",
                "kind": "dirty",
                "key": f"{node_id}:dirty",
                "message": f"{node_id} is dirty",
                "channels": {"cleanliness"},
            })

        if semantic in FOOD_TYPES and bool(states.get("is_rotten", False)):
            records.append({
                "bucket": "state",
                "kind": "rotten",
                "key": f"{node_id}:rotten",
                "message": f"{node_id} is rotten",
                "channels": {"cleanliness"},
            })

        if "cleanliness" in states and float(states.get("cleanliness", 1.0)) < 0.5:
            records.append({
                "bucket": "state",
                "kind": "low_cleanliness",
                "key": f"{node_id}:low_cleanliness",
                "message": f"{node_id} cleanliness is low",
                "channels": {"cleanliness"},
            })

        if semantic == "trash_bin" and (bool(states.get("is_full", False)) or float(states.get("fill_level", 0.0)) >= 0.75):
            records.append({
                "bucket": "state",
                "kind": "trash_full",
                "key": f"{node_id}:trash_full",
                "message": f"{node_id} is full",
                "channels": {"cleanliness"},
            })

        if semantic == "sink" and (bool(states.get("is_full", False)) or float(states.get("fill_level", 0.0)) > 0.5):
            records.append({
                "bucket": "state",
                "kind": "sink_full",
                "key": f"{node_id}:sink_full",
                "message": f"{node_id} has standing water",
                "channels": {"cleanliness"},
            })

        if semantic in OPENABLE_TYPES and bool(states.get("is_open", False)):
            channels = {"safety"}
            if semantic != "door":
                records.append({
                    "bucket": "state",
                    "kind": "open",
                    "key": f"{node_id}:open",
                    "message": f"{node_id} is open",
                    "channels": channels,
                })
            elif _door_risk_record(state, node_id):
                records.append(_door_risk_record(state, node_id))

        if semantic in RISK_ACTIVE_TYPES and bool(states.get("is_on", False)):
            records.append({
                "bucket": "state",
                "kind": "active_risk",
                "key": f"{node_id}:active_risk",
                "message": f"{node_id} is active",
                "channels": {"safety"},
            })

        if semantic_class == "appliance" and semantic == "medicine_fridge" and not bool(states.get("is_on", True)):
            records.append({
                "bucket": "state",
                "kind": "fridge_off",
                "key": f"{node_id}:fridge_off",
                "message": f"{node_id} is off",
                "channels": {"safety"},
            })

    return records


def _room_occupants(state: dict, room_id: str) -> list[dict[str, Any]]:
    nodes = state.get("nodes", {})
    parent_of = state.get("parent_of", {})
    room_of: dict[str, str] = {}
    for node_id in nodes:
        current = node_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            node = nodes.get(current) or {}
            if canonical_node_type(node) == "room":
                room_of[node_id] = current
                break
            current = parent_of.get(current, "")
    occupants: list[dict[str, Any]] = []
    for node_id, current_room in room_of.items():
        if current_room != room_id:
            continue
        node = nodes.get(node_id) or {}
        if canonical_node_type(node) == "agent":
            occupants.append(node)
    return occupants


def _door_risk_record(state: dict, node_id: str) -> dict[str, Any] | None:
    nodes = state.get("nodes", {})
    node = nodes.get(node_id) or {}
    scene = {"world_state": copy.deepcopy(state.get("world_state") or {}), "scene_name": state.get("scene_name") or ""}
    scene_type = _scene_type(scene)
    parent_of = state.get("parent_of", {})
    connected_rooms = connected_rooms_for_door_node(node)
    room_id = str(parent_of.get(node_id) or (connected_rooms[0] if connected_rooms else ""))
    low_risk_daytime = _is_daytime_low_risk(scene)
    occupants: list[dict[str, Any]] = []
    for candidate_room in connected_rooms or ([room_id] if room_id else []):
        occupants.extend(_room_occupants(state, candidate_room))
    has_staff = any(_agent_role(agent) in {"doctor", "nurse", "receptionist"} for agent in occupants)
    has_activity = bool(occupants)
    severity = "medium"
    channels = {"safety"}

    if scene_type != "hospital":
        if low_risk_daytime and has_activity:
            return None
        severity = "medium" if low_risk_daytime else "high"
    else:
        if room_id in HOSPITAL_PUBLIC_ROOMS:
            if low_risk_daytime and (has_activity or has_staff):
                return None
            severity = "low" if low_risk_daytime else "medium"
        elif room_id in HOSPITAL_SEMI_PRIVATE_ROOMS:
            severity = "low" if low_risk_daytime and (has_activity or has_staff) else ("medium" if low_risk_daytime else "high")
        elif room_id in HOSPITAL_SENSITIVE_ROOMS:
            severity = "medium" if low_risk_daytime and has_staff else "high"
        else:
            severity = "low" if low_risk_daytime and has_activity else ("medium" if low_risk_daytime else "high")

    return {
        "bucket": "state",
        "kind": f"open_{severity}",
        "key": f"{node_id}:open:{severity}",
        "message": f"{node_id} is open",
        "channels": channels,
    }


def _penalty_total(records: list[dict[str, Any]], penalty_map: dict[str, float]) -> float:
    total = 0.0
    for record in records:
        total += float(penalty_map.get(record["kind"], 0.0))
    return round(total, 4)


def _score_from_penalty(penalty: float) -> float:
    return _clip_score(1.0 - max(0.0, float(penalty)))


def _recent_trend_score(trend_snapshots: list[dict[str, Any]]) -> float:
    if not trend_snapshots:
        return 1.0
    window = trend_snapshots[-TREND_WINDOW_STEPS:]
    current_count = float(window[-1]["active_issue_count"])
    previous_count = float(window[0]["active_issue_count"])
    average_count = sum(float(item["active_issue_count"]) for item in window) / max(1, len(window))

    if current_count <= 0.0 and average_count <= 0.5:
        return 1.0

    improvement = previous_count - current_count
    normalized_level = average_count / (average_count + 6.0)
    normalized_improvement = improvement / max(4.0, previous_count + 1.0)
    score = 0.70 + 0.20 * normalized_improvement - 0.35 * normalized_level
    return _clip_score(score)


def _primary_human(ctx: SceneContext) -> tuple[str, dict[str, Any]]:
    if "human_resident" in ctx.nodes:
        return "human_resident", ctx.nodes["human_resident"]
    if ctx.agents:
        actor_id = sorted(ctx.agents)[0]
        return actor_id, ctx.agents[actor_id]
    return "", {}


def _role_metrics(ctx: SceneContext, role_profile: dict[str, float]) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for actor_id, agent in sorted(ctx.agents.items()):
        profile = copy.deepcopy(role_profile)
        profile["id"] = actor_id
        profile["role"] = _agent_role(agent)
        profile["name"] = str(agent.get("name") or actor_id)
        profile["name_cn"] = str(agent.get("name_cn") or agent.get("name") or actor_id)
        profile["activity"] = str((_states(agent).get("current_activity")) or "")
        profile["room_id"] = ctx.room_of.get(actor_id, "")
        profile["is_primary"] = actor_id == "human_resident"
        payload[actor_id] = profile
    return payload


def _agent_role(agent: dict[str, Any]) -> str:
    operation = str((agent.get("property") or {}).get("operation") or "")
    role = "agent"
    for part in operation.split(";"):
        part = part.strip()
        if part.startswith("schedule_role="):
            role = part.split("=", 1)[1].strip() or "agent"
    return role


def evaluate_scene(raw_scene: dict[str, Any]) -> dict[str, Any]:
    ctx = _build_context(raw_scene)
    structure_records = ctx.current_structure_records
    state_records = ctx.current_state_records

    structure_issues = [str(record.get("message") or "") for record in structure_records]
    state_issues = [str(record.get("message") or "") for record in state_records]

    structure_penalty = _penalty_total(structure_records, STRUCTURE_PENALTIES)
    cleanliness_penalty = _penalty_total(
        [record for record in state_records if "cleanliness" in set(record.get("channels") or [])],
        STATE_PENALTIES,
    )
    safety_penalty = _penalty_total(
        [record for record in state_records if "safety" in set(record.get("channels") or [])],
        STATE_PENALTIES,
    )

    orderliness_score = _score_from_penalty(structure_penalty)
    cleanliness_score = _score_from_penalty(cleanliness_penalty)
    safety_score = _score_from_penalty(safety_penalty)

    world_score = _weighted_score(
        {
            "safety": safety_score,
            "cleanliness": cleanliness_score,
            "orderliness": orderliness_score,
        },
        WORLD_SCORE_WEIGHTS,
    )

    actor_id, actor = _primary_human(ctx)
    states = _states(actor)
    mood = float(states.get("mood", 1.0))
    activity = str(states.get("current_activity") or "")
    room_id = ctx.room_of.get(actor_id, "")
    room_temperature = float(_states(ctx.rooms.get(room_id, {})).get("temperature", 24.0)) if room_id else 24.0
    thermal_comfort_score = _temperature_comfort_score(room_temperature)
    fresh_food_score = _fresh_food_score(ctx)
    accessibility_score = 1.0 if room_id and room_id in ctx.rooms else 0.6

    human_safety_score = _weighted_score(
        {
            "safety": safety_score,
            "cleanliness": cleanliness_score,
            "fresh_food": fresh_food_score,
        },
        {
            "safety": 0.50,
            "cleanliness": 0.25,
            "fresh_food": 0.25,
        },
    )
    comfort_score = _weighted_score(
        {
            "thermal": thermal_comfort_score,
            "cleanliness": cleanliness_score,
            "mood": mood,
        },
        {
            "thermal": 0.45,
            "cleanliness": 0.35,
            "mood": 0.20,
        },
    )
    convenience_score = _weighted_score(
        {
            "orderliness": orderliness_score,
            "accessibility": accessibility_score,
            "safety": safety_score,
        },
        {
            "orderliness": 0.45,
            "accessibility": 0.35,
            "safety": 0.20,
        },
    )
    mood_score = _clip_score(mood)
    human_score = _weighted_score(
        {
            "safety": human_safety_score,
            "comfort": comfort_score,
            "convenience": convenience_score,
            "mood": mood_score,
        },
        HUMAN_SCORE_WEIGHTS,
    )

    trend_score = _recent_trend_score(ctx.trend_snapshots)
    current_state_score = _weighted_score(
        {
            "world": world_score,
            "human": human_score,
        },
        {
            "world": 0.65,
            "human": 0.35,
        },
    )
    final_score = _weighted_score(
        {
            "current_state": current_state_score,
            "trend": trend_score,
        },
        FINAL_SCORE_WEIGHTS,
    )

    top_issues = structure_issues + state_issues
    if activity:
        top_issues.append(f"{actor_id or 'primary_agent'} current activity: {activity}")
    if mood < 0.5:
        top_issues.append(f"{actor_id or 'primary_agent'} mood is low")
    if thermal_comfort_score < 0.6:
        top_issues.append(f"{room_id or 'current_room'} temperature is uncomfortable ({room_temperature:.1f}C)")

    return {
        "scene_type": ctx.scene_type,
        "world_metrics": {
            "world_score": world_score,
            "human_score": human_score,
            "final_score": final_score,
            "cleanliness_score": cleanliness_score,
            "orderliness_score": orderliness_score,
            "safety_score": safety_score,
            "comfort_score": comfort_score,
            "convenience_score": convenience_score,
            "mood_score": mood_score,
            "trend_score": trend_score,
            "current_state_score": current_state_score,
        },
        "world_details": {
            "structure": {
                "penalty": round(structure_penalty, 4),
                "active_issue_count": len(structure_records),
                "tracked_issue_count": len(structure_records),
            },
            "state": {
                "cleanliness_penalty": round(cleanliness_penalty, 4),
                "safety_penalty": round(safety_penalty, 4),
                "active_issue_count": len(state_records),
                "tracked_issue_count": len(state_records),
            },
            "system": {
                "entropy": round(float((ctx.scene.get("world_state") or {}).get("entropy") or 0.0), 4),
                "collapse_stage": str((ctx.scene.get("world_state") or {}).get("collapse_stage") or "stable"),
                "weather": str((ctx.scene.get("world_state") or {}).get("weather") or "sunny"),
                "season_name": str((ctx.scene.get("world_state") or {}).get("season_name") or "spring"),
                "weekday_name": str((ctx.scene.get("world_state") or {}).get("weekday_name") or "monday"),
                "trend_score": round(trend_score, 4),
            },
            "human": {
                "mood": round(mood, 4),
                "accessibility_score": round(accessibility_score, 4),
                "safety_score": round(human_safety_score, 4),
                "comfort_score": round(comfort_score, 4),
                "convenience_score": round(convenience_score, 4),
                "mood_score": round(mood_score, 4),
                "fresh_food_score": round(fresh_food_score, 4),
                "room_temperature_c": round(room_temperature, 2),
                "thermal_comfort_score": round(thermal_comfort_score, 4),
                "primary_actor": actor_id,
            },
        },
        "role_metrics": _role_metrics(
            ctx,
            {
                "role_score": human_score,
                "mood_score": mood_score,
                "convenience_score": convenience_score,
                "safety_score": human_safety_score,
                "comfort_score": comfort_score,
                "final_score": final_score,
            },
        ),
        "top_issues": top_issues[:12],
        "meta": {
            "room_count": len(ctx.rooms),
            "node_count": len(ctx.nodes),
            "edge_count": len(ctx.edges),
            "agent_count": len(ctx.agents),
        },
    }
