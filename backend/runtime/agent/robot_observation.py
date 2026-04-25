from __future__ import annotations

import copy
from typing import Any

from ..engine.state import build_runtime_state
from ..engine.state import connected_rooms_for_door_node, is_room_door_node
from ..eval.scene_evaluator import evaluate_scene
from ..schema.home_schema import canonical_node_type, canonical_semantic_type, normalize_home_scene, scene_nodes
from ..world.environment import ensure_world_environment
from .robot_executor import _agent_anchor, _ensure_robot_agent_node, _holding_item, _room_of, _state_to_scene
from .robot_planner import ALLOWED_ACTIONS


DEFAULT_AGENT_DRIVES = [
    "preserve world stability over time",
    "reduce accumulating safety, cleanliness, and order risks",
    "learn environment structure and causal control relations",
    "support humans according to the current scene and role context",
]

GAME_OVER_WORLD_SCORE = 0.60
RISK_TYPES = {"stove", "faucet", "washer", "washing_machine", "microwave", "dishwasher"}
CONTROL_TYPES = {"button", "knob", "door"}
HUMAN_TYPES = {"human", "resident", "doctor", "nurse", "patient", "receptionist"}


def ensure_scene_robot_stub(scene: dict[str, Any], agent_id: str) -> None:
    scene.setdefault("agent", {})
    scene["agent"].setdefault("id", agent_id)
    if scene["agent"].get("current_room"):
        return
    first_room = next(
        (str(node.get("id")) for node in scene_nodes(scene) if canonical_node_type(node) == "room"),
        "",
    )
    if first_room:
        scene["agent"]["current_room"] = first_room
    scene["agent"].setdefault("inventory", [])


def current_step(world_state: dict[str, Any]) -> int:
    return int(world_state.get("step") or 0)


def current_time_min(world_state: dict[str, Any]) -> int:
    return int(world_state.get("time_min") or 0)


def minutes_per_step(world_state: dict[str, Any]) -> int:
    return max(1, int(world_state.get("minutes_per_step") or 10))


def clock_text(minutes: int) -> str:
    total = minutes % (24 * 60)
    hour = total // 60
    minute = total % 60
    return f"{hour:02d}:{minute:02d}"


def adjacent_rooms(state: dict, room_id: str) -> list[str]:
    neighbors: set[str] = set()
    for edge in state.get("structural_edges", []):
        if str(edge.get("relation") or "").lower() != "adjacent_to":
            continue
        source = str(edge.get("source_id") or "")
        target = str(edge.get("target_id") or "")
        if source == room_id and target:
            neighbors.add(target)
        elif target == room_id and source:
            neighbors.add(source)
    return sorted(neighbors)


def _is_open_door(node: dict[str, Any]) -> bool:
    if canonical_semantic_type(node) != "door":
        return False
    states = node.get("states") or {}
    return bool(states.get("is_open", states.get("isOpen", False)))


def _rooms_revealed_by_open_doors(state: dict, room_id: str) -> set[str]:
    revealed: set[str] = set()
    for node in state.get("nodes", {}).values():
        if not is_room_door_node(node) or not _is_open_door(node):
            continue
        connected_rooms = connected_rooms_for_door_node(node)
        if room_id not in connected_rooms:
            continue
        for other_room in connected_rooms:
            other_room = str(other_room or "")
            if other_room and other_room != room_id:
                revealed.add(other_room)
    return revealed


def visible_nodes(state: dict, agent_id: str) -> list[dict[str, Any]]:
    room_id = _room_of(state, agent_id)
    visible_rooms = {room_id}
    current_room_nodes = [
        node
        for node_id, node in state.get("nodes", {}).items()
        if node_id != agent_id and (
            _room_of(state, node_id) == room_id
            or (is_room_door_node(node) and room_id in connected_rooms_for_door_node(node))
        )
    ]
    visible_rooms.update(_rooms_revealed_by_open_doors(state, room_id))
    scanned_rooms = {
        node_id
        for node_id, node in state.get("nodes", {}).items()
        if canonical_node_type(node) == "room" and bool((node.get("states") or {}).get("scanned", False))
    }

    visible: list[dict[str, Any]] = []
    for node_id, node in state.get("nodes", {}).items():
        if node_id == agent_id:
            continue

        node_room = _room_of(state, node_id)
        if is_room_door_node(node):
            if not (set(connected_rooms_for_door_node(node)) & visible_rooms):
                continue
        elif node_room not in visible_rooms:
            continue

        node_type = canonical_node_type(node)
        parent_id = state.get("parent_of", {}).get(node_id)

        # ==========================================
        # ✅ 替换为以下新的视野过滤逻辑
        # ==========================================
        
        # 1. 跨房间视野限制：门开着时，只能看到隔壁房间的“房间本身”和“一阶子节点”（如地上的桌子）
        if node_room != room_id and node_type != "room":
            if parent_id != node_room:
                continue

        # 2. 容器内部视野限制（Auto-See 核心）：如果物体在某个父节点内部（非房间）
        if parent_id and parent_id != node_room:
            parent_node = state.get("nodes", {}).get(parent_id)
            if parent_node:
                parent_states = parent_node.get("states") or {}
                # 如果父节点具有开闭状态，并且当前是关着的，则隐藏内部物品！
                if "is_open" in parent_states or "isOpen" in parent_states:
                    if not parent_states.get("is_open", parent_states.get("isOpen", False)):
                        continue
        # ==========================================

        visible.append(
            {
                "id": node_id,
                # ... 下面保留你原有的字典生成逻辑不变 ...
                "name": node.get("name"),
                "name_cn": node.get("name_cn"),
                "node_type": canonical_node_type(node),
                "semantic_type": canonical_semantic_type(node),
                "parent": state.get("parent_of", {}).get(node_id),
                "states": copy.deepcopy(node.get("states") or {}),
                "interactive_actions": list(node.get("interactive_actions") or []),
            }
        )
    visible.sort(key=lambda item: (item["node_type"], item["semantic_type"], item["id"]))
    return visible


def compressed_observation(
    observation: dict[str, Any],
    recent_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    visible = list(observation.get("visible_nodes") or [])
    current_room_objects: list[dict[str, Any]] = []
    for node in visible:
        current_room_objects.append(
            {
                "id": node.get("id"),
                "semantic_type": str(node.get("semantic_type") or ""),
                "states": copy.deepcopy(node.get("states") or {}),
                "interactive_actions": list(node.get("interactive_actions") or []),
            }
        )

    return {
        "world": {
            "step": (observation.get("world") or {}).get("step"),
            "clock": (observation.get("world") or {}).get("clock"),
            "day_phase": (observation.get("world") or {}).get("day_phase"),
            "weather": (observation.get("world") or {}).get("weather"),
            "world_score": (observation.get("scores") or {}).get("world_score"),
            "human_score": (observation.get("scores") or {}).get("human_score"),
        },
        "robot": {
            "id": (observation.get("robot") or {}).get("id"),
            "current_room": (observation.get("robot") or {}).get("current_room"),
            "holding": (observation.get("robot") or {}).get("holding"),
        },
        "current_room_objects": current_room_objects[:12],
        "adjacent_rooms": list((observation.get("robot") or {}).get("adjacent_rooms") or []),
        "recent_memory": copy.deepcopy(recent_memory or {}),
    }


def build_robot_observation(
    raw_scene: dict,
    task: dict[str, Any] | str | None = None,
    runtime_state: dict | None = None,
    agent_id: str = "robot_01",
) -> dict[str, Any]:
    scene = normalize_home_scene(copy.deepcopy(raw_scene))
    ensure_scene_robot_stub(scene, agent_id)
    state = copy.deepcopy(runtime_state) if runtime_state is not None else build_runtime_state(scene)
    _ensure_robot_agent_node(state, scene, agent_id)
    ensure_world_environment(state.setdefault("world_state", {}))

    world_state = state.get("world_state") or {}
    room_id = _room_of(state, agent_id)
    holding = _holding_item(state, agent_id)
    if isinstance(task, str):
        normalized_task = {"goal": task.strip()} if task.strip() else {}
    else:
        normalized_task = copy.deepcopy(task or {})
    task_payload = normalized_task if isinstance(normalized_task, dict) else {}
    mission_goal = (
        str(task_payload.get("goal") or "").strip()
        or "Act autonomously from internal drives: keep the world stable, learn useful structure and dynamics, and support humans."
    )
    metrics = evaluate_scene(_state_to_scene(scene, state, agent_id))
    world_metrics = metrics.get("world_metrics") or {}

    observation = {
        "mission": {
            "identity": "household_service_robot",
            "goal": mission_goal,
            "drives": copy.deepcopy(task_payload.get("drives") or DEFAULT_AGENT_DRIVES),
            "game_over_world_score_below": GAME_OVER_WORLD_SCORE,
        },
        "world": {
            "step": current_step(world_state),
            "day": int(world_state.get("day") or 1),
            "time_min": current_time_min(world_state),
            "clock": clock_text(current_time_min(world_state)),
            "minutes_per_step": minutes_per_step(world_state),
            "weather": str(world_state.get("weather") or "sunny"),
            "day_phase": str(world_state.get("day_phase") or "day"),
        },
        "robot": {
            "id": agent_id,
            "current_room": room_id,
            "current_anchor": _agent_anchor(state, agent_id),
            "holding": holding,
            "adjacent_rooms": adjacent_rooms(state, room_id),
        },
        "scores": {
            "world_score": float(world_metrics.get("world_score") or 0.0),
            "human_score": float(world_metrics.get("human_score") or 0.0),
        },
        "visible_nodes": visible_nodes(state, agent_id),
        "task": task_payload,
        "allowed_actions": list(ALLOWED_ACTIONS),
        "output_format": {
            "reasoning": "short reasoning string",
            "action": {
                "action_type": "one of move/pick/place/press/scan/open/close/brush",
                "target_id": "node id when needed",
                "object_id": "node id when needed",
                "placement_target_id": "node id when needed for place",
            },
        },
    }
    observation["compressed_observation"] = compressed_observation(observation)
    return observation


__all__ = [
    "DEFAULT_AGENT_DRIVES",
    "GAME_OVER_WORLD_SCORE",
    "adjacent_rooms",
    "build_robot_observation",
    "compressed_observation",
    "clock_text",
    "current_step",
    "current_time_min",
    "ensure_scene_robot_stub",
    "minutes_per_step",
    "visible_nodes",
]
