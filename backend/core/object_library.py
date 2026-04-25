from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ObjectSpec:
    semantic_type: str
    name: str
    name_cn: str
    node_type: str
    default_states: Dict[str, Any] = field(default_factory=dict)
    interactive_actions: List[str] = field(default_factory=list)
    placement: str = "room"
    aliases: List[str] = field(default_factory=list)


OBJECT_LIBRARY: Dict[str, ObjectSpec] = {
    "door": ObjectSpec(
        "door",
        "door",
        "门",
        "fixed_object",
        {"is_open": False, "is_dirty": False},
        ["move", "scan", "open", "close"],
        "wall",
    ),
    "button": ObjectSpec(
        "button",
        "button",
        "按钮",
        "fixed_object",
        {"is_on": False, "is_pressed": False},
        ["move", "press", "scan"],
        "wall",
    ),
    "room_light": ObjectSpec(
        "room_light",
        "light",
        "灯",
        "fixed_object",
        {"is_on": False, "fill_level": 0.0, "is_full": False},
        ["move", "scan"],
        "ceiling",
        ["light"],
    ),
    "air_conditioner": ObjectSpec(
        "air_conditioner",
        "air conditioner",
        "空调",
        "fixed_object",
        {
            "is_on": False,
            "mode": "cool",
            "target_temperature": 24.0,
            "fan_level": 1,
            "is_dirty": False,
        },
        ["move", "press", "scan"],
        "wall",
        ["ac"],
    ),
    "rack": ObjectSpec(
        "rack",
        "rack",
        "架子",
        "fixed_object",
        {"is_dirty": False},
        ["move", "scan"],
        "wall",
        ["shoe_rack"],
    ),
    "seat": ObjectSpec(
        "seat",
        "seat",
        "座椅",
        "fixed_object",
        {"is_dirty": False, "fill_level": 0.0, "is_full": False},
        ["move", "place", "scan"],
        "room",
        ["bench", "chair", "sofa"],
        
    ),
    "table": ObjectSpec(
        "table",
        "table",
        "桌子",
        "fixed_object",
        {"is_dirty": False, "fill_level": 0.0, "is_full": False},
        ["move", "place", "scan", "brush"],
        "room",
        ["coffee_table", "counter", "desk"],
    ),
    "bed": ObjectSpec(
        "bed",
        "bed",
        "床",
        "fixed_object",
        {"is_dirty": False, "is_made": True},
        ["move", "scan", "brush"],
        "room",
    ),
    "wardrobe": ObjectSpec(
        "wardrobe",
        "wardrobe",
        "衣柜",
        "fixed_object",
        {"is_open": False, "is_dirty": False},
        ["move", "scan", "open", "close"],
        "wall",
        ["drawer", "cabinet"],
    ),
    "sink": ObjectSpec(
        "sink",
        "sink",
        "水槽",
        "fixed_object",
        {"is_on": False, "is_dirty": False, "has_water": False},
        ["move", "press", "scan", "brush"],
        "wall",
    ),
    "toilet": ObjectSpec(
        "toilet",
        "toilet",
        "马桶",
        "fixed_object",
        {"is_dirty": False},
        ["move", "scan", "brush"],
        "wall",
    ),
    "shower": ObjectSpec(
        "shower",
        "shower",
        "淋浴",
        "fixed_object",
        {"is_on": False, "is_dirty": False},
        ["move", "press", "scan", "brush"],
        "wall",
        ["faucet"],
    ),
    "refrigerator": ObjectSpec(
        "refrigerator",
        "refrigerator",
        "冰箱",
        "fixed_object",
        {"is_on": True, "is_open": False, "is_dirty": False},
        ["move", "scan", "open", "close", "brush"],
        "wall",
        ["fridge"],
    ),
    "microwave": ObjectSpec(
        "microwave",
        "microwave",
        "微波炉",
        "fixed_object",
        {"is_on": False, "is_open": False, "is_dirty": False},
        ["move", "scan", "press", "open", "close", "brush"],
        "counter",
    ),
    "stove": ObjectSpec(
        "stove",
        "stove",
        "炉灶",
        "fixed_object",
        {"is_on": False, "is_dirty": False},
        ["move", "scan", "press", "brush"],
        "counter",
    ),
    "washing_machine": ObjectSpec(
        "washing_machine",
        "washing machine",
        "洗衣机",
        "fixed_object",
        {"is_on": False, "is_open": False, "is_dirty": False},
        ["move", "scan", "press", "open", "close", "brush"],
        "wall",
        ["washer"],
    ),
    "television": ObjectSpec(
        "television",
        "television",
        "电视",
        "fixed_object",
        {"is_on": False, "is_dirty": False},
        ["move", "scan", "press", "brush"],
        "wall",
        ["tv", "display"],
    ),
    "plant": ObjectSpec(
        "plant",
        "plant",
        "植物",
        "movable_object",
        {"is_healthy": True, "is_dry": False},
        ["pick", "place", "scan"],
        "room",
    ),
    "mug": ObjectSpec(
        "mug",
        "mug",
        "杯子",
        "movable_object",
        {"is_dirty": False, "is_full": False, "fill_level": 0.0},
        ["pick", "place", "scan", "brush"],
        "surface",
        ["cup"],
    ),
    "plate": ObjectSpec(
        "plate",
        "plate",
        "盘子",
        "movable_object",
        {"is_dirty": False},
        ["pick", "place", "scan", "brush"],
        "surface",
        ["bowl"],
    ),
    "book": ObjectSpec(
        "book",
        "book",
        "书",
        "movable_object",
        {"is_dirty": False},
        ["pick", "place", "scan"],
        "surface",
    ),
    "remote": ObjectSpec(
        "remote",
        "remote",
        "遥控器",
        "movable_object",
        {"is_dirty": False},
        ["pick", "place", "scan"],
        "surface",
    ),
    "clothes": ObjectSpec(
        "clothes",
        "clothes",
        "衣物",
        "movable_object",
        {"is_dirty": False, "is_wet": False, "is_dry": True},
        ["pick", "place", "scan", "brush"],
        "container",
    ),
    "shoes": ObjectSpec(
        "shoes",
        "shoes",
        "鞋",
        "movable_object",
        {"is_dirty": False, "is_wet": False, "is_dry": True},
        ["pick", "scan"],
        "rack",
    ),
}

ALIASES: Dict[str, str] = {}
for key, spec in OBJECT_LIBRARY.items():
    names = [
        key,
        spec.semantic_type,
        spec.name,
    ]
    for name in names:
        ALIASES[name] = key
    for alias in spec.aliases:
        ALIASES[alias] = key


def resolve_object_key(object_type: str) -> str:
    key = ALIASES.get(object_type, object_type)
    if key not in OBJECT_LIBRARY:
        return object_type
    return key


def get_object_spec(object_type: str) -> Dict[str, Any]:
    key = resolve_object_key(object_type)
    if key not in OBJECT_LIBRARY:
        return {
            "semantic_type": object_type,
            "name": object_type.replace("_", " "),
            "name_cn": object_type,
            "node_type": "movable_object",
            "default_states": {},
            "interactive_actions": ["scan"],
            "placement": "room",
        }
    spec = OBJECT_LIBRARY[key]
    return {
        "semantic_type": spec.semantic_type,
        "name": spec.name,
        "name_cn": spec.name_cn,
        "node_type": spec.node_type,
        "default_states": deepcopy(spec.default_states),
        "interactive_actions": list(spec.interactive_actions),
        "placement": spec.placement,
    }


def build_object_node(node_id: str, object_type: str, *, parent: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    spec = get_object_spec(object_type)
    node = {
        "id": node_id,
        "name": spec["name"],
        "name_cn": spec["name_cn"],
        "node_type": spec["node_type"],
        "semantic_type": spec["semantic_type"],
        "parent": parent,
        "states": deepcopy(spec["default_states"]),
        "interactive_actions": list(spec["interactive_actions"]),
    }
    if overrides:
        for key, value in overrides.items():
            if key == "states" and isinstance(value, dict):
                node["states"].update(value)
            else:
                node[key] = value
    return node


def list_object_types() -> Iterable[str]:
    return OBJECT_LIBRARY.keys()


def get_object_template(name: str) -> Dict[str, Any]:
    spec = get_object_spec(name)
    return {
        "object_type": spec["semantic_type"],
        "affordances": list(spec["interactive_actions"]),
        "states": deepcopy(spec["default_states"]),
        "default_states": deepcopy(spec["default_states"]),
        "physical_properties": {"placement": spec["placement"]},
    }


def list_available_objects() -> List[str]:
    return list(OBJECT_LIBRARY.keys())


def get_objects_for_room(room_type: str) -> List[str]:
    room_map = {
        "entrance": [
            "door",
            "button",
            "room_light",
            "rack",
            "seat",
            "shoes",
        ],
        "living_room": [
            "door",
            "button",
            "room_light",
            "air_conditioner",
            "seat",
            "table",
            "television",
            "remote",
            "book",
            "mug",
            "plant",
        ],
        "bedroom": [
            "door",
            "button",
            "room_light",
            "air_conditioner",
            "bed",
            "wardrobe",
            "book",
            "clothes",
        ],
        "bathroom": [
            "door",
            "button",
            "room_light",
            "sink",
            "toilet",
            "shower",
        ],
        "kitchen": [
            "door",
            "button",
            "room_light",
            "sink",
            "refrigerator",
            "microwave",
            "stove",
            "table",
            "mug",
            "plate",
        ],
        "balcony": [
            "door",
            "button",
            "room_light",
            "washing_machine",
            "clothes",
            "plant",
        ],
    }
    return list(room_map.get(room_type, []))
