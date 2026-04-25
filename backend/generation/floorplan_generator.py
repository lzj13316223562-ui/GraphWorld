from __future__ import annotations

import json
import math
import random
from copy import deepcopy
from pathlib import Path
from typing import Any

from backend.core import FloorplanTemplate, RoomTypeSpec, get_home_floorplan_template, get_room_type_spec
from backend.runtime.schema.home_schema import set_scene_graph


HOME_ROOM_OBJECTS: dict[str, list[dict[str, Any]]] = {
    "entrance": [
        {"id": "bench_entrance", "semantic_type": "seat", "node_type": "fixed_object", "parent": "entrance", "placement_mode": "wall", "preferred_zone": "south"},
        {"id": "shoe_rack_entrance", "semantic_type": "shoe_rack", "node_type": "fixed_object", "parent": "entrance", "placement_mode": "wall", "preferred_zone": "west", "clearance_required": 0.35},
        {"id": "shoes_entrance_1", "semantic_type": "shoes", "node_type": "movable_object", "parent": "shoe_rack_entrance", "placement_mode": "inside"},
        {"id": "shoes_entrance_2", "semantic_type": "shoes", "node_type": "movable_object", "parent": "shoe_rack_entrance", "placement_mode": "inside"},
        {"id": "shoes_entrance_3", "semantic_type": "shoes", "node_type": "movable_object", "parent": "shoe_rack_entrance", "placement_mode": "inside"},
    ],
    "living_room": [
        {"id": "coffee_table_living_room", "semantic_type": "coffee_table", "node_type": "fixed_object", "parent": "living_room", "placement_mode": "paired_front", "pair_with": "sofa_living_room"},
        {"id": "sofa_living_room", "semantic_type": "sofa", "node_type": "fixed_object", "parent": "living_room", "placement_mode": "anchor", "preferred_zone": "west", "clearance_required": 0.7},
        {"id": "trash_bin_living_room", "semantic_type": "trash_bin", "node_type": "fixed_object", "parent": "living_room", "placement_mode": "corner", "preferred_zone": "southeast"},
        {"id": "tv_living_room", "semantic_type": "tv", "node_type": "fixed_object", "parent": "living_room", "placement_mode": "paired_opposite", "pair_with": "sofa_living_room"},
        {"id": "air_conditioner_living_room", "semantic_type": "air_conditioner", "node_type": "fixed_object", "parent": "living_room", "placement_mode": "wall", "preferred_zone": "north"},
    ],
    "kitchen": [
        {"id": "counter_kitchen", "semantic_type": "counter", "node_type": "fixed_object", "parent": "kitchen", "placement_mode": "anchor", "preferred_zone": "north", "clearance_required": 0.75},
        {"id": "sink_kitchen", "semantic_type": "sink", "node_type": "fixed_object", "parent": "kitchen", "placement_mode": "paired_on_surface", "pair_with": "counter_kitchen", "preferred_zone": "left"},
        {"id": "faucet_kitchen", "semantic_type": "faucet", "node_type": "fixed_object", "parent": "kitchen", "placement_mode": "attached", "pair_with": "sink_kitchen"},
        {"id": "fridge_kitchen", "semantic_type": "fridge", "node_type": "fixed_object", "parent": "kitchen", "placement_mode": "wall", "preferred_zone": "west"},
        {"id": "milk_fridge_kitchen", "semantic_type": "milk", "node_type": "movable_object", "parent": "fridge_kitchen", "placement_mode": "inside"},
        {"id": "juice_fridge_kitchen", "semantic_type": "juice", "node_type": "movable_object", "parent": "fridge_kitchen", "placement_mode": "inside"},
        {"id": "vegetable_fridge_kitchen", "semantic_type": "vegetable", "node_type": "movable_object", "parent": "fridge_kitchen", "placement_mode": "inside"},
        {"id": "dishwasher_kitchen", "semantic_type": "dishwasher", "node_type": "fixed_object", "parent": "kitchen", "placement_mode": "paired_under", "pair_with": "counter_kitchen", "preferred_zone": "left"},
        {"id": "bowls_dishwasher_kitchen", "semantic_type": "bowl", "node_type": "movable_object", "parent": "dishwasher_kitchen", "placement_mode": "inside"},
        {"id": "microwave_kitchen", "semantic_type": "microwave", "node_type": "fixed_object", "parent": "kitchen", "placement_mode": "paired_on_surface", "pair_with": "counter_kitchen", "preferred_zone": "center"},
        {"id": "stove_kitchen", "semantic_type": "stove", "node_type": "fixed_object", "parent": "kitchen", "placement_mode": "paired_on_surface", "pair_with": "counter_kitchen", "preferred_zone": "right"},
    ],
    "bedroom": [
        {"id": "bed_bedroom", "semantic_type": "bed", "node_type": "fixed_object", "parent": "bedroom", "placement_mode": "anchor", "preferred_zone": "west", "clearance_required": 0.75},
        {"id": "wardrobe_bedroom", "semantic_type": "wardrobe", "node_type": "fixed_object", "parent": "bedroom", "placement_mode": "wall", "preferred_zone": "east"},
        {"id": "clothes_bedroom_1", "semantic_type": "clothes", "node_type": "movable_object", "parent": "wardrobe_bedroom", "placement_mode": "inside"},
        {"id": "clothes_bedroom_2", "semantic_type": "clothes", "node_type": "movable_object", "parent": "wardrobe_bedroom", "placement_mode": "inside"},
        {"id": "clothes_bedroom_3", "semantic_type": "clothes", "node_type": "movable_object", "parent": "wardrobe_bedroom", "placement_mode": "inside"},
        {"id": "desk_bedroom", "semantic_type": "desk", "node_type": "fixed_object", "parent": "bedroom", "placement_mode": "wall", "preferred_zone": "southwest"},
        {"id": "desk_drawer_bedroom", "semantic_type": "drawer", "node_type": "fixed_object", "parent": "desk_bedroom", "placement_mode": "attached"},
        {"id": "book_bedroom", "semantic_type": "book", "node_type": "movable_object", "parent": "desk_bedroom", "placement_mode": "surface"},
        {"id": "air_conditioner_bedroom", "semantic_type": "air_conditioner", "node_type": "fixed_object", "parent": "bedroom", "placement_mode": "wall", "preferred_zone": "north"},
    ],
    "bathroom": [
        {"id": "sink_bathroom", "semantic_type": "sink", "node_type": "fixed_object", "parent": "bathroom", "placement_mode": "wall", "preferred_zone": "west"},
        {"id": "faucet_bathroom", "semantic_type": "faucet", "node_type": "fixed_object", "parent": "bathroom", "placement_mode": "attached", "pair_with": "sink_bathroom"},
        {"id": "toilet_bathroom", "semantic_type": "toilet", "node_type": "fixed_object", "parent": "bathroom", "placement_mode": "wall", "preferred_zone": "east"},
        {"id": "toilet_brush_bathroom", "semantic_type": "toilet_brush", "node_type": "movable_object", "parent": "bathroom", "placement_mode": "nearby", "pair_with": "toilet_bathroom"},
        {"id": "washer_bathroom", "semantic_type": "washer", "node_type": "fixed_object", "parent": "bathroom", "placement_mode": "wall", "preferred_zone": "north"},
        {"id": "cup_bathroom", "semantic_type": "cup", "node_type": "movable_object", "parent": "sink_bathroom", "placement_mode": "surface"},
        {"id": "toothbrush_bathroom", "semantic_type": "toothbrush", "node_type": "movable_object", "parent": "sink_bathroom", "placement_mode": "surface"},
    ],
    "balcony": [
        {"id": "chair_balcony", "semantic_type": "chair", "node_type": "fixed_object", "parent": "balcony", "placement_mode": "free", "preferred_zone": "west"},
        {"id": "plant_balcony", "semantic_type": "plant", "node_type": "fixed_object", "parent": "balcony", "placement_mode": "corner", "preferred_zone": "east"},
    ],
}


DEVICE_CONTROLS: list[dict[str, str]] = [
    {"parent": "dishwasher_kitchen", "child_id": "dishwasher_kitchen_door", "semantic_type": "door"},
    {"parent": "dishwasher_kitchen", "child_id": "dishwasher_kitchen_button", "semantic_type": "button", "controls": "dishwasher_kitchen"},
    {"parent": "microwave_kitchen", "child_id": "microwave_kitchen_door", "semantic_type": "door"},
    {"parent": "microwave_kitchen", "child_id": "microwave_kitchen_button", "semantic_type": "button", "controls": "microwave_kitchen"},
    {"parent": "stove_kitchen", "child_id": "stove_kitchen_knob", "semantic_type": "knob", "controls": "stove_kitchen"},
    {"parent": "washer_bathroom", "child_id": "washer_bathroom_door", "semantic_type": "door"},
    {"parent": "washer_bathroom", "child_id": "washer_bathroom_button", "semantic_type": "button", "controls": "washer_bathroom"},
    {"parent": "fridge_kitchen", "child_id": "door_fridge_kitchen", "semantic_type": "door"},
]


EPS = 1e-6
DEFAULT_SEED = 7


def _base_node(
    node_id: str,
    name: str,
    name_cn: str,
    node_type: str,
    semantic_class: str,
    semantic_type: str,
    mobility: str,
    parent: str | None,
    interactive_actions: list[str],
    states: dict[str, Any] | None = None,
    child: list[str] | None = None,
    affordance_count: int = 0,
    **extra: Any,
) -> dict[str, Any]:
    node = {
        "id": node_id,
        "name": name,
        "name_cn": name_cn,
        "node_type": node_type,
        "semantic_class": semantic_class,
        "semantic_type": semantic_type,
        "mobility": mobility,
        "states": states or {},
        "property": {
            "appearance": "",
            "physical": "",
            "operation": "",
        },
        "affordance_count": affordance_count,
        "parent": parent,
        "child": child or [],
        "interactive_actions": interactive_actions,
    }
    node.update(extra)
    return node


def _midpoint(value_range: tuple[int, int]) -> float:
    return (float(value_range[0]) + float(value_range[1])) / 2.0


def _sample_room_size(spec: RoomTypeSpec, rng: random.Random) -> tuple[float, float]:
    area_mid = _midpoint(spec.area_range)
    area_span = max(0.4, (spec.area_range[1] - spec.area_range[0]) * 0.18)
    sampled_area = max(float(spec.area_range[0]), min(float(spec.area_range[1]), area_mid + rng.uniform(-area_span, area_span)))
    aspect_mid = (float(spec.aspect_ratio_range[0]) + float(spec.aspect_ratio_range[1])) / 2.0
    aspect_span = max(0.08, (spec.aspect_ratio_range[1] - spec.aspect_ratio_range[0]) * 0.22)
    sampled_aspect = max(float(spec.aspect_ratio_range[0]), min(float(spec.aspect_ratio_range[1]), aspect_mid + rng.uniform(-aspect_span, aspect_span)))
    width = math.sqrt(sampled_area * sampled_aspect)
    height = sampled_area / max(width, EPS)
    width = max(width, spec.min_wall_length)
    height = max(height, spec.min_wall_length)
    return round(width, 2), round(height, 2)


def _offset_for_token(anchor: dict[str, float], width: float, height: float, token: str) -> tuple[float, float]:
    ax = float(anchor["x"])
    ay = float(anchor["y"])
    aw = float(anchor["w"])
    ah = float(anchor["h"])
    cx = ax + aw / 2.0
    cy = ay + ah / 2.0

    def along_vertical(mode: str) -> float:
        if mode == "north":
            return ay
        if mode == "south":
            return ay + ah - height
        return cy - height / 2.0

    def along_horizontal(mode: str) -> float:
        if mode == "west":
            return ax
        if mode == "east":
            return ax + aw - width
        return cx - width / 2.0

    primary, _, secondary = token.partition("_")
    if primary == "west":
        return round(ax - width, 2), round(along_vertical(secondary), 2)
    if primary == "east":
        return round(ax + aw, 2), round(along_vertical(secondary), 2)
    if primary == "north":
        return round(along_horizontal(secondary), 2), round(ay - height, 2)
    if primary == "south":
        return round(along_horizontal(secondary), 2), round(ay + ah, 2)
    return round(ax + aw, 2), round(cy - height / 2.0, 2)


def _overlap_1d(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _rects_overlap(a: dict[str, float], b: dict[str, float]) -> bool:
    return _overlap_1d(a["x"], a["x"] + a["w"], b["x"], b["x"] + b["w"]) > EPS and _overlap_1d(a["y"], a["y"] + a["h"], b["y"], b["y"] + b["h"]) > EPS


def _place_room(
    room_id: str,
    token: str,
    width: float,
    height: float,
    anchor_id: str,
    rects: dict[str, dict[str, float]],
) -> dict[str, float]:
    anchor = rects[anchor_id]
    rect = {"x": 0.0, "y": 0.0, "w": width, "h": height}
    x, y = _offset_for_token(anchor, width, height, token)
    rect.update({"x": x, "y": y, "w": width, "h": height})
    attempts = 0
    while any(_rects_overlap(rect, other) for other_id, other in rects.items() if other_id != anchor_id) and attempts < 20:
        if token.startswith(("east", "west")):
            rect["y"] = round(rect["y"] + 0.55, 2)
        else:
            rect["x"] = round(rect["x"] + 0.55, 2)
        attempts += 1
    rect["x"] = round(rect["x"], 2)
    rect["y"] = round(rect["y"], 2)
    return rect


def _room_anchor(template: FloorplanTemplate, room_id: str, placed: dict[str, dict[str, float]]) -> str:
    required = list(template.required_edges) + list(template.optional_edges)
    for left, right in required:
        if left == room_id and right in placed:
            return right
        if right == room_id and left in placed:
            return left
    if template.hub_room and template.hub_room in placed:
        return template.hub_room
    return next(iter(placed))


def generate_room_rect_layout(template_name: str, *, seed: int = DEFAULT_SEED) -> dict[str, dict[str, float]]:
    template = get_home_floorplan_template(template_name)
    if template is None:
        raise ValueError(f"Unknown home floorplan template: {template_name}")
    rng = random.Random(f"{template_name}:{seed}")
    room_order = list(template.room_order_hint or template.room_types)
    hub = template.hub_room or room_order[0]
    rects: dict[str, dict[str, float]] = {}

    hub_spec = get_room_type_spec(hub)
    if hub_spec is None:
        raise ValueError(f"Unknown hub room type: {hub}")
    hub_w, hub_h = _sample_room_size(hub_spec, rng)
    rects[hub] = {"x": 0.0, "y": 0.0, "w": hub_w, "h": hub_h}

    for room_id in room_order:
        if room_id == hub:
            continue
        spec = get_room_type_spec(room_id)
        if spec is None:
            raise ValueError(f"Unknown room type: {room_id}")
        width, height = _sample_room_size(spec, rng)
        token = str(template.room_positions_hint.get(room_id) or "east")
        anchor_id = _room_anchor(template, room_id, rects)
        rects[room_id] = _place_room(room_id, token, width, height, anchor_id, rects)

    min_x = min(rect["x"] for rect in rects.values())
    min_y = min(rect["y"] for rect in rects.values())
    for rect in rects.values():
        rect["x"] = round(rect["x"] - min_x + 0.5, 2)
        rect["y"] = round(rect["y"] - min_y + 0.5, 2)
    return rects


def _shared_wall(a: dict[str, float], b: dict[str, float]) -> dict[str, float] | None:
    ax0, ay0, ax1, ay1 = a["x"], a["y"], a["x"] + a["w"], a["y"] + a["h"]
    bx0, by0, bx1, by1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]

    if abs(ax1 - bx0) < EPS or abs(bx1 - ax0) < EPS:
        overlap = _overlap_1d(ay0, ay1, by0, by1)
        if overlap > 0.6:
            y0 = max(ay0, by0)
            return {
                "orientation": "vertical",
                "x": round(bx0 if abs(ax1 - bx0) < EPS else ax0, 2),
                "y": round(y0 + overlap / 2.0, 2),
                "length": round(overlap, 2),
            }
    if abs(ay1 - by0) < EPS or abs(by1 - ay0) < EPS:
        overlap = _overlap_1d(ax0, ax1, bx0, bx1)
        if overlap > 0.6:
            x0 = max(ax0, bx0)
            return {
                "orientation": "horizontal",
                "x": round(x0 + overlap / 2.0, 2),
                "y": round(by0 if abs(ay1 - by0) < EPS else ay0, 2),
                "length": round(overlap, 2),
            }
    return None


def _derive_adjacency(template: FloorplanTemplate, rects: dict[str, dict[str, float]]) -> tuple[list[tuple[str, str]], dict[str, list[dict[str, Any]]]]:
    adjacency: list[tuple[str, str]] = []
    doorways: dict[str, list[dict[str, Any]]] = {room_id: [] for room_id in rects}
    template_pairs = {tuple(sorted(edge)) for edge in list(template.required_edges) + list(template.optional_edges)}
    room_ids = list(rects)

    for i, left in enumerate(room_ids):
        for right in room_ids[i + 1 :]:
            pair = tuple(sorted((left, right)))
            if pair not in template_pairs:
                continue
            shared = _shared_wall(rects[left], rects[right])
            if not shared:
                continue
            adjacency.append((left, right))
            door_width = round(min(1.1, max(0.8, shared["length"] * 0.35)), 2)
            left_rec = {"target_room": right, "width": door_width, **shared}
            right_rec = {"target_room": left, "width": door_width, **shared}
            doorways[left].append(left_rec)
            doorways[right].append(right_rec)

    missing = [edge for edge in template.required_edges if tuple(sorted(edge)) not in {tuple(sorted(x)) for x in adjacency}]
    if missing:
        raise ValueError(f"Failed to realize required room adjacencies: {missing}")
    return adjacency, doorways


def _room_node(room_id: str, spec: RoomTypeSpec, rect: dict[str, float], doorways: list[dict[str, Any]]) -> dict[str, Any]:
    return _base_node(
        node_id=room_id,
        name=spec.room_type.replace("_", " ").title(),
        name_cn=spec.display_name_cn,
        node_type="room",
        semantic_class="space",
        semantic_type="room",
        mobility="fixed",
        parent=None,
        interactive_actions=["move", "place", "scan"],
        states={"temperature": 24.0},
        layout={**deepcopy(rect), "doorways": deepcopy(doorways)},
    )


def _fixture_name(semantic_type: str) -> tuple[str, str]:
    name_map = {
        "door": ("door", "门"),
        "light": ("light", "灯"),
        "button": ("button", "按钮"),
        "bench": ("bench", "长凳"),
        "shoe_rack": ("shoe rack", "鞋架"),
        "coffee_table": ("coffee table", "茶几"),
        "sofa": ("sofa", "沙发"),
        "trash_bin": ("trash bin", "垃圾桶"),
        "tv": ("tv", "电视"),
        "counter": ("counter", "操作台"),
        "sink": ("sink", "洗手池"),
        "faucet": ("faucet", "水龙头"),
        "fridge": ("fridge", "冰箱"),
        "dishwasher": ("dishwasher", "洗碗机"),
        "microwave": ("microwave", "微波炉"),
        "stove": ("stove", "炉灶"),
        "bed": ("bed", "床"),
        "wardrobe": ("wardrobe", "衣柜"),
        "desk": ("desk", "书桌"),
        "drawer": ("drawer", "抽屉"),
        "toilet": ("toilet", "马桶"),
        "washer": ("washer", "洗衣机"),
        "chair": ("chair", "椅子"),
        "plant": ("plant", "盆栽"),
        "toilet_brush": ("toilet brush", "马桶刷"),
        "bowl": ("bowl", "碗"),
        "book": ("book", "书"),
        "cup": ("cup", "杯子"),
        "toothbrush": ("toothbrush", "牙刷"),
        "milk": ("milk", "牛奶"),
        "juice": ("juice", "果汁"),
        "vegetable": ("vegetable", "蔬菜"),
        "fruit": ("fruit", "水果"),
        "clothes": ("clothes", "衣服"),
        "shoes": ("shoes", "鞋"),
        "knob": ("knob", "旋钮"),
        "air_conditioner": ("air conditioner", "空调"),
        "seat": ("seat", "座椅"),
    }
    return name_map.get(semantic_type, (semantic_type.replace("_", " "), semantic_type))


def _interactive_actions(node_type: str, semantic_type: str) -> list[str]:
    if node_type == "room":
        return ["move", "place", "scan"]
    if semantic_type in {"door", "window", "drawer", "wardrobe", "cabinet"}:
        return ["move", "scan", "open", "close"]
    if semantic_type in {"button", "knob", "faucet", "air_conditioner"}:
        return ["move", "press", "scan"]
    if node_type == "movable_object":
        return ["pick", "scan"]
    if semantic_type in {"sink", "toilet", "counter", "bowl", "plate", "cup", "cloth", "brush", "toilet_brush"}:
        return ["move", "scan", "brush"]
    return ["move", "scan"]


def _semantic_class(semantic_type: str, node_type: str) -> str:
    if node_type == "room":
        return "space"
    class_map = {
        "door": "control",
        "button": "control",
        "knob": "control",
        "light": "appliance",
        "seat": "furniture",
        "bench": "furniture",
        "shoe_rack": "container",
        "coffee_table": "furniture",
        "sofa": "furniture",
        "trash_bin": "container",
        "tv": "appliance",
        "counter": "furniture",
        "sink": "appliance",
        "faucet": "appliance",
        "air_conditioner": "appliance",
        "fridge": "appliance",
        "dishwasher": "appliance",
        "microwave": "appliance",
        "stove": "appliance",
        "bed": "furniture",
        "wardrobe": "container",
        "desk": "furniture",
        "drawer": "container",
        "toilet": "appliance",
        "washer": "appliance",
        "chair": "furniture",
        "plant": "furniture",
        "toilet_brush": "tool",
        "bowl": "consumable",
        "book": "personal_item",
        "cup": "consumable",
        "toothbrush": "personal_item",
        "milk": "consumable",
        "juice": "consumable",
        "vegetable": "consumable",
        "fruit": "consumable",
        "clothes": "personal_item",
        "shoes": "personal_item",
    }
    return class_map.get(semantic_type, "tool")


def _default_states(semantic_type: str) -> dict[str, Any]:
    if semantic_type in {"door", "wardrobe", "drawer", "fridge", "dishwasher", "microwave", "washer"}:
        return {"is_open": False}
    if semantic_type in {"button", "knob"}:
        return {"is_on": False, "is_pressed": False}
    if semantic_type in {"light", "faucet", "stove", "dishwasher", "microwave", "washer"}:
        return {"is_on": False}
    if semantic_type == "air_conditioner":
        return {"is_on": False, "target_temperature": 24.0, "mode": "cool", "fan_level": 2}
    if semantic_type in {"trash_bin", "sink"}:
        return {"fill_level": 0.0, "is_full": False}
    if semantic_type in {"milk", "juice", "vegetable", "fruit"}:
        return {"freshness": 1.0, "temperature": "room", "is_cooked": False, "is_rotten": False}
    if semantic_type in {"clothes", "shoes"}:
        return {"is_dirty": False, "is_wet": False, "is_dry": True}
    if semantic_type in {"bowl", "cup"}:
        return {"is_dirty": False, "is_wet": False, "is_dry": True, "is_clean": True}
    if semantic_type == "toilet":
        return {"cleanliness": 0.92, "is_dirty": False}
    if semantic_type == "plant":
        return {"vitality": 1.0, "is_wilted": False}
    return {}


def _affordance_count(semantic_type: str) -> int:
    counts = {
        "shoe_rack": 6,
        "wardrobe": 8,
        "drawer": 4,
        "counter": 4,
        "trash_bin": 8,
        "sink": 4,
        "fridge": 10,
        "washer": 5,
        "dishwasher": 8,
        "coffee_table": 4,
        "desk": 5,
    }
    return counts.get(semantic_type, 0)


def _box_size(semantic_type: str) -> tuple[float, float]:
    return {
        "bed": (2.0, 1.6),
        "sofa": (1.8, 0.9),
        "coffee_table": (1.0, 0.6),
        "tv": (0.4, 1.1),
        "counter": (2.0, 0.7),
        "fridge": (0.8, 0.8),
        "dishwasher": (0.7, 0.7),
        "microwave": (0.6, 0.4),
        "stove": (0.9, 0.7),
        "wardrobe": (1.3, 0.6),
        "desk": (1.2, 0.6),
        "sink": (0.8, 0.55),
        "washer": (0.8, 0.8),
        "toilet": (0.7, 0.9),
        "shoe_rack": (1.2, 0.35),
        "seat": (0.9, 0.4),
        "chair": (0.7, 0.7),
        "plant": (0.55, 0.55),
        "trash_bin": (0.45, 0.45),
        "light": (0.35, 0.35),
        "button": (0.18, 0.18),
        "door": (0.95, 0.18),
        "air_conditioner": (0.95, 0.28),
    }.get(semantic_type, (0.36, 0.36))


def _anchor_fraction(semantic_type: str) -> tuple[float, float]:
    return {
        "air_conditioner": (0.5, 0.08),
        "sofa": (0.28, 0.62),
        "coffee_table": (0.50, 0.58),
        "tv": (0.84, 0.53),
        "trash_bin": (0.88, 0.86),
        "bed": (0.48, 0.30),
        "wardrobe": (0.84, 0.22),
        "desk": (0.22, 0.78),
        "counter": (0.50, 0.16),
        "sink": (0.18, 0.18),
        "faucet": (0.18, 0.08),
        "fridge": (0.12, 0.58),
        "dishwasher": (0.34, 0.18),
        "microwave": (0.62, 0.16),
        "stove": (0.82, 0.16),
        "toilet": (0.78, 0.58),
        "washer": (0.80, 0.18),
        "shoe_rack": (0.20, 0.24),
        "seat": (0.36, 0.78),
        "chair": (0.38, 0.56),
        "plant": (0.72, 0.34),
        "door": (0.50, 0.50),
        "button": (0.62, 0.50),
    }.get(semantic_type, (0.50, 0.50))


def _layout_rect(x: float, y: float, w: float, h: float) -> dict[str, float]:
    return {"x": round(x, 2), "y": round(y, 2), "w": round(w, 2), "h": round(h, 2)}


def _clamp_rect_to_room(rect: dict[str, float], room_rect: dict[str, float], margin: float = 0.08) -> dict[str, float]:
    x = min(max(rect["x"], room_rect["x"] + margin), room_rect["x"] + room_rect["w"] - rect["w"] - margin)
    y = min(max(rect["y"], room_rect["y"] + margin), room_rect["y"] + room_rect["h"] - rect["h"] - margin)
    return _layout_rect(x, y, rect["w"], rect["h"])


def _center_of(rect: dict[str, float]) -> tuple[float, float]:
    return rect["x"] + rect["w"] / 2.0, rect["y"] + rect["h"] / 2.0


def _expand_rect(rect: dict[str, float], clearance: float) -> dict[str, float]:
    if clearance <= 0:
        return rect
    return {
        "x": rect["x"] - clearance,
        "y": rect["y"] - clearance,
        "w": rect["w"] + clearance * 2,
        "h": rect["h"] + clearance * 2,
    }


def _zone_point(room_rect: dict[str, float], zone: str | None) -> tuple[float, float]:
    zone = str(zone or "center").lower()
    rx, ry, rw, rh = room_rect["x"], room_rect["y"], room_rect["w"], room_rect["h"]
    points = {
        "center": (rx + rw * 0.5, ry + rh * 0.5),
        "north": (rx + rw * 0.5, ry + rh * 0.18),
        "south": (rx + rw * 0.5, ry + rh * 0.82),
        "west": (rx + rw * 0.18, ry + rh * 0.5),
        "east": (rx + rw * 0.82, ry + rh * 0.5),
        "northwest": (rx + rw * 0.2, ry + rh * 0.22),
        "northeast": (rx + rw * 0.8, ry + rh * 0.22),
        "southwest": (rx + rw * 0.2, ry + rh * 0.78),
        "southeast": (rx + rw * 0.8, ry + rh * 0.78),
        "left": (rx + rw * 0.3, ry + rh * 0.5),
        "right": (rx + rw * 0.7, ry + rh * 0.5),
    }
    return points.get(zone, points["center"])


def _candidate_rects(room_rect: dict[str, float], width: float, height: float, preferred_zone: str | None, placement_mode: str) -> list[dict[str, float]]:
    rx, ry, rw, rh = room_rect["x"], room_rect["y"], room_rect["w"], room_rect["h"]
    margin = 0.1
    cx, cy = _zone_point(room_rect, preferred_zone)
    centered = _layout_rect(cx - width / 2.0, cy - height / 2.0, width, height)

    wall_candidates = {
        "west": _layout_rect(rx + margin, cy - height / 2.0, width, height),
        "east": _layout_rect(rx + rw - width - margin, cy - height / 2.0, width, height),
        "north": _layout_rect(cx - width / 2.0, ry + margin, width, height),
        "south": _layout_rect(cx - width / 2.0, ry + rh - height - margin, width, height),
        "northwest": _layout_rect(rx + margin, ry + margin, width, height),
        "northeast": _layout_rect(rx + rw - width - margin, ry + margin, width, height),
        "southwest": _layout_rect(rx + margin, ry + rh - height - margin, width, height),
        "southeast": _layout_rect(rx + rw - width - margin, ry + rh - height - margin, width, height),
    }

    candidates: list[dict[str, float]] = []
    if placement_mode in {"anchor", "wall", "corner"}:
        ordered_zones = [preferred_zone or "west", "south", "east", "north", "southwest", "southeast", "northwest", "northeast"]
        for zone in ordered_zones:
            if zone in wall_candidates:
                candidates.append(wall_candidates[zone])
    else:
        candidates.append(centered)
        candidates.extend(wall_candidates.values())

    grid_x = [0.24, 0.5, 0.76]
    grid_y = [0.24, 0.5, 0.76]
    for fx in grid_x:
        for fy in grid_y:
            candidates.append(_layout_rect(rx + rw * fx - width / 2.0, ry + rh * fy - height / 2.0, width, height))

    unique: list[dict[str, float]] = []
    seen = set()
    for rect in candidates:
        rect = _clamp_rect_to_room(rect, room_rect)
        key = (round(rect["x"], 2), round(rect["y"], 2), round(rect["w"], 2), round(rect["h"], 2))
        if key in seen:
            continue
        seen.add(key)
        unique.append(rect)
    return unique


def _door_clearance_rects(room_rect: dict[str, float], doorways: list[dict[str, Any]]) -> list[dict[str, float]]:
    rects: list[dict[str, float]] = []
    for doorway in doorways:
        orientation = str(doorway.get("orientation") or "")
        length = float(doorway.get("length") or 0.9)
        if orientation == "vertical":
            rects.append(_layout_rect(float(doorway["x"]) - 0.3, float(doorway["y"]) - length / 2.0 - 0.35, 0.7, length + 0.7))
        else:
            rects.append(_layout_rect(float(doorway["x"]) - length / 2.0 - 0.35, float(doorway["y"]) - 0.3, length + 0.7, 0.7))
    return [
        _clamp_rect_to_room(rect, room_rect, margin=0.0)
        for rect in rects
    ]


def _score_candidate(
    rect: dict[str, float],
    *,
    room_rect: dict[str, float],
    occupied: list[dict[str, float]],
    door_blocks: list[dict[str, float]],
    preferred_zone: str | None,
    pair_rect: dict[str, float] | None = None,
    mode: str = "free",
    clearance: float = 0.0,
) -> float:
    expanded = _expand_rect(rect, clearance)
    penalty = 0.0
    for other in occupied:
        if _rects_overlap(expanded, other):
            penalty += 1000.0
    for other in door_blocks:
        if _rects_overlap(expanded, other):
            penalty += 1200.0
    cx, cy = _center_of(rect)
    zx, zy = _zone_point(room_rect, preferred_zone)
    penalty += math.hypot(cx - zx, cy - zy) * 0.8
    if pair_rect:
        px, py = _center_of(pair_rect)
        dist = math.hypot(cx - px, cy - py)
        if mode == "paired_front":
            penalty += abs(dist - max(pair_rect["h"], pair_rect["w"]) * 0.95) * 1.1
        elif mode == "paired_opposite":
            penalty += abs(dist - max(room_rect["w"], room_rect["h"]) * 0.38) * 0.9
        elif mode in {"paired_on_surface", "paired_under", "nearby", "attached"}:
            penalty += dist * 1.4
    return penalty


def _paired_child_rect(parent_rect: dict[str, float], semantic_type: str, mode: str, preferred_zone: str | None = None, child_index: int = 0) -> dict[str, float]:
    pw, ph = parent_rect["w"], parent_rect["h"]
    px, py = parent_rect["x"], parent_rect["y"]
    width, height = _box_size(semantic_type)
    width = min(width, max(0.16, pw * 0.9))
    height = min(height, max(0.16, ph * 0.9))
    if mode == "paired_on_surface":
        fx = {"left": 0.22, "center": 0.5, "right": 0.78}.get(str(preferred_zone or "center"), 0.5)
        return _layout_rect(px + pw * fx - width / 2.0, py + ph * 0.5 - height / 2.0, width, height)
    if mode == "paired_under":
        fx = {"left": 0.22, "center": 0.5, "right": 0.78}.get(str(preferred_zone or "center"), 0.22)
        return _layout_rect(px + pw * fx - width / 2.0, py + ph - height - 0.04, width, height)
    if mode == "attached":
        return _layout_rect(px + pw * 0.5 - width / 2.0, py + 0.08, width, height)
    if mode == "nearby":
        return _layout_rect(px + pw + 0.08 + child_index * 0.04, py + ph * 0.5 - height / 2.0, width, height)
    return _child_layout(parent_rect, semantic_type, child_index)


def _room_primary_layouts(nodes: list[dict[str, Any]], room_rect: dict[str, float], doorways: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    top_level = [node for node in nodes if node.get("parent") == node.get("room_id")]
    layout_map: dict[str, dict[str, float]] = {}
    occupied = _door_clearance_rects(room_rect, doorways)

    priority = {
        "anchor": 0,
        "wall": 1,
        "corner": 2,
        "free": 3,
        "paired_front": 4,
        "paired_opposite": 5,
    }
    top_level.sort(key=lambda node: (priority.get(str(node.get("placement_mode") or "free"), 9), str(node["id"])))

    for node in top_level:
        semantic_type = str(node.get("semantic_type") or "")
        width, height = _box_size(semantic_type)
        mode = str(node.get("placement_mode") or "free")
        preferred_zone = node.get("preferred_zone")
        pair_id = str(node.get("pair_with") or "")
        pair_rect = layout_map.get(pair_id)

        candidates = _candidate_rects(room_rect, width, height, preferred_zone, mode)
        if pair_rect and mode == "paired_front":
            px, py = _center_of(pair_rect)
            candidates = [
                _clamp_rect_to_room(_layout_rect(px + pair_rect["w"] * 0.08 - width / 2.0, py + pair_rect["h"] + 0.22, width, height), room_rect),
                _clamp_rect_to_room(_layout_rect(px + pair_rect["w"] + 0.22, py - height / 2.0, width, height), room_rect),
            ] + candidates
        elif pair_rect and mode == "paired_opposite":
            px, py = _center_of(pair_rect)
            candidates = [
                _clamp_rect_to_room(_layout_rect(px + pair_rect["w"] + 0.85, py - height / 2.0, width, height), room_rect),
                _clamp_rect_to_room(_layout_rect(px - width - 0.85, py - height / 2.0, width, height), room_rect),
            ] + candidates

        best = min(
            candidates,
            key=lambda rect: _score_candidate(
                rect,
                room_rect=room_rect,
                occupied=occupied,
                door_blocks=[],
                preferred_zone=preferred_zone,
                pair_rect=pair_rect,
                mode=mode,
                clearance=float(node.get("clearance_required") or 0.0),
            ),
        )
        layout_map[str(node["id"])] = best
        occupied.append(_expand_rect(best, float(node.get("clearance_required") or 0.0) * 0.4))
    return layout_map


def _child_layout(parent_layout: dict[str, Any], semantic_type: str, child_index: int) -> dict[str, float]:
    pw = float(parent_layout.get("w", 1.0))
    ph = float(parent_layout.get("h", 1.0))
    px = float(parent_layout.get("x", 0.0))
    py = float(parent_layout.get("y", 0.0))
    width, height = _box_size(semantic_type)
    width = min(width, max(0.16, pw * 0.88))
    height = min(height, max(0.16, ph * 0.88))

    if parent_layout.get("orientation") in {"vertical", "horizontal"}:
        return {
            "x": round(px - width / 2.0, 2),
            "y": round(py - height / 2.0, 2),
            "w": round(width, 2),
            "h": round(height, 2),
        }

    fx, fy = _anchor_fraction(semantic_type)
    x = px + pw * fx - width / 2.0
    y = py + ph * fy - height / 2.0
    if semantic_type in {"milk", "juice", "vegetable", "fruit", "bowl", "cup", "clothes", "shoes", "book", "toothbrush"}:
        slot_x = child_index % 2
        slot_y = child_index // 2
        x = px + 0.18 + slot_x * (width + 0.12)
        y = py + 0.16 + slot_y * (height + 0.12)
    return {"x": round(x, 2), "y": round(y, 2), "w": round(width, 2), "h": round(height, 2)}


def _control_profile_nodes(room_id: str, room_rect: dict[str, float], doorways: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary_door = deepcopy(doorways[0]) if doorways else {
        "orientation": "vertical",
        "x": round(room_rect["x"] + room_rect["w"], 2),
        "y": round(room_rect["y"] + room_rect["h"] / 2.0, 2),
        "width": 0.9,
        "target_room": "",
    }
    button_layout = {
        "x": round(primary_door["x"] + (0.18 if primary_door["orientation"] == "vertical" else 0.0), 2),
        "y": round(primary_door["y"] - (0.32 if primary_door["orientation"] == "vertical" else 0.18), 2),
        "w": 0.18,
        "h": 0.18,
    }
    light_layout = {
        "x": round(room_rect["x"] + room_rect["w"] / 2.0 - 0.18, 2),
        "y": round(room_rect["y"] + room_rect["h"] / 2.0 - 0.18, 2),
        "w": 0.36,
        "h": 0.36,
    }
    return [
        _base_node(
            node_id=f"door_{room_id}",
            name="door",
            name_cn="门",
            node_type="fixed_object",
            semantic_class="control",
            semantic_type="door",
            mobility="fixed",
            parent=room_id,
            interactive_actions=["move", "scan", "open", "close"],
            states={"is_open": False},
            layout={**primary_door},
        ),
        _base_node(
            node_id=f"light_{room_id}",
            name="light",
            name_cn="灯",
            node_type="fixed_object",
            semantic_class="appliance",
            semantic_type="light",
            mobility="fixed",
            interactive_actions=["move", "scan"],
            parent=room_id,
            states={"is_on": False},
            layout=light_layout,
        ),
        _base_node(
            node_id=f"button_{room_id}",
            name="button",
            name_cn="按钮",
            node_type="fixed_object",
            semantic_class="control",
            semantic_type="button",
            mobility="fixed",
            interactive_actions=["move", "press", "scan"],
            parent=room_id,
            states={"is_on": False, "is_pressed": False},
            layout=button_layout,
        ),
    ]


def _object_node(spec: dict[str, Any]) -> dict[str, Any]:
    semantic_type = str(spec["semantic_type"])
    node_type = str(spec["node_type"])
    parent = str(spec["parent"])
    name, name_cn = _fixture_name(semantic_type)
    mobility = "movable" if node_type == "movable_object" else "fixed"
    return _base_node(
        node_id=str(spec["id"]),
        name=name,
        name_cn=name_cn,
        node_type=node_type,
        semantic_class=_semantic_class(semantic_type, node_type),
        semantic_type=semantic_type,
        mobility=mobility,
        parent=parent,
        interactive_actions=_interactive_actions(node_type, semantic_type),
        states=_default_states(semantic_type),
        affordance_count=_affordance_count(semantic_type),
        placement_mode=str(spec.get("placement_mode") or "free"),
        pair_with=spec.get("pair_with"),
        clearance_required=float(spec.get("clearance_required") or 0.0),
        preferred_zone=spec.get("preferred_zone"),
    )


def _device_profile_nodes() -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for profile in DEVICE_CONTROLS:
        semantic_type = str(profile["semantic_type"])
        name, name_cn = _fixture_name(semantic_type)
        interactive_actions = ["move", "scan", "open", "close"] if semantic_type == "door" else ["move", "press", "scan"]
        states = {"is_open": False} if semantic_type == "door" else {"is_on": False, "is_pressed": False}
        nodes.append(
            _base_node(
                node_id=str(profile["child_id"]),
                name=name,
                name_cn=name_cn,
                node_type="fixed_object",
                semantic_class=_semantic_class(semantic_type, "fixed_object"),
                semantic_type=semantic_type,
                mobility="fixed",
                parent=str(profile["parent"]),
                interactive_actions=interactive_actions,
                states=states,
            )
        )
    return nodes


def _assign_layouts(nodes: list[dict[str, Any]]) -> None:
    node_map = {str(node["id"]): node for node in nodes}
    room_nodes = [node for node in nodes if str(node.get("node_type")) == "room"]

    for room in room_nodes:
        room_id = str(room["id"])
        room_rect = room.get("layout") or {}
        doorways = list(room_rect.get("doorways") or [])
        descendants = [node for node in nodes if str(node.get("room_id") or node.get("parent") or "") == room_id or str(node.get("parent") or "") == room_id]
        for node in descendants:
            if node.get("parent") == room_id:
                node["room_id"] = room_id
        layout_map = _room_primary_layouts(descendants, room_rect, doorways)
        for node_id, layout in layout_map.items():
            if node_id in node_map:
                node_map[node_id]["layout"] = layout

    sibling_index: dict[str, int] = {}
    pending = True
    guard = 0
    while pending and guard < 12:
        pending = False
        guard += 1
        for node in nodes:
            if node.get("layout") is not None:
                continue
            parent_id = str(node.get("parent") or "")
            parent = node_map.get(parent_id)
            if not parent or parent.get("layout") is None:
                pending = True
                continue
            key = parent_id
            idx = sibling_index.get(key, 0)
            sibling_index[key] = idx + 1
            semantic_type = str(node.get("semantic_type") or "")
            placement_mode = str(node.get("placement_mode") or "")
            preferred_zone = node.get("preferred_zone")
            if placement_mode in {"paired_on_surface", "paired_under", "attached", "nearby"}:
                node["layout"] = _paired_child_rect(parent["layout"], semantic_type, placement_mode, preferred_zone, idx)
            else:
                node["layout"] = _child_layout(parent["layout"], semantic_type, idx)


def _build_edges(
    template: FloorplanTemplate,
    all_nodes: dict[str, dict[str, Any]],
    adjacency: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    edges.extend(
        {
            "source_id": "F1",
            "target_id": room_id,
            "category": "structural",
            "relation": "contains",
        }
        for room_id in template.room_types
    )
    for source, target in adjacency:
        edges.append({"source_id": source, "target_id": target, "category": "structural", "relation": "adjacent_to"})

    for node_id, node in all_nodes.items():
        parent_id = node.get("parent")
        if not parent_id:
            continue
        relation = "inside_room"
        semantic_type = str(node.get("semantic_type") or "")
        parent_semantic = str((all_nodes.get(parent_id) or {}).get("semantic_type") or "")
        if parent_semantic in {"shoe_rack", "wardrobe", "fridge", "dishwasher", "washer", "drawer"}:
            relation = "in"
        elif parent_semantic in {"sink", "coffee_table", "desk"}:
            relation = "on"
        elif semantic_type in {"door", "light", "button", "knob"} and parent_id.startswith(("dishwasher_", "microwave_", "stove_", "washer_", "fridge_")):
            relation = "contains"
        elif semantic_type in {"door", "light", "button"} and parent_id in template.room_types:
            relation = "contains"
        elif parent_semantic == "desk" and semantic_type == "drawer":
            relation = "part_of"
        elif parent_semantic == "sink" and semantic_type in {"cup", "toothbrush"}:
            relation = "on"
        edges.append({"source_id": parent_id, "target_id": node_id, "category": "structural", "relation": relation})

    for room_id in template.room_types:
        edges.append({"source_id": f"button_{room_id}", "target_id": f"light_{room_id}", "category": "control", "relation": "controls"})
    edges.extend(
        [
            {"source_id": "faucet_kitchen", "target_id": "sink_kitchen", "category": "control", "relation": "controls"},
            {"source_id": "faucet_bathroom", "target_id": "sink_bathroom", "category": "control", "relation": "controls"},
        ]
    )
    for profile in DEVICE_CONTROLS:
        target = profile.get("controls")
        if target:
            edges.append({"source_id": str(profile["child_id"]), "target_id": str(target), "category": "control", "relation": "controls"})
    return edges


def generate_home_scene_from_template(
    template_name: str = "hub_home",
    scene_name: str = "simple_home_1f",
    *,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    template = get_home_floorplan_template(template_name)
    if template is None:
        raise ValueError(f"Unknown home floorplan template: {template_name}")

    rects = generate_room_rect_layout(template_name, seed=seed)
    adjacency, doorways = _derive_adjacency(template, rects)

    nodes: list[dict[str, Any]] = [
        _base_node(
            node_id="F1",
            name="Floor 1",
            name_cn="第 1 层",
            node_type="fixed_object",
            semantic_class="space",
            semantic_type="floor",
            mobility="structural",
            parent=None,
            interactive_actions=["move", "scan"],
            floor_number=1,
            layout={
                "x": 0.0,
                "y": 0.0,
                "w": round(max(rect["x"] + rect["w"] for rect in rects.values()) + 0.5, 2),
                "h": round(max(rect["y"] + rect["h"] for rect in rects.values()) + 0.5, 2),
            },
        )
    ]

    for room_id in template.room_types:
        spec = get_room_type_spec(room_id)
        if spec is None:
            raise ValueError(f"Unknown room type: {room_id}")
        nodes.append(_room_node(room_id, spec, rects[room_id], doorways.get(room_id, [])))

    for room_id in template.room_types:
        nodes.extend(_control_profile_nodes(room_id, rects[room_id], doorways.get(room_id, [])))
        for obj_spec in HOME_ROOM_OBJECTS.get(room_id, []):
            nodes.append(_object_node(obj_spec))

    nodes.extend(_device_profile_nodes())
    _assign_layouts(nodes)

    node_map = {str(node["id"]): node for node in nodes}
    edges = _build_edges(template, node_map, adjacency)

    children_map: dict[str, list[str]] = {}
    for edge in edges:
        relation = str(edge["relation"])
        if relation in {"contains", "inside_room", "in", "on", "part_of"}:
            children_map.setdefault(str(edge["source_id"]), []).append(str(edge["target_id"]))
    for node in nodes:
        node["child"] = sorted(children_map.get(str(node["id"]), []))

    scene = {
        "scene_name": scene_name,
        "scene_name_cn": "简单住宅单层",
        "world_state": {
            "step": 0,
            "day": 1,
            "time_min": 360,
            "minutes_per_step": 10,
            "weather": "sunny",
            "floorplan_template": template_name,
            "layout_seed": seed,
        },
    }
    set_scene_graph(scene, nodes, edges)
    return scene


def write_home_scene_json(
    output_path: str | Path,
    template_name: str = "hub_home",
    scene_name: str = "simple_home_1f",
    *,
    seed: int = DEFAULT_SEED,
) -> Path:
    scene = generate_home_scene_from_template(template_name=template_name, scene_name=scene_name, seed=seed)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scene, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


__all__ = [
    "generate_home_scene_from_template",
    "generate_room_rect_layout",
    "write_home_scene_json",
]
