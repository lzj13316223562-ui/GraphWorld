from __future__ import annotations

import copy
from collections import defaultdict

"""Home scene validator.

This module assumes scenes already follow the current GraphWorld schema.
It validates/fills required runtime defaults, but it is no longer intended
to be a legacy-scene compatibility layer.
"""


INTERACTIVE_ACTIONS = ["move", "pick", "place", "press", "scan", "open", "close", "brush"]
PARENT_RELATIONS = {"inside_room", "in", "on", "part_of", "held_by", "worn_by", "at", "near"}

FURNITURE_TYPES = {
    "sofa",
    "bed",
    "coffee_table",
    "table",
    "desk",
    "wardrobe",
    "seat",
    "drawer",
    "cabinet",
    "counter",
    "drying_rack",
    "shoe_rack",
    "door",
    "window",
    "rack",
    "shelf",
    "chair",
}
APPLIANCE_TYPES = {
    "toilet",
    "refrigerator",
    "fridge",
    "tv",
    "display",
    "washer",
    "washing_machine",
    "stove",
    "sink",
    "faucet",
    "light",
    "room_light",
    "trash_bin",
    "microwave",
    "dishwasher",
    "air_conditioner",
    "medicine_fridge",
}
CONTROL_TYPES = {"button", "knob"}
FOOD_TYPES = {"vegetable", "fruit", "yogurt", "drink", "milk", "juice", "raw_food", "cooked_food"}
CLOTHING_TYPES = {"shoes", "clothes", "socks", "towel"}
DISHWARE_TYPES = {"bowl", "plate", "cup"}
SUPPLY_TYPES = {"book", "stationery", "brush", "cloth", "broom", "watering_can", "plant", "toothbrush"}
CONTAINER_TYPES = {
    "wardrobe",
    "cabinet",
    "drawer",
    "refrigerator",
    "fridge",
    "washer",
    "dishwasher",
    "trash_bin",
    "sink",
    "shoe_rack",
    "rack",
    "medicine_fridge",
}
SUPPORT_TYPES = {
    "coffee_table",
    "table",
    "desk",
    "counter",
    "bed",
    "seat",
    "drying_rack",
    "shoe_rack",
    "rack",
    "shelf",
    "sofa",
    "chair",
    "cart",
    "medical_cart",
}
STATE_ALLOWLIST = {
    "common": {"is_dirty", "is_open", "is_on", "is_pressed", "fill_level", "is_full", "cycle_remaining", "freshness", "temperature", "target_temperature", "is_cooked", "is_rotten", "is_wet", "is_dry", "vitality", "is_wilted", "current_activity", "mood", "is_home", "is_clean", "folded", "cleanliness", "scattered", "holding", "handempty", "held_by", "heldBy", "misplaced_near", "brushed", "scanned", "pushed", "pulled", "dry_remaining", "mode", "fan_level"},
}

DEFAULT_AFFORDANCE_COUNT = {
    "shoe_rack": 6,
    "rack": 6,
    "shelf": 6,
    "wardrobe": 8,
    "drawer": 4,
    "cabinet": 6,
    "counter": 4,
    "drying_rack": 5,
    "sofa": 4,
    "chair": 4,
    "cart": 6,
    "medical_cart": 6,
    "trash_bin": 8,
    "sink": 4,
    "refrigerator": 10,
    "medicine_fridge": 10,
    "washer": 5,
    "dishwasher": 8,
    "coffee_table": 4,
    "table": 4,
    "desk": 5,
}

SEMANTIC_NAME_CN = {
    "door": "门",
    "room_light": "灯",
    "light": "灯",
    "button": "按钮",
    "knob": "旋钮",
    "shoe_rack": "鞋架",
    "rack": "架子",
    "shoes": "鞋",
    "seat": "座椅",
    "sofa": "沙发",
    "coffee_table": "茶几",
    "table": "桌子",
    "tv": "电视",
    "trash_bin": "垃圾桶",
    "counter": "操作台",
    "refrigerator": "冰箱",
    "fridge": "冰箱",
    "milk": "牛奶",
    "juice": "果汁",
    "vegetable": "蔬菜",
    "dishwasher": "洗碗机",
    "bowl": "碗",
    "microwave": "微波炉",
    "stove": "炉灶",
    "bed": "床",
    "wardrobe": "衣柜",
    "clothes": "衣服",
    "desk": "书桌",
    "drawer": "抽屉",
    "book": "书",
    "sink": "洗手池",
    "toilet": "马桶",
    "washer": "洗衣机",
    "washing_machine": "洗衣机",
    "faucet": "水龙头",
    "cup": "杯子",
    "toothbrush": "牙刷",
    "plant": "盆栽",
    "chair": "椅子",
    "display": "显示屏",
    "air_conditioner": "空调",
    "signboard": "导视牌",
    "wheelchair": "轮椅",
    "computer": "电脑",
    "printer": "打印机",
    "water_dispenser": "饮水机",
    "hand_sanitizer_dispenser": "手部消毒器",
    "medicine_box": "药盒",
    "pill_bottle": "药瓶",
    "medical_form": "医疗单据",
    "prescription_sheet": "处方单",
    "receipt": "收费单",
    "nurse_uniform": "护士服",
    "doctor_coat": "白大褂",
    "refrigerated_medicine": "冷藏药品",
    "syringe": "针筒",
    "infusion_bag": "输液袋",
    "medical_cart": "治疗推车",
    "medicine_fridge": "药品冰箱",
    "dispenser": "分配器",
    "machine": "机器",
    "cabinet": "柜子",
    "box": "箱子",
    "shelf": "货架",
    "cart": "推车",
    "human": "人",
    "robot": "机器人",
}
SEMANTIC_NAME_EN = {
    "door": "door",
    "room_light": "light",
    "light": "light",
    "button": "button",
    "knob": "knob",
    "shoe_rack": "shoe rack",
    "rack": "rack",
    "shoes": "shoes",
    "seat": "seat",
    "sofa": "sofa",
    "coffee_table": "coffee table",
    "table": "table",
    "tv": "tv",
    "trash_bin": "trash bin",
    "counter": "counter",
    "refrigerator": "refrigerator",
    "fridge": "refrigerator",
    "milk": "milk",
    "juice": "juice",
    "vegetable": "vegetable",
    "dishwasher": "dishwasher",
    "bowl": "bowl",
    "microwave": "microwave",
    "stove": "stove",
    "bed": "bed",
    "wardrobe": "wardrobe",
    "clothes": "clothes",
    "desk": "desk",
    "drawer": "drawer",
    "book": "book",
    "sink": "sink",
    "toilet": "toilet",
    "washer": "washer",
    "washing_machine": "washer",
    "faucet": "faucet",
    "cup": "cup",
    "toothbrush": "toothbrush",
    "plant": "plant",
    "chair": "chair",
    "display": "display",
    "air_conditioner": "air conditioner",
    "signboard": "signboard",
    "wheelchair": "wheelchair",
    "computer": "computer",
    "printer": "printer",
    "water_dispenser": "water dispenser",
    "hand_sanitizer_dispenser": "hand sanitizer dispenser",
    "medicine_box": "medicine box",
    "pill_bottle": "pill bottle",
    "medical_form": "medical form",
    "prescription_sheet": "prescription sheet",
    "receipt": "receipt",
    "nurse_uniform": "nurse uniform",
    "doctor_coat": "doctor coat",
    "refrigerated_medicine": "refrigerated medicine",
    "syringe": "syringe",
    "infusion_bag": "infusion bag",
    "medical_cart": "medical cart",
    "medicine_fridge": "medicine fridge",
    "dispenser": "dispenser",
    "machine": "machine",
    "cabinet": "cabinet",
    "box": "box",
    "shelf": "shelf",
    "cart": "cart",
    "human": "human",
    "robot": "robot",
}
SEMANTIC_CLASS_MAP = {
    "floor": "space",
    "room": "space",
    "door": "control",
    "window": "control",
    "button": "control",
    "knob": "control",
    "room_light": "appliance",
    "light": "appliance",
    "sofa": "furniture",
    "bed": "furniture",
    "coffee_table": "furniture",
    "table": "furniture",
    "desk": "furniture",
    "seat": "furniture",
    "chair": "furniture",
    "counter": "furniture",
    "shelf": "furniture",
    "refrigerator": "appliance",
    "fridge": "appliance",
    "washer": "appliance",
    "washing_machine": "appliance",
    "dishwasher": "appliance",
    "microwave": "appliance",
    "stove": "appliance",
    "sink": "appliance",
    "faucet": "appliance",
    "toilet": "appliance",
    "display": "appliance",
    "air_conditioner": "appliance",
    "signboard": "appliance",
    "computer": "appliance",
    "printer": "appliance",
    "water_dispenser": "appliance",
    "hand_sanitizer_dispenser": "appliance",
    "medicine_fridge": "appliance",
    "tv": "appliance",
    "cabinet": "container",
    "drawer": "container",
    "wardrobe": "container",
    "shoe_rack": "container",
    "rack": "container",
    "box": "container",
    "medicine_box": "container",
    "trash_bin": "container",
    "toilet_brush": "tool",
    "brush": "tool",
    "cloth": "tool",
    "broom": "tool",
    "watering_can": "tool",
    "wheelchair": "tool",
    "cart": "tool",
    "syringe": "tool",
    "medical_cart": "tool",
    "machine": "tool",
    "stationery": "tool",
    "shoes": "personal_item",
    "clothes": "personal_item",
    "socks": "personal_item",
    "towel": "personal_item",
    "toothbrush": "personal_item",
    "book": "personal_item",
    "medical_form": "personal_item",
    "prescription_sheet": "personal_item",
    "receipt": "personal_item",
    "nurse_uniform": "personal_item",
    "doctor_coat": "personal_item",
    "plant": "furniture",
    "milk": "consumable",
    "juice": "consumable",
    "vegetable": "consumable",
    "fruit": "consumable",
    "yogurt": "consumable",
    "drink": "consumable",
    "pill_bottle": "consumable",
    "refrigerated_medicine": "consumable",
    "infusion_bag": "consumable",
    "raw_food": "consumable",
    "cooked_food": "consumable",
    "bowl": "consumable",
    "plate": "consumable",
    "cup": "consumable",
    "human": "agent",
    "robot": "agent",
}




def _scene_type(scene: dict) -> str:
    name = str(scene.get("scene_name") or "").lower()
    if "home" in name or "residential" in name:
        return "home"
    if "hospital" in name:
        return "hospital"
    if "office" in name:
        return "office"
    if "supermarket" in name:
        return "supermarket"
    if "factory" in name:
        return "factory"
    return "generic"


def canonical_node_type(node: dict) -> str:
    value = str(node.get("node_type") or "").lower()
    if value:
        return value
    legacy = str(node.get("type") or "").lower()
    if legacy == "room":
        return "room"
    if legacy == "agent":
        return "agent"
    if legacy == "movable":
        return "movable_object"
    return "fixed_object"


def canonical_semantic_type(node: dict) -> str:
    return str(node.get("semantic_type") or node.get("object_type") or node.get("type") or "").lower()



def canonical_semantic_class(node: dict) -> str:
    value = str(node.get("semantic_class") or "").lower()
    if value:
        return value
    semantic_type = canonical_semantic_type(node)
    return SEMANTIC_CLASS_MAP.get(semantic_type, "tool")

def canonical_mobility(node: dict) -> str:
    value = str(node.get("mobility") or "").lower()
    if value:
        return value
    node_type = canonical_node_type(node)
    semantic_type = canonical_semantic_type(node)
    if node_type == "agent":
        return "agent"
    if semantic_type == "floor":
        return "structural"
    if node_type == "movable_object":
        return "movable"
    return "fixed"


def canonical_property(node: dict) -> dict:
    value = node.get("property")
    if isinstance(value, dict):
        return {
            "appearance": str(value.get("appearance") or ""),
            "physical": str(value.get("physical") or ""),
            "operation": str(value.get("operation") or ""),
        }
    legacy_props = node.get("properties") or {}
    legacy_physical = node.get("physical_properties") or {}
    return {
        "appearance": str(legacy_props.get("appearance") or ""),
        "physical": str(legacy_physical or legacy_props.get("physical") or ""),
        "operation": str(legacy_props.get("operation") or legacy_props.get("control_profile") or ""),
    }



def canonical_name(node: dict) -> str:
    node_type = canonical_node_type(node)
    semantic_type = canonical_semantic_type(node)
    if node_type == "room":
        return str(node.get("name") or node.get("id") or semantic_type)
    if semantic_type == "floor":
        return str(node.get("name") or node.get("id") or "floor")
    return SEMANTIC_NAME_EN.get(semantic_type, semantic_type.replace("_", " ") or str(node.get("name") or node.get("id") or "object"))


def canonical_name_cn(node: dict) -> str:
    node_type = canonical_node_type(node)
    semantic_type = canonical_semantic_type(node)
    if node_type == "room":
        return str(node.get("name_cn") or node.get("name") or node.get("id") or semantic_type)
    if semantic_type == "floor":
        return str(node.get("name_cn") or node.get("name") or node.get("id") or "楼层")
    return SEMANTIC_NAME_CN.get(semantic_type, str(node.get("name_cn") or node.get("name") or semantic_type))

def canonical_states(node: dict) -> dict:
    original_states = copy.deepcopy(node.get("states") or {})
    states = {}
    for key, value in original_states.items():
        states[key] = value
    if "isOpen" in states and "is_open" not in states:
        states["is_open"] = bool(states.pop("isOpen"))
    if "isOn" in states and "is_on" not in states:
        states["is_on"] = bool(states.pop("isOn"))
    if "isPressed" in states and "is_pressed" not in states:
        states["is_pressed"] = bool(states.pop("isPressed"))
    if "dirty" in states and "is_dirty" not in states:
        states["is_dirty"] = bool(states.pop("dirty"))
    semantic_type = canonical_semantic_type(node)
    node_type = canonical_node_type(node)
    defaults = {}
    if semantic_type in FURNITURE_TYPES:
        defaults.update({"is_dirty": False})
        if semantic_type in {"door", "window", "wardrobe", "drawer", "cabinet"}:
            defaults.update({"is_open": False})
    if semantic_type in APPLIANCE_TYPES:
        defaults.update({"is_on": False, "fill_level": 0.0, "is_full": False})
        if semantic_type in {"washer", "washing_machine", "dishwasher", "microwave", "refrigerator", "fridge"}:
            defaults.update({"is_open": False, "cycle_remaining": 0})
        if semantic_type in {"sink"}:
            defaults.update({"fill_level": 0.0, "is_full": False})
        if semantic_type == "air_conditioner":
            defaults.update({"target_temperature": 24.0, "mode": "cool", "fan_level": 2})
    if semantic_type in CONTROL_TYPES:
        defaults.update({"is_on": False, "is_pressed": False})
    if semantic_type in FOOD_TYPES:
        defaults.update({"freshness": 1.0, "temperature": "room", "is_cooked": False, "is_rotten": False})
    if semantic_type in CLOTHING_TYPES:
        defaults.update({"is_dirty": False, "is_wet": False, "is_dry": True})
    if semantic_type in DISHWARE_TYPES:
        defaults.update({"is_dirty": False, "is_wet": False, "is_dry": True, "is_clean": True})
    if semantic_type == "plant":
        defaults.update({"vitality": 1.0, "is_wilted": False})
    if semantic_type in CONTAINER_TYPES or semantic_type in SUPPORT_TYPES:
        defaults.update({"fill_level": 0.0, "is_full": False})
    if node_type == "agent":
        defaults.update({"current_activity": "idle", "mood": 1.0, "is_home": True})
    if node_type == "room":
        defaults.update({"temperature": 24.0})
    filtered_states = {key: value for key, value in states.items() if key in STATE_ALLOWLIST["common"]}
    defaults.update(filtered_states)
    return defaults


def canonical_affordance_count(node: dict) -> int:
    value = node.get("affordance_count")
    if isinstance(value, int):
        return value
    semantic_type = canonical_semantic_type(node)
    return DEFAULT_AFFORDANCE_COUNT.get(semantic_type, 0)


def infer_interactive_actions(node: dict) -> list[str]:
    node_type = canonical_node_type(node)
    semantic_type = canonical_semantic_type(node)
    actions = {"scan"}
    if node_type in {"room", "fixed_object"}:
        actions.add("move")
    if node_type == "movable_object":
        actions.add("pick")
    if semantic_type in CONTAINER_TYPES or semantic_type in SUPPORT_TYPES or node_type == "room":
        actions.add("place")
    if semantic_type in CONTROL_TYPES or semantic_type in {"faucet", "air_conditioner"}:
        actions.add("press")
    if semantic_type in {"door", "window", "drawer", "wardrobe", "cabinet"}:
        actions.update({"open", "close"})
    if semantic_type in {"toilet", "sink", "counter", "bowl", "plate", "cloth", "brush"}:
        actions.add("brush")
    return [action for action in INTERACTIVE_ACTIONS if action in actions]


def scene_nodes(scene: dict) -> list[dict]:
    if isinstance(scene.get("nodes"), list):
        return [copy.deepcopy(node) for node in scene.get("nodes", []) if isinstance(node, dict)]
    if isinstance(scene.get("node"), dict):
        nodes = []
        for node_id, node in scene["node"].items():
            payload = copy.deepcopy(node) if isinstance(node, dict) else {}
            payload.setdefault("id", str(node_id))
            nodes.append(payload)
        return nodes
    return []


def scene_edges(scene: dict) -> list[dict]:
    if isinstance(scene.get("edges"), list):
        return [copy.deepcopy(edge) for edge in scene.get("edges", []) if isinstance(edge, dict)]
    if isinstance(scene.get("edge"), dict):
        edges = []
        for edge_id, edge in scene["edge"].items():
            payload = copy.deepcopy(edge) if isinstance(edge, dict) else {}
            payload.setdefault("id", str(edge_id))
            edges.append(payload)
        return edges
    return []


def set_scene_graph(scene: dict, nodes: list[dict], edges: list[dict]) -> None:
    normalized_nodes = [copy.deepcopy(node) for node in nodes]
    normalized_edges = [copy.deepcopy(edge) for edge in edges]
    scene["nodes"] = normalized_nodes
    scene["edges"] = normalized_edges
    scene.pop("node", None)
    scene.pop("edge", None)


def infer_parent_child(scene: dict) -> tuple[dict[str, str | None], dict[str, list[str]]]:
    nodes = {str(node["id"]): node for node in scene_nodes(scene) if node.get("id")}
    parent_map: dict[str, str | None] = {node_id: None for node_id in nodes}
    child_map: dict[str, list[str]] = defaultdict(list)
    for edge in scene_edges(scene):
        source = str(edge.get("source_id") or "")
        target = str(edge.get("target_id") or "")
        relation = str(edge.get("relation") or "").lower()
        if source not in nodes or target not in nodes:
            continue
        if relation in PARENT_RELATIONS:
            parent_map[target] = source
    for node_id, node in nodes.items():
        if canonical_semantic_type(node) == "floor":
            continue
        if canonical_node_type(node) == "room" and not parent_map.get(node_id):
            floor_id = str(node.get("floor_id") or "")
            if floor_id in nodes:
                parent_map[node_id] = floor_id
    for node_id, parent_id in parent_map.items():
        if parent_id:
            child_map[parent_id].append(node_id)
    for child_ids in child_map.values():
        child_ids.sort()
    return parent_map, child_map


def canonical_layout(node: dict) -> dict:
    layout = copy.deepcopy(node.get("layout") or {})
    if not isinstance(layout, dict):
        layout = {}
    if canonical_node_type(node) == "room":
        layout.setdefault("doorways", [])
    return layout



def validate_home_scene(raw_scene: dict) -> dict:
    scene = copy.deepcopy(raw_scene)
    parent_map, child_map = infer_parent_child(scene)
    normalized_nodes = []
    for node in scene_nodes(scene):
        node_id = str(node.get("id") or "")
        normalized = copy.deepcopy(node)
        normalized.update({
            "id": node_id,
            "name": canonical_name(node),
            "name_cn": canonical_name_cn(node),
            "node_type": canonical_node_type(node),
            "semantic_class": canonical_semantic_class(node),
            "semantic_type": canonical_semantic_type(node),
            "mobility": canonical_mobility(node),
            "states": canonical_states(node),
            "property": canonical_property(node),
            "affordance_count": canonical_affordance_count(node),
            "parent": parent_map.get(node_id),
            "child": copy.deepcopy(child_map.get(node_id, [])),
            "interactive_actions": infer_interactive_actions(node),
            "layout": canonical_layout(node),
        })
        if node_id == "human_resident":
            normalized["property"]["operation"] = normalized["property"]["operation"] or "schedule_role=resident"
        normalized_nodes.append(normalized)
    set_scene_graph(scene, normalized_nodes, scene_edges(scene))
    world_state = scene.setdefault("world_state", {})
    world_state.setdefault("day", 1)
    world_state.setdefault("time_min", 360)
    world_state.setdefault("minutes_per_step", 10)
    world_state.setdefault("weather", "sunny")
    world_state.setdefault("day_phase", "dawn")
    return scene


def fill_home_scene_defaults(raw_scene: dict) -> dict:
    return validate_home_scene(raw_scene)


def normalize_home_scene(raw_scene: dict) -> dict:
    """Backward-compatible alias for the scene validator."""
    return validate_home_scene(raw_scene)


def is_home_scene(scene: dict) -> bool:
    return _scene_type(scene) == "home"
