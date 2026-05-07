from __future__ import annotations

from collections import defaultdict
import copy
import json
import math
from pathlib import Path
import re

import networkx as nx

from backend.core import get_object_spec
from backend.replay_store import ReplayStore
from backend.human_session_store import HumanSessionStore
from backend.runtime import evaluate_scene, simulate_scene
from backend.runtime.engine.engine import simulate_scene_with_state
from backend.runtime.schema.home_schema import (
    canonical_mobility,
    canonical_node_type,
    canonical_property,
    canonical_semantic_class,
    canonical_semantic_type,
    scene_edges,
    scene_nodes,
)

ROOT = Path(__file__).resolve().parent
SCENE_DIRS = [
    ROOT / "data" / "sg_output" / "simple_graph",
    ROOT / "data" / "sg_output" / "simple_graph_new",
    ROOT / "data" / "sg_output" / "batch_strict",
    ROOT / "data" / "sg_output" / "batch_v1",
    ROOT / "data" / "sg_output" / "batch_v2",
    ROOT / "data" / "sg_output" / "graph_new",
]


SCENE_PREFIX_CN = {
    "hospital": "医院场景",
    "hotel": "酒店场景",
    "library": "图书馆场景",
    "office": "办公场景",
    "supermarket": "超市场景",
    "teaching_building": "教学楼场景",
    "school": "学校场景",
}

MOVABLE_AFFORDANCES = {
    "movable",
    "wearable",
    "drinkable",
    "edible",
    "dishware",
    "usable",
    "tool",
    "cleaning",
}


def _ring(n: int, r: float, cx: float = 0.0, cy: float = 0.0) -> list[tuple[float, float]]:
    if n <= 0:
        return []
    if n == 1:
        return [(cx, cy)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _concentric_points(
    n: int,
    base_radius: float,
    radius_step: float,
    min_gap: float,
    cx: float = 0.0,
    cy: float = 0.0,
) -> list[tuple[float, float]]:
    if n <= 0:
        return []
    if n == 1:
        return [(cx, cy)]
    points: list[tuple[float, float]] = []
    remaining = n
    ring_index = 0
    while remaining > 0:
        radius = base_radius + ring_index * radius_step
        capacity = max(6, int((2 * math.pi * radius) / max(min_gap, 1.0)))
        take = min(remaining, capacity)
        points.extend(_ring(take, radius, cx, cy))
        remaining -= take
        ring_index += 1
    return points


def _normalize_layout(pos: dict[str, tuple[float, float]], width: float, height: float) -> dict[str, tuple[float, float]]:
    if not pos:
        return {}
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-6)
    span_y = max(max_y - min_y, 1e-6)
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    scale = min(width / span_x, height / span_y) * 0.88
    return {nid: ((x - cx) * scale, (y - cy) * scale) for nid, (x, y) in pos.items()}


def _relax_positions(
    pos: dict[str, tuple[float, float]],
    radii: dict[str, float],
    min_x: float,
    max_x: float,
    min_y: float,
    max_y: float,
    iterations: int = 120,
) -> dict[str, tuple[float, float]]:
    movable = {nid: [x, y] for nid, (x, y) in pos.items()}
    ids = list(movable.keys())
    for _ in range(iterations):
        moved = False
        for i in range(len(ids)):
            a = ids[i]
            ax, ay = movable[a]
            for j in range(i + 1, len(ids)):
                b = ids[j]
                bx, by = movable[b]
                dx = bx - ax
                dy = by - ay
                dist = math.hypot(dx, dy)
                min_dist = radii.get(a, 90.0) + radii.get(b, 90.0)
                if dist >= min_dist:
                    continue
                if dist < 1e-6:
                    dx, dy, dist = 1.0, 0.0, 1.0
                push = (min_dist - dist) / 2.0
                ux, uy = dx / dist, dy / dist
                movable[a][0] -= ux * push
                movable[a][1] -= uy * push
                movable[b][0] += ux * push
                movable[b][1] += uy * push
                moved = True
        for nid in ids:
            movable[nid][0] = max(min_x, min(max_x, movable[nid][0]))
            movable[nid][1] = max(min_y, min(max_y, movable[nid][1]))
        if not moved:
            break
    return {nid: (float(coords[0]), float(coords[1])) for nid, coords in movable.items()}


def _room_label(node: dict) -> str:
    name = str(node.get("name") or "")
    node_id = str(node.get("id") or "")
    return name if name and name != node_id else node_id.replace("_", " ")


def _item_label(node: dict) -> str:
    text = str(node.get("semantic_type") or node.get("object_type") or node.get("name") or node.get("id") or "item")
    return text.replace("__", "_").replace("_", " ")


def _normalize_rect_layout(layout: dict | None) -> dict | None:
    if not isinstance(layout, dict):
        return None
    try:
        x = float(layout.get("x"))
        y = float(layout.get("y"))
        w = float(layout.get("w"))
        h = float(layout.get("h"))
    except (TypeError, ValueError):
        return None
    rect = {"x": x, "y": y, "w": w, "h": h}
    if isinstance(layout.get("orientation"), str):
        rect["orientation"] = str(layout["orientation"])
    doorways = []
    for doorway in layout.get("doorways") or []:
        if not isinstance(doorway, dict):
            continue
        try:
            doorway_rect = {
                "to": str(doorway.get("to") or doorway.get("target_room") or ""),
                "orientation": str(doorway.get("orientation") or ""),
                "x": float(doorway.get("x")),
                "y": float(doorway.get("y")),
                "length": float(doorway.get("length")),
                "width": float(doorway.get("width")),
            }
        except (TypeError, ValueError):
            continue
        doorways.append(doorway_rect)
    if doorways:
        rect["doorways"] = doorways
    return rect


def _bounds_from_layouts(layouts: list[dict]) -> dict | None:
    valid = [layout for layout in layouts if isinstance(layout, dict)]
    if not valid:
        return None
    min_x = min(layout["x"] for layout in valid)
    min_y = min(layout["y"] for layout in valid)
    max_x = max(layout["x"] + layout["w"] for layout in valid)
    max_y = max(layout["y"] + layout["h"] for layout in valid)
    return {
        "x": float(min_x),
        "y": float(min_y),
        "w": float(max_x - min_x),
        "h": float(max_y - min_y),
    }


def _node_meta(node: dict, *, parent: str | None = None, child: list[str] | None = None, current_location=None) -> dict:
    semantic_type = node.get("semantic_type") or node.get("object_type") or node.get("type")
    meta = {
        "node_type": canonical_node_type(node),
        "semantic_class": canonical_semantic_class(node),
        "semantic_type": semantic_type,
        "mobility": canonical_mobility(node),
        "states": node.get("states") or {},
        "property": copy.deepcopy(node.get("property") or canonical_property(node)),
        "affordance_count": node.get("affordance_count", 0),
        "parent": parent,
        "child": copy.deepcopy(child or node.get("child") or []),
        "interactive_actions": copy.deepcopy(node.get("interactive_actions") or []),
        "current_location": current_location,
        "runtime": copy.deepcopy(node.get("runtime") or {}),
    }
    image_spec = get_object_spec(str(semantic_type or ""))
    image_path = node.get("image_path") or image_spec.get("image_path")
    if image_path:
        meta["image_path"] = image_path
        meta["image_url"] = node.get("image_url") or image_spec.get("image_url")
        meta["image_source_url"] = node.get("image_source_url") or image_spec.get("image_source_url")
        meta["image_license"] = node.get("image_license") or image_spec.get("image_license")
    return meta


def _node_family(node: dict) -> str:
    semantic = canonical_semantic_type(node)
    node_type = canonical_node_type(node)
    if semantic == "floor":
        return "floor"
    if node_type == "room":
        return "room"
    if node_type == "agent":
        return "agent"
    if node_type == "movable_object":
        return "movable"
    if node_type == "fixed_object":
        return "fixture"
    raw = str(node.get("type") or "").lower()
    if raw == "mobile_tool":
        return "movable"
    if raw == "object":
        affordances = {str(item).lower() for item in node.get("affordances") or []}
        if affordances & MOVABLE_AFFORDANCES:
            return "movable"
        return "fixture"
    return raw or "fixture"


def _is_tool_like(node: dict) -> bool:
    semantic = canonical_semantic_type(node)
    return semantic in {"brush", "cloth", "broom", "watering_can", "toothbrush"} or str(node.get("type") or "").lower() == "mobile_tool"


def _node_box(label: str, kind: str) -> tuple[float, float, float]:
    text = str(label or "")
    if kind == "room":
        width = max(118.0, min(230.0, 56.0 + len(text) * 7.2))
        height = 46.0
    elif kind == "fixture":
        width = max(72.0, min(132.0, 42.0 + len(text) * 6.2))
        height = 42.0
    else:
        width = max(64.0, min(150.0, 34.0 + len(text) * 5.6))
        height = 30.0
    radius = math.hypot(width, height) / 2.0 + 8.0
    return width, height, radius


def _edge_kind(edge: dict) -> str:
    relation = str(edge.get("relation") or "").lower()
    category = str(edge.get("category") or "").lower()
    if category == "control" or relation == "controls":
        return "controls"
    if relation in {"adjacent_to", "neighbour", "neighbor"}:
        return "neighbor"
    if relation in {"contains", "inside_room", "inside_floor", "in", "on", "part_of", "mounted_on", "held_by", "worn_by", "at"}:
        return "contains"
    if relation in {"transport", "carried_to"}:
        return "transport"
    if relation == "ontop":
        return "ontop"
    if relation == "next_to":
        return "next_to"
    return relation or "other"


def _scene_name_cn(scene_id: str) -> str:
    raw = str(scene_id or "")
    for prefix, label in SCENE_PREFIX_CN.items():
        if raw.startswith(prefix):
            suffix = raw[len(prefix):].strip("_ ")
            return f"{label} {suffix}".strip()
    return raw


def _floor_name_cn(name: str) -> str:
    match = re.fullmatch(r"Floor\s+(\d+)", str(name or ""), re.IGNORECASE)
    return f"第 {match.group(1)} 层" if match else str(name or "")


def _ensure_visual_robot_node(raw: dict, agent_id: str = "robot_01") -> None:
    nodes = raw.setdefault("nodes", [])
    if any(str(node.get("id") or "") == agent_id for node in nodes if isinstance(node, dict)):
        return
    agent = raw.get("agent") or {}
    current_room = str(agent.get("current_room") or "")
    if not current_room:
        current_room = next((str(node.get("id") or "") for node in nodes if isinstance(node, dict) and canonical_node_type(node) == "room"), "")
    if not current_room:
        return
    nodes.append(
        {
            "id": agent_id,
            "name": "Robot",
            "name_cn": "机器人",
            "node_type": "agent",
            "semantic_type": "robot",
            "mobility": "agent",
            "states": {"current_activity": "idle", "mood": 1.0, "is_home": True},
            "property": {"appearance": "", "physical": "", "operation": ""},
            "affordance_count": 0,
            "parent": current_room,
            "child": [],
            "interactive_actions": [],
            "layout": {},
            "current_location": current_room,
        }
    )
    edges = raw.setdefault("edges", [])
    if not any(
        isinstance(edge, dict)
        and str(edge.get("source_id") or "") == current_room
        and str(edge.get("target_id") or "") == agent_id
        and str(edge.get("relation") or "").lower() in {"at", "in", "contains"}
        for edge in edges
    ):
        edges.append(
            {
                "source_id": current_room,
                "target_id": agent_id,
                "relation": "at",
                "edge_type": "agent_room_edge",
                "category": "containment",
                "properties": {"visualized_from": "robot_injection"},
            }
        )


class SceneStore:
    def __init__(self) -> None:
        self.scenes: dict[str, dict] = {}
        self.replays = ReplayStore()
        self.human_sessions = HumanSessionStore(self.replays)
        self._simulation_cache: dict[str, dict] = {}
        self._load()

    def _simulate_scene_for_step(self, scene_id: str, raw_source: dict, step_override: int | None) -> dict:
        target_step = max(0, int(step_override)) if step_override is not None else int((raw_source.get("world_state") or {}).get("step") or 0)
        cache = self._simulation_cache.get(scene_id)
        if cache and int(cache.get("step") or 0) == target_step:
            return copy.deepcopy(cache["raw"])

        simulate_from = copy.deepcopy(raw_source)
        start_step = 0
        runtime_state = None
        if cache and target_step > int(cache.get("step") or 0):
            simulate_from.setdefault("world_state", {})
            simulate_from["world_state"]["step"] = target_step
            start_step = int(cache.get("step") or 0) + 1
            runtime_state = copy.deepcopy(cache.get("state"))
        else:
            simulate_from.setdefault("world_state", {})
            simulate_from["world_state"]["step"] = target_step

        simulated, next_state = simulate_scene_with_state(simulate_from, start_step=start_step, runtime_state=runtime_state)
        self._simulation_cache[scene_id] = {
            "step": target_step,
            "raw": copy.deepcopy(simulated),
            "state": copy.deepcopy(next_state),
        }
        return simulated

    def _load(self) -> None:
        for directory in SCENE_DIRS:
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.json")):
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                scene_id = str(raw.get("scene_name") or path.stem)
                if scene_id not in self.scenes:
                    self.scenes[scene_id] = {"path": path, "raw": raw}

    def list_scenes(self, lang: str = "en") -> list[dict]:
        items = []
        for scene_id in sorted(self.scenes):
            raw = self.scenes[scene_id]["raw"]
            nodes = raw.get("nodes", [])
            items.append(
                {
                    "id": scene_id,
                    "name": scene_id,
                    "floor_count": sum(1 for n in nodes if _node_family(n) == "floor"),
                    "room_count": sum(1 for n in nodes if _node_family(n) == "room"),
                    "object_count": sum(1 for n in nodes if _node_family(n) == "movable"),
                    "path": str(self.scenes[scene_id]["path"].relative_to(ROOT)),
                }
            )
        if lang == "cn":
            for item in items:
                raw = self.scenes[item["id"]]["raw"]
                if raw.get("scene_name_cn"):
                    item["name"] = raw["scene_name_cn"]
                else:
                    item["name"] = _scene_name_cn(item["name"])
        return items

    def get_scene(self, scene_id: str, lang: str = "en", step_override: int | None = None) -> dict | None:
        item = self.scenes.get(scene_id)
        if not item:
            return None
        raw_source = copy.deepcopy(item["raw"])
        raw = self._simulate_scene_for_step(scene_id, raw_source, step_override)
        _ensure_visual_robot_node(raw, "robot_01")
        metrics_source = copy.deepcopy(raw_source)
        metrics_source.setdefault("world_state", {})
        metrics_source["world_state"]["step"] = int((raw.get("world_state") or {}).get("step") or step_override or 0)
        metrics_source["world_state"]["day"] = int((raw_source.get("world_state") or {}).get("day") or 1)
        metrics_source["world_state"]["time_min"] = int((raw_source.get("world_state") or {}).get("time_min") or 360)
        metrics_source["world_state"]["minutes_per_step"] = int((raw_source.get("world_state") or {}).get("minutes_per_step") or 10)
        metrics = evaluate_scene(metrics_source)
        world_state = raw.get("world_state") or {}
        nodes = {str(n["id"]): n for n in scene_nodes(raw) if isinstance(n, dict) and n.get("id")}
        source_nodes = {str(n["id"]): n for n in scene_nodes(raw_source) if isinstance(n, dict) and n.get("id")}
        edges = [e for e in scene_edges(raw) if isinstance(e, dict)]
        agent = raw.get("agent") or {}
        agent_room = str(agent.get("current_room") or "")
        contains_children: dict[str, list[str]] = defaultdict(list)
        adjacency: dict[str, list[dict]] = defaultdict(list)
        for edge in edges:
            source = str(edge.get("source_id") or "")
            target = str(edge.get("target_id") or "")
            relation = str(edge.get("relation") or "").lower()
            adjacency[source].append(edge)
            adjacency[target].append(edge)
            if relation in {"contains", "in", "on", "part_of", "held_by", "worn_by", "at"} and source and target:
                contains_children[source].append(target)

        floors = sorted(
            [
                {
                    "id": str(n["id"]),
                    "name": str(n.get("name") or n["id"]),
                    "floor_number": n.get("floor_number"),
                    "room_count": len([child_id for child_id in n.get("child") or [] if child_id in nodes and _node_family(nodes[child_id]) == "room"]),
                }
                for n in nodes.values()
                if _node_family(n) == "floor"
            ],
            key=lambda x: (x["floor_number"] if isinstance(x["floor_number"], int) else 9999, x["id"]),
        )

        floor_by_room: dict[str, str] = {}
        for node in nodes.values():
            if _node_family(node) != "room":
                continue
            room_id = str(node["id"])
            floor_id = str(node.get("parent") or node.get("floor_id") or "")
            if floor_id:
                floor_by_room[room_id] = floor_id
        for floor in floors:
            floor_id = floor["id"]
            floor_node = nodes.get(floor_id, {})
            for room_id in floor_node.get("child") or floor_node.get("rooms") or []:
                room_id = str(room_id)
                if room_id in nodes and _node_family(nodes[room_id]) == "room":
                    floor_by_room.setdefault(room_id, floor_id)
        for edge in edges:
            source = str(edge.get("source_id") or "")
            target = str(edge.get("target_id") or "")
            relation = str(edge.get("relation") or "").lower()
            if relation in {"contains", "inside_floor"} or str(edge.get("edge_type") or "").lower() == "room_floor_edge":
                if source in nodes and target in nodes:
                    source_type = _node_family(nodes[source])
                    target_type = _node_family(nodes[target])
                    if source_type == "floor" and target_type == "room":
                        floor_by_room.setdefault(target, source)
                    elif source_type == "room" and target_type == "floor":
                        floor_by_room.setdefault(source, target)
        for room_id, node in nodes.items():
            if _node_family(node) != "room" or room_id in floor_by_room:
                continue
            floor_id = ""
            explicit_floor = str(node.get("floor_id") or "")
            if explicit_floor:
                floor_id = explicit_floor
            else:
                match = next(iter(re.finditer(r"F(\d+)", room_id, re.IGNORECASE)), None)
                if match:
                    candidate = f"F{match.group(1)}"
                    if candidate in nodes and _node_family(nodes[candidate]) == "floor":
                        floor_id = candidate
            if floor_id:
                floor_by_room[room_id] = floor_id

        def build_floor(floor_id: str) -> dict:
            rooms = [n for n in nodes.values() if _node_family(n) == "room" and floor_by_room.get(str(n["id"])) == floor_id]
            visible: set[str] = set()
            floor_nodes, floor_edges = [], []
            room_ids = {str(r["id"]) for r in rooms}
            room_centers: dict[str, tuple[float, float]] = {}
            room_objects: dict[str, list[str]] = {}
            room_layouts: list[dict] = []
            object_layouts: list[dict] = []
            floor_layout = _normalize_rect_layout(nodes.get(floor_id, {}).get("layout") or source_nodes.get(floor_id, {}).get("layout"))

            def collect_object_tree(start_ids: list[str]) -> tuple[list[str], dict[str, int], dict[str, str]]:
                ordered: list[str] = []
                depth_by_object: dict[str, int] = {}
                parent_by_object: dict[str, str] = {}
                queue: list[tuple[str, int, str]] = [(obj_id, 1, "") for obj_id in start_ids]
                while queue:
                    obj_id, depth, parent_id = queue.pop(0)
                    if obj_id in depth_by_object or obj_id not in nodes:
                        continue
                    if _node_family(nodes[obj_id]) not in {"fixture", "movable", "agent"}:
                        continue
                    depth_by_object[obj_id] = depth
                    if parent_id:
                        parent_by_object[obj_id] = parent_id
                    ordered.append(obj_id)
                    for child_id in contains_children.get(obj_id, []):
                        if child_id not in depth_by_object:
                            queue.append((child_id, depth + 1, obj_id))
                return ordered, depth_by_object, parent_by_object

            for room in rooms:
                room_id = str(room["id"])
                direct_obj_ids = [str(oid) for oid in room.get("child") or room.get("contained_objects") or [] if oid in nodes and _node_family(nodes[oid]) in {"fixture", "movable", "agent"}]
                for node in nodes.values():
                    if _node_family(node) != "agent":
                        continue
                    node_id = str(node.get("id") or "")
                    if not node_id:
                        continue
                    node_room = str(
                        node.get("current_location")
                        or node.get("current_room")
                        or node.get("room")
                        or node.get("parent")
                        or ""
                    )
                    if node_room == room_id and node_id not in direct_obj_ids:
                        direct_obj_ids.append(node_id)
                for node in nodes.values():
                    runtime = node.get("runtime") or {}
                    connected_rooms = runtime.get("connected_rooms") or []
                    anchor_room = str(runtime.get("door_anchor_room") or (connected_rooms[0] if connected_rooms else ""))
                    if canonical_semantic_type(node) == "door" and anchor_room == room_id:
                        node_id = str(node.get("id") or "")
                        if node_id and node_id not in direct_obj_ids:
                            direct_obj_ids.append(node_id)
                for edge in edges:
                    source = str(edge.get("source_id") or "")
                    target = str(edge.get("target_id") or "")
                    relation = str(edge.get("relation") or "").lower()
                    if source == room_id and target in nodes and _node_family(nodes[target]) in {"fixture", "movable", "agent"} and relation in {"contains", "inside_room", "in", "on", "at"}:
                        if target not in direct_obj_ids:
                            direct_obj_ids.append(target)
                ordered, depth_map, parent_map = collect_object_tree(direct_obj_ids)
                room_objects[room_id] = ordered
                room.setdefault("_viz_depth_map", depth_map)
                room.setdefault("_viz_parent_map", parent_map)

            if room_ids:
                room_cluster_extent = {}
                for room in rooms:
                    room_id = str(room["id"])
                    depth_map = room.get("_viz_depth_map", {})
                    max_depth = max(depth_map.values(), default=0)
                    if max_depth <= 0:
                        room_cluster_extent[room_id] = 52.0
                    else:
                        room_cluster_extent[room_id] = 64.0 + (max_depth - 1) * 48.0 + 18.0

                if len(room_ids) == 1:
                    room_radius = 0.0
                else:
                    min_sin = max(math.sin(math.pi / len(room_ids)), 0.2)
                    required_chord = max(room_cluster_extent.values(), default=120.0) * 2.0 + 48.0
                    room_radius = max(240.0, min(460.0, required_chord / (2.0 * min_sin)))
                room_points = _ring(len(room_ids), room_radius)
                base_pos = {room_id: room_points[idx] for idx, room_id in enumerate(sorted(room_ids))}
            else:
                base_pos = {}

            for room in rooms:
                room_id = str(room["id"])
                x, y = base_pos.get(room_id, (0.0, 0.0))
                room_layout = _normalize_rect_layout(room.get("layout") or source_nodes.get(room_id, {}).get("layout"))
                if room_layout:
                    x = room_layout["x"] + room_layout["w"] / 2.0
                    y = room_layout["y"] + room_layout["h"] / 2.0
                room_width, room_height, _ = _node_box(_room_label(room), "room")
                room_radius = _node_box(_room_label(room), "room")[2]
                room_centers[room_id] = (x, y)
                visible.add(room_id)
                neighbor_count = sum(1 for e in edges if str(e.get("relation") or "").lower() == "adjacent_to" and room_id in {str(e.get("source_id") or ""), str(e.get("target_id") or "")})
                floor_nodes.append(
                    {
                        "id": room_id,
                        "label": _room_label(room),
                        "kind": "room",
                        "x": float(x),
                        "y": float(y),
                        "width": room_width,
                        "height": room_height,
                        "is_agent_room": room_id == agent_room,
                        "layout": room_layout,
                        "meta": {
                            **_node_meta(room, parent=floor_id, child=room.get("child") or room.get("contained_objects") or []),
                            "contained_objects": len(room.get("child") or room.get("contained_objects") or []),
                            "neighbors": neighbor_count,
                        },
                    }
                )
                if room_layout:
                    room_layouts.append(room_layout)
                obj_ids = room_objects.get(room_id, [])
                depth_map = room.get("_viz_depth_map", {})
                parent_map = room.get("_viz_parent_map", {})
                object_nodes = [nodes[oid] for oid in obj_ids]
                object_labels = [_item_label(obj) for obj in object_nodes]
                object_boxes = {str(obj["id"]): _node_box(label, "movable" if _node_family(obj) in {"movable", "agent"} else "fixture") for obj, label in zip(object_nodes, object_labels, strict=False)}
                object_point_map: dict[str, tuple[float, float]] = {}
                children_by_parent: dict[str, list[str]] = defaultdict(list)
                placed_radii: dict[str, float] = {room_id: room_radius}
                placed_points: dict[str, tuple[float, float]] = {room_id: (x, y)}
                for oid in obj_ids:
                    parent_id = str(parent_map.get(oid) or room_id)
                    children_by_parent[parent_id].append(oid)

                def assign_children(parent_id: str, center_x: float, center_y: float, level: int) -> None:
                    child_ids = children_by_parent.get(parent_id, [])
                    if not child_ids:
                        return
                    ordered_children = sorted(
                        child_ids,
                        key=lambda oid: (max(1, int(depth_map.get(oid, 1))), oid),
                    )
                    parent_radius = placed_radii.get(parent_id, object_boxes.get(parent_id, (0.0, 0.0, 20.0))[2])
                    for index, child_id in enumerate(ordered_children):
                        child_radius = object_boxes.get(child_id, (0.0, 0.0, 18.0))[2]
                        if parent_id != room_id:
                            # Keep children tightly anchored to their parent so contained objects do not drift across rooms.
                            slot_offsets = [
                                (0.0, -(parent_radius + child_radius + 16.0)),
                                (parent_radius + child_radius + 18.0, 0.0),
                                (0.0, parent_radius + child_radius + 16.0),
                                (-(parent_radius + child_radius + 18.0), 0.0),
                                (parent_radius + child_radius + 14.0, -(parent_radius + child_radius + 14.0)),
                                (parent_radius + child_radius + 14.0, parent_radius + child_radius + 14.0),
                                (-(parent_radius + child_radius + 14.0), parent_radius + child_radius + 14.0),
                                (-(parent_radius + child_radius + 14.0), -(parent_radius + child_radius + 14.0)),
                            ]
                            dx, dy = slot_offsets[index % len(slot_offsets)]
                            if index >= len(slot_offsets):
                                ring = index // len(slot_offsets) + 1
                                dx *= 1.0 + ring * 0.45
                                dy *= 1.0 + ring * 0.45
                            best_point = (center_x + dx, center_y + dy)
                            object_point_map[child_id] = best_point
                            placed_points[child_id] = best_point
                            placed_radii[child_id] = child_radius
                            continue
                        base_gap = 22.0 if parent_id == room_id else 14.0
                        base_radius = parent_radius + child_radius + base_gap
                        angle_offset = (sum(ord(ch) for ch in f"{parent_id}:{child_id}") % 360) * math.pi / 180.0
                        best_point = None
                        best_score = float("inf")
                        candidate_rings = [base_radius + 28.0 * step for step in range(5)]
                        candidate_angles = [
                            angle_offset + (2 * math.pi * step / 12.0) + (index * math.pi / 18.0)
                            for step in range(12)
                        ]
                        for radius in candidate_rings:
                            for angle in candidate_angles:
                                px = center_x + radius * math.cos(angle)
                                py = center_y + radius * math.sin(angle)
                                overlap_penalty = 0.0
                                nearest_gap = float("inf")
                                for other_id, (ox, oy) in placed_points.items():
                                    if other_id == parent_id:
                                        continue
                                    other_radius = placed_radii.get(other_id, 18.0)
                                    dist = math.hypot(px - ox, py - oy)
                                    gap = dist - (child_radius + other_radius)
                                    nearest_gap = min(nearest_gap, gap)
                                    if gap < 0:
                                        overlap_penalty += (-gap + 1.0) ** 2 * 1000.0
                                score = overlap_penalty + radius * 0.35 - min(nearest_gap, 0.0) * 0.5
                                if score < best_score:
                                    best_score = score
                                    best_point = (px, py)
                            if best_score < 1.0:
                                break
                        if best_point is None:
                            best_point = (center_x, center_y - base_radius)
                        object_point_map[child_id] = best_point
                        placed_points[child_id] = best_point
                        placed_radii[child_id] = child_radius
                    for child_id in ordered_children:
                        child_x, child_y = object_point_map[child_id]
                        assign_children(child_id, child_x, child_y, level + 1)

                assign_children(room_id, x, y, 1)
                for obj, label in zip(object_nodes, object_labels, strict=False):
                    obj_id = str(obj["id"])
                    ox, oy = object_point_map.get(obj_id, (x, y))
                    obj_layout = _normalize_rect_layout(obj.get("layout") or source_nodes.get(obj_id, {}).get("layout"))
                    if obj_layout:
                        ox = obj_layout["x"] + obj_layout["w"] / 2.0
                        oy = obj_layout["y"] + obj_layout["h"] / 2.0
                    obj_width, obj_height, _ = object_boxes[obj_id]
                    parent_id = str(parent_map.get(obj_id, room_id) or room_id)
                    viz_obj = copy.deepcopy(obj)
                    room_anchor_id = room_id
                    meta_parent_id = parent_id
                    if canonical_semantic_type(obj) == "door" and parent_id in room_ids:
                        runtime = copy.deepcopy(viz_obj.get("runtime") or {})
                        connected_rooms = [str(room_id) for room_id in (runtime.get("connected_rooms") or []) if str(room_id or "")]
                        if not connected_rooms:
                            connected_rooms = [parent_id]
                        runtime["connected_rooms"] = connected_rooms
                        if len(connected_rooms) > 1:
                            runtime["doorway_to"] = str(runtime.get("doorway_to") or connected_rooms[1])
                        runtime["door_anchor_room"] = parent_id
                        viz_obj["runtime"] = runtime
                        room_anchor_id = connected_rooms[0]
                        meta_parent_id = None
                        other_room = str(runtime.get("doorway_to") or "")
                        if other_room and other_room in room_centers:
                            ax, ay = room_centers.get(room_anchor_id, (x, y))
                            bx, by = room_centers[other_room]
                            ox = (ax + bx) / 2.0
                            oy = (ay + by) / 2.0
                    visible.add(obj_id)
                    floor_nodes.append(
                        {
                            "id": obj_id,
                            "label": label,
                            "kind": _node_family(obj),
                            "x": float(ox),
                            "y": float(oy),
                            "width": obj_width,
                            "height": obj_height,
                            "room_id": room_anchor_id,
                            "layout": obj_layout,
                            "meta": _node_meta(viz_obj, parent=meta_parent_id, child=obj.get("child") or []),
                        }
                    )
                    if obj_layout:
                        object_layouts.append(obj_layout)

            movable_rooms: dict[str, set[str]] = defaultdict(set)
            movable_targets: dict[str, set[str]] = defaultdict(set)
            controlled_movable_ids: set[str] = set()
            for edge in edges:
                source = str(edge.get("source_id") or "")
                target = str(edge.get("target_id") or "")
                source_type = _node_family(nodes.get(source, {})) if source in nodes else ""
                target_type = _node_family(nodes.get(target, {})) if target in nodes else ""
                source_room = source if source in room_ids else None
                target_room = target if target in room_ids else None

                if source_type == "movable" and _is_tool_like(nodes.get(source, {})) and target_room:
                    visible.add(source)
                    controlled_movable_ids.add(source)
                    movable_rooms[source].add(target_room)
                if target_type == "movable" and _is_tool_like(nodes.get(target, {})) and source_room:
                    visible.add(target)
                    controlled_movable_ids.add(target)
                    movable_rooms[target].add(source_room)
                if source_type == "movable" and _is_tool_like(nodes.get(source, {})) and target in visible:
                    visible.add(source)
                    controlled_movable_ids.add(source)
                if target_type == "movable" and _is_tool_like(nodes.get(target, {})) and source in visible:
                    visible.add(target)
                    controlled_movable_ids.add(target)
                if str(edge.get("relation") or "").lower() == "controls":
                    if source_type == "movable" and _is_tool_like(nodes.get(source, {})) and target in visible:
                        visible.add(source)
                        controlled_movable_ids.add(source)
                        movable_targets[source].add(target)
                    if target_type == "movable" and _is_tool_like(nodes.get(target, {})) and source in visible:
                        visible.add(target)
                        controlled_movable_ids.add(target)
                        movable_targets[target].add(source)

            for movable_id in controlled_movable_ids:
                linked_rooms = movable_rooms.get(movable_id, set())
                movable = nodes.get(movable_id)
                if not movable:
                    continue
                if any(node.get("id") == movable_id for node in floor_nodes):
                    continue
                target_ids = movable_targets.get(movable_id, set())
                target_nodes = [node for node in floor_nodes if node.get("id") in target_ids]
                if target_nodes:
                    base_x = sum(node["x"] for node in target_nodes) / len(target_nodes)
                    base_y = sum(node["y"] for node in target_nodes) / len(target_nodes) + 52.0
                else:
                    anchors = [room_centers[rid] for rid in linked_rooms if rid in room_centers]
                    if anchors:
                        base_x = sum(x for x, _ in anchors) / len(anchors)
                        base_y = min(y for _, y in room_centers.values()) - 170.0
                    else:
                        base_x, base_y = (0.0, -300.0)
                movable_width, movable_height, _ = _node_box(_item_label(movable), "movable")
                floor_nodes.append(
                    {
                        "id": movable_id,
                        "label": _item_label(movable),
                        "kind": "movable",
                        "x": float(base_x),
                        "y": float(base_y),
                        "width": movable_width,
                        "height": movable_height,
                        "layout": _normalize_rect_layout(movable.get("layout") or source_nodes.get(movable_id, {}).get("layout")),
                        "meta": _node_meta(movable, current_location=movable.get("current_location")),
                    }
                )
                movable_layout = _normalize_rect_layout(movable.get("layout") or source_nodes.get(movable_id, {}).get("layout"))
                if movable_layout:
                    object_layouts.append(movable_layout)

            seen = set()

            # 1. 先显式构造“房间/设施/可移动物体 -> 子物体”的层级边，保证结构可读
            for node in floor_nodes:
                if node.get("kind") not in {"fixture", "movable", "agent"}:
                    continue
                obj_id = str(node["id"])
                parent_id = str(node.get("meta", {}).get("parent") or node.get("room_id") or "")
                if not parent_id or parent_id not in visible:
                    continue
                runtime = (node.get("meta", {}) or {}).get("runtime") or {}
                connected_rooms = runtime.get("connected_rooms") or []
                is_room_door = bool(
                    str((node.get("meta", {}) or {}).get("semantic_type") or "").lower() == "door"
                    and isinstance(connected_rooms, list)
                    and len(connected_rooms) >= 2
                )
                if is_room_door:
                    continue

                key = (parent_id, obj_id, "contains")
                if key in seen:
                    continue
                seen.add(key)
                floor_edges.append(
                    {
                        "source": parent_id,
                        "target": obj_id,
                        "kind": "contains",
                        "meta": {
                            "relation": "contains",
                            "edge_type": "visual_room_object",
                            "category": "containment",
                            "properties": {
                                "visualized_from": "object_tree",
                                "depth": node.get("meta", {}).get("depth", 1),
                            },
                        },
                    }
                )

            # 2. 再补房间拓扑边、控制边和其他可见关系边
            for e in edges:
                s = str(e.get("source_id") or "")
                t = str(e.get("target_id") or "")
                if s not in visible or t not in visible:
                    continue
                kind = _edge_kind(e)
                if kind not in {"neighbor", "transport", "controls"}:
                    continue
                if kind in {"neighbor", "transport"}:
                    key = tuple(sorted((s, t))) + (kind,)
                else:
                    key = (s, t, kind)
                if key in seen:
                    continue
                seen.add(key)
                floor_edges.append(
                    {
                        "source": s,
                        "target": t,
                        "kind": kind,
                        "meta": {
                            "relation": str(e.get("relation") or ""),
                            "edge_type": str(e.get("edge_type") or ""),
                            "category": str(e.get("category") or ""),
                            "properties": e.get("properties") or {},
                        },
                    }
                )

            floorplan_bounds = floor_layout or _bounds_from_layouts(room_layouts or object_layouts)
            has_floorplan = bool(room_layouts)
            return {
                "floor_id": floor_id,
                "floor_name": next((f["name"] for f in floors if f["id"] == floor_id), floor_id),
                "node_count": len(floor_nodes),
                "edge_count": len(floor_edges),
                "layout_mode": "floorplan" if has_floorplan else "graph",
                "floorplan_bounds": floorplan_bounds,
                "nodes": floor_nodes,
                "edges": floor_edges,
            }

        floor_views = {f["id"]: build_floor(f["id"]) for f in floors}
        agent_floor = str(nodes.get(agent_room, {}).get("floor_id") or floor_by_room.get(agent_room) or floors[0]["id"] if floors else "")
        minutes_per_step = max(1, int(world_state.get("minutes_per_step") or 10))
        start_time_min = int(world_state.get("time_min") or 0)
        max_step = max(int(world_state.get("step") or 0), math.ceil((100 * 24 * 60) / minutes_per_step))
        scene_list = self.list_scenes(lang="en")
        scene_index = [x["id"] for x in scene_list].index(scene_id)
        payload = {
            "scene": scene_list[scene_index],
            "agent": {
                "id": agent.get("id"),
                "current_room": agent_room,
                "current_floor": agent_floor,
                "inventory": agent.get("inventory", []),
            },
            "floors": floors,
            "current_floor": agent_floor,
            "floor_views": floor_views,
            "timeline": {
                "day": int(world_state.get("day") or 1),
                "weekday_index": int(world_state.get("weekday_index") or 0),
                "weekday_name": str(world_state.get("weekday_name") or "monday"),
                "weekday_name_cn": str(world_state.get("weekday_name_cn") or "周一"),
                "week_index": int(world_state.get("week_index") or 1),
                "season_index": int(world_state.get("season_index") or 0),
                "season_name": str(world_state.get("season_name") or "spring"),
                "season_name_cn": str(world_state.get("season_name_cn") or "春"),
                "season_week": int(world_state.get("season_week") or 1),
                "day_of_season": int(world_state.get("day_of_season") or 1),
                "weather": str(world_state.get("weather") or "sunny"),
                "collapse_stage": str(world_state.get("collapse_stage") or "stable"),
                "entropy": float(world_state.get("entropy") or 0.0),
                "current_step": int(world_state.get("step") or 0),
                "start_time_min": start_time_min,
                "minutes_per_step": minutes_per_step,
                "max_step": max_step,
            },
            "scene_metrics": metrics,
            "world_metrics": metrics.get("world_metrics") or {},
            "role_metrics": metrics.get("role_metrics") or {},
            "top_issues": metrics.get("top_issues") or [],
        }
        if lang == "cn":
            payload = self._localize_payload_from_cn_fields(payload)
        return payload

    def list_replays(self) -> list[dict]:
        return self.replays.list_replays()

    def get_replay(self, replay_id: str) -> dict | None:
        return self.replays.get_replay(replay_id)

    def get_replay_metrics(self, replay_id: str) -> dict | None:
        return self.replays.get_replay_metrics(replay_id)

    def get_replay_summary(self, replay_id: str) -> dict | None:
        return self.replays.get_replay_summary(replay_id)

    def get_replay_step(self, replay_id: str, step_index: int) -> dict | None:
        return self.replays.get_replay_step(replay_id, step_index)

    def get_replay_telemetry(self, replay_id: str) -> dict | None:
        payload = self.replays.get_replay_summary(replay_id)
        if not payload:
            return None
        summary = payload.get("summary") or {}
        return {
            "replay_id": str(payload.get("replay_id") or replay_id),
            "scene_id": str(payload.get("scene_id") or ""),
            "run_name": str(summary.get("run_name") or ""),
            "tensorboard_log_dir": str(summary.get("tensorboard_log_dir") or ""),
            "experiment_type": str(summary.get("experiment_type") or ""),
            "experiment_label": str(summary.get("experiment_label") or ""),
            "step_count": int(summary.get("step_count") or 0),
        }

    def run_replay(
        self,
        scene_id: str,
        *,
        task: dict | str | None = None,
        agent_id: str = "robot_01",
        agent_model: str = "local-qwen3.5-35b",
        timeout: int = 30,
        enable_search: bool = False,
        image_path: str | None = None,
        max_days: float = 1.5,
        experiment_type: str | None = None,
    ) -> dict | None:
        item = self.scenes.get(scene_id)
        if not item:
            return None
        raw_source = copy.deepcopy(item["raw"])
        return self.replays.run_and_save_replay(
            scene_id,
            raw_source,
            task=task,
            agent_id=agent_id,
            agent_model=agent_model,
            timeout=timeout,
            enable_search=enable_search,
            image_path=image_path,
            max_days=max_days,
            experiment_type=experiment_type,
        )

    def start_human_session(
        self,
        scene_id: str,
        *,
        agent_id: str = "robot_01",
    ) -> dict | None:
        item = self.scenes.get(scene_id)
        if not item:
            return None
        return self.human_sessions.start_session(scene_id, copy.deepcopy(item["raw"]), agent_id=agent_id)

    def get_human_session(self, session_id: str) -> dict | None:
        return self.human_sessions.get_session(session_id)

    def get_human_session_scene_view(self, session_id: str) -> dict | None:
        payload = self.human_sessions.get_session(session_id)
        if not payload:
            return None
        current_step = payload.get("current_step") or {}
        scene_view = current_step.get("memory_scene") or current_step.get("scene")
        if not isinstance(scene_view, dict):
            return None
        return {
            "session_id": str(payload.get("session_id") or session_id),
            "scene_id": str(payload.get("scene_id") or ""),
            "episode_step": int((current_step.get("episode_step") or 0)),
            "scene_view": copy.deepcopy(scene_view),
        }

    def apply_human_action(self, session_id: str, action: dict) -> dict | None:
        return self.human_sessions.apply_action(session_id, action)

    def end_human_session(self, session_id: str, reason: str = "human_stopped") -> dict | None:
        return self.human_sessions.end_session(session_id, reason=reason)

    def _localize_payload_from_cn_fields(self, payload: dict) -> dict:
        localized = copy.deepcopy(payload)
        room_label_by_id: dict[str, str] = {}
        raw = self.scenes.get(localized["scene"]["id"], {}).get("raw", {})
        raw_nodes_by_id = {str(n.get("id")): n for n in raw.get("nodes", []) if isinstance(n, dict) and n.get("id")}
        localized["scene"]["name"] = raw.get("scene_name_cn") or localized["scene"]["name"]
        for floor in localized.get("floors", []):
            floor_node = raw_nodes_by_id.get(str(floor["id"]), {})
            floor["name"] = floor_node.get("name_cn") or _floor_name_cn(floor["name"])
        for view in localized.get("floor_views", {}).values():
            floor_node = raw_nodes_by_id.get(str(view["floor_id"]), {})
            view["floor_name"] = floor_node.get("name_cn") or _floor_name_cn(view["floor_name"])
            for node in view.get("nodes", []):
                raw_node = raw_nodes_by_id.get(str(node["id"]), {})
                node["label"] = raw_node.get("label_cn") or raw_node.get("name_cn") or node["label"]
                if node.get("kind") == "room":
                    room_label_by_id[node["id"]] = node["label"]
                node["meta"] = self._localize_meta_from_cn_fields(node.get("meta") or {}, raw_node)
            for node in view.get("nodes", []):
                if node.get("room_id"):
                    room_raw = raw_nodes_by_id.get(str(node["room_id"]), {})
                    node["room_label"] = room_label_by_id.get(node["room_id"], room_raw.get("label_cn") or room_raw.get("name_cn") or node["room_id"])
            for edge in view.get("edges", []):
                edge["meta"] = edge.get("meta") or {}
        if localized.get("agent", {}).get("current_room"):
            current_room = localized["agent"]["current_room"]
            room_raw = raw_nodes_by_id.get(str(current_room), {})
            localized["agent"]["current_room_label"] = room_label_by_id.get(current_room, room_raw.get("label_cn") or room_raw.get("name_cn") or current_room)
        return localized

    def _localize_meta_from_cn_fields(self, value, raw_node: dict | None = None):
        if value is None:
            return value
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                if str(k) == "object_type" and raw_node and raw_node.get("object_type_cn"):
                    out[str(k)] = raw_node["object_type_cn"]
                else:
                    out[str(k)] = self._localize_meta_from_cn_fields(v, raw_node)
            return out
        if isinstance(value, list):
            return [self._localize_meta_from_cn_fields(item, raw_node) for item in value]
        return value
