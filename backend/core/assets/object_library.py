from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from ..nodes import ControlObject, FixedObject, MovableObject, NodeType
from ..states import DISCRETE_STATE_SPACE, DiscreteState


ALLOWED_STATE_NAMES = frozenset(DISCRETE_STATE_SPACE)


@dataclass(frozen=True)
class Capability:
    name: str
    states: Dict[str, Any] = field(default_factory=dict)
    actions: tuple[str, ...] = ()
    properties: Dict[str, Any] = field(default_factory=dict)


def _merge_actions(*groups: Iterable[str]) -> List[str]:
    actions: List[str] = []
    seen: set[str] = set()
    for group in groups:
        for action in group:
            if action in seen:
                continue
            seen.add(action)
            actions.append(action)
    return actions


MOVEABLE = Capability("moveable", actions=("move",))
PICKABLE = Capability("pickable", actions=("pick", "place"))
PLACE_TARGET = Capability("place_target", actions=("place",))
CLEANABLE = Capability("cleanable", states={DiscreteState.IS_DIRTY.value: False}, actions=("brush",))
SWITCHABLE = Capability("switchable", states={DiscreteState.IS_ON.value: False}, actions=("press",))
OPENABLE = Capability("openable", states={DiscreteState.IS_OPEN.value: False}, actions=("open", "close"))
FOLDABLE = Capability("foldable", states={DiscreteState.FOLDED.value: True}, actions=("fold",))
FILLABLE = Capability(
    "fillable",
    states={
        DiscreteState.FILL_LEVEL.value: 0.0,
        DiscreteState.IS_FULL.value: False,
    },
)
PERISHABLE = Capability("perishable", states={DiscreteState.IS_ROTTEN.value: False})
PLANT_LIFE = Capability(
    "plant_life",
    states={
        DiscreteState.IS_WILTED.value: False,
        DiscreteState.IS_WET.value: True,
        DiscreteState.VITALITY.value: 1.0,
    },
)
STRUCTURAL_DOOR = Capability(
    "structural_door",
    states={DiscreteState.IS_OPEN.value: False},
    actions=("open", "close"),
    properties={
        "door_kind": "structural",
        "blocks_visibility": True,
        "blocks_navigation": True,
    },
)
CONTAINMENT_BLOCKER = Capability(
    "containment_blocker",
    properties={"blocks_containment": True},
)
START_REQUIRES_CLOSED = Capability(
    "start_requires_closed",
    properties={"requires_closed_to_start": True},
)


@dataclass(frozen=True)
class ObjectTemplate:
    semantic_type: str
    name: str
    name_cn: str
    node_type: NodeType
    default_states: Dict[str, Any] = field(default_factory=dict)
    interactive_actions: List[str] = field(default_factory=list)
    placement: str = "room"
    capabilities: tuple[Capability, ...] = ()
    door_kind: Optional[str] = None
    blocks_visibility: bool = False
    blocks_navigation: bool = False
    blocks_containment: bool = False
    requires_closed_to_start: bool = False
    parent_device_type: Optional[str] = None

    def __post_init__(self) -> None:
        states: Dict[str, Any] = {}
        actions: List[str] = []
        properties: Dict[str, Any] = {}
        for capability in self.capabilities:
            states.update(deepcopy(capability.states))
            actions = _merge_actions(actions, capability.actions)
            properties.update(deepcopy(capability.properties))
        states.update(deepcopy(self.default_states))
        actions = _merge_actions(actions, self.interactive_actions)
        invalid_states = sorted(set(states) - ALLOWED_STATE_NAMES)
        if invalid_states:
            raise ValueError(f"{self.semantic_type} uses states outside DiscreteState: {invalid_states}")

        object.__setattr__(self, "default_states", states)
        object.__setattr__(self, "interactive_actions", actions)

        for key, default_value in (
            ("door_kind", None),
            ("blocks_visibility", False),
            ("blocks_navigation", False),
            ("blocks_containment", False),
            ("requires_closed_to_start", False),
            ("parent_device_type", None),
        ):
            if getattr(self, key) == default_value and key in properties:
                object.__setattr__(self, key, properties[key])

    def to_spec(self) -> Dict[str, Any]:
        return {
            "semantic_type": self.semantic_type,
            "name": self.name,
            "name_cn": self.name_cn,
            "node_type": self.node_type.value,
            "default_states": deepcopy(self.default_states),
            "interactive_actions": list(self.interactive_actions),
            "placement": self.placement,
            "capabilities": [capability.name for capability in self.capabilities],
            "door_kind": self.door_kind,
            "blocks_visibility": self.blocks_visibility,
            "blocks_navigation": self.blocks_navigation,
            "blocks_containment": self.blocks_containment,
            "requires_closed_to_start": self.requires_closed_to_start,
            "parent_device_type": self.parent_device_type,
        }

    def instantiate(self, node_id: str, *, parent: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cls = {
            NodeType.FIXED_OBJECT: FixedObject,
            NodeType.MOVABLE_OBJECT: MovableObject,
            NodeType.CONTROL_OBJECT: ControlObject,
        }.get(self.node_type, FixedObject)
        kwargs: Dict[str, Any] = {
            "states": deepcopy(self.default_states),
            "interactive_actions": list(self.interactive_actions),
            "parent": parent,
        }
        if cls is ControlObject:
            kwargs.update(
                {
                    "door_kind": self.door_kind,
                    "blocks_visibility": self.blocks_visibility,
                    "blocks_navigation": self.blocks_navigation,
                    "blocks_containment": self.blocks_containment,
                    "requires_closed_to_start": self.requires_closed_to_start,
                    "parent_device_type": self.parent_device_type,
                }
            )
        node = cls(str(node_id), self.semantic_type, self.name, self.name_cn, **kwargs).to_dict()
        for key in (
            "door_kind",
            "blocks_visibility",
            "blocks_navigation",
            "blocks_containment",
            "requires_closed_to_start",
            "parent_device_type",
        ):
            value = getattr(self, key)
            if value not in (None, False):
                node[key] = value
        if self.capabilities:
            node["capabilities"] = [capability.name for capability in self.capabilities]
        if overrides:
            for key, value in overrides.items():
                if key == "states" and isinstance(value, dict):
                    node["states"].update(value)
                else:
                    node[key] = value
        return node


OBJECT_LIBRARY: Dict[str, ObjectTemplate] = {
    "door": ObjectTemplate(
        "door",
        "door",
        "门",
        NodeType.CONTROL_OBJECT,
        {"is_dirty": False},
        ["move"],
        "wall",
        capabilities=(STRUCTURAL_DOOR,),
    ),
    "button": ObjectTemplate(
        "button",
        "button",
        "按钮",
        NodeType.CONTROL_OBJECT,
        {"is_pressed": False},
        ["move"],
        "wall",
        capabilities=(SWITCHABLE,),
    ),
    "room_light": ObjectTemplate(
        "room_light",
        "light",
        "灯",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "ceiling",
        capabilities=(SWITCHABLE,),
    ),
    "air_conditioner": ObjectTemplate(
        "air_conditioner",
        "air conditioner",
        "空调",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(SWITCHABLE, CLEANABLE),
    ),
    "rack": ObjectTemplate(
        "rack",
        "rack",
        "架子",
        NodeType.FIXED_OBJECT,
        {"is_dirty": False},
        ["move"],
        "wall",
    ),
    "shoe_rack": ObjectTemplate(
        "shoe_rack",
        "shoe rack",
        "鞋架",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(CLEANABLE, PLACE_TARGET),
    ),
    "seat": ObjectTemplate(
        "seat",
        "seat",
        "座椅",
        NodeType.FIXED_OBJECT,
        {},
        ["move", "place"],
        "room",
        capabilities=(CLEANABLE,),
    ),
    "chair": ObjectTemplate(
        "chair",
        "chair",
        "椅子",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "room",
        capabilities=(CLEANABLE, PLACE_TARGET),
    ),
    "table": ObjectTemplate(
        "table",
        "table",
        "桌子",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "room",
        capabilities=(CLEANABLE, PLACE_TARGET),
    ),
    "coffee_table": ObjectTemplate(
        "coffee_table",
        "coffee table",
        "茶几",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "room",
        capabilities=(CLEANABLE, PLACE_TARGET),
    ),
    "counter": ObjectTemplate(
        "counter",
        "counter",
        "操作台",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "room",
        capabilities=(CLEANABLE, PLACE_TARGET),
    ),
    "desk": ObjectTemplate(
        "desk",
        "desk",
        "书桌",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "room",
        capabilities=(CLEANABLE, PLACE_TARGET),
    ),
    "drawer": ObjectTemplate(
        "drawer",
        "drawer",
        "抽屉",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "container",
        capabilities=(OPENABLE, CLEANABLE, PLACE_TARGET),
    ),
    "sofa": ObjectTemplate(
        "sofa",
        "sofa",
        "沙发",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "room",
        capabilities=(CLEANABLE, PLACE_TARGET),
    ),
    "bed": ObjectTemplate(
        "bed",
        "bed",
        "床",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "room",
        capabilities=(CLEANABLE,),
    ),
    "wardrobe": ObjectTemplate(
        "wardrobe",
        "wardrobe",
        "衣柜",
        NodeType.FIXED_OBJECT,
        {"is_open": False, "is_dirty": False},
        ["move", "open", "close"],
        "wall",
    ),
    "cabinet": ObjectTemplate(
        "cabinet",
        "cabinet",
        "柜子",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(OPENABLE, CLEANABLE, PLACE_TARGET),
    ),
    "sink": ObjectTemplate(
        "sink",
        "sink",
        "水槽",
        NodeType.FIXED_OBJECT,
        {},
        ["move", "dump"],
        "wall",
        capabilities=(CLEANABLE, FILLABLE, PLACE_TARGET),
    ),
    "faucet": ObjectTemplate(
        "faucet",
        "faucet",
        "水龙头",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(SWITCHABLE,),
    ),
    "toilet": ObjectTemplate(
        "toilet",
        "toilet",
        "马桶",
        NodeType.FIXED_OBJECT,
        {"is_dirty": False},
        ["move", "brush"],
        "wall",
    ),
    "shower": ObjectTemplate(
        "shower",
        "shower",
        "淋浴",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "wall",
    ),
    "refrigerator": ObjectTemplate(
        "refrigerator",
        "refrigerator",
        "冰箱",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(OPENABLE, CLEANABLE, CONTAINMENT_BLOCKER),
    ),
    "microwave": ObjectTemplate(
        "microwave",
        "microwave",
        "微波炉",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "counter",
        capabilities=(SWITCHABLE, OPENABLE, CLEANABLE, CONTAINMENT_BLOCKER, START_REQUIRES_CLOSED),
    ),
    "stove": ObjectTemplate(
        "stove",
        "stove",
        "炉灶",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "counter",
    ),
    "washing_machine": ObjectTemplate(
        "washing_machine",
        "washing machine",
        "洗衣机",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(SWITCHABLE, OPENABLE, CLEANABLE, CONTAINMENT_BLOCKER, START_REQUIRES_CLOSED),
    ),
    "washer": ObjectTemplate(
        "washer",
        "washer",
        "洗衣机",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(SWITCHABLE, OPENABLE, CLEANABLE, CONTAINMENT_BLOCKER, START_REQUIRES_CLOSED),
    ),
    "drying_rack": ObjectTemplate(
        "drying_rack",
        "drying rack",
        "晾衣架",
        NodeType.FIXED_OBJECT,
        {},
        ["move", "place"],
        "wall",
    ),
    "television": ObjectTemplate(
        "television",
        "television",
        "电视",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "wall",
    ),
    "display": ObjectTemplate(
        "display",
        "display",
        "显示屏",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(SWITCHABLE, CLEANABLE),
    ),
    "plant": ObjectTemplate(
        "plant",
        "plant",
        "植物",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "room",
        capabilities=(PICKABLE, PLANT_LIFE),
    ),
    "mug": ObjectTemplate(
        "mug",
        "mug",
        "杯子",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "surface",
        capabilities=(PICKABLE, CLEANABLE, FILLABLE),
    ),
    "cup": ObjectTemplate(
        "cup",
        "cup",
        "杯子",
        NodeType.MOVABLE_OBJECT,
        {DiscreteState.IS_WET.value: False},
        [],
        "surface",
        capabilities=(PICKABLE, CLEANABLE, FILLABLE),
    ),
    "plate": ObjectTemplate(
        "plate",
        "plate",
        "盘子",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place", "brush"],
        "surface",
    ),
    "bowl": ObjectTemplate(
        "bowl",
        "bowl",
        "碗",
        NodeType.MOVABLE_OBJECT,
        {DiscreteState.IS_WET.value: False},
        [],
        "surface",
        capabilities=(PICKABLE, CLEANABLE),
    ),
    "book": ObjectTemplate(
        "book",
        "book",
        "书",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
    ),
    "remote": ObjectTemplate(
        "remote",
        "remote",
        "遥控器",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
    ),
    "clothes": ObjectTemplate(
        "clothes",
        "clothes",
        "衣物",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False, "is_wet": False},
        ["pick", "place"],
        "container",
        capabilities=(FOLDABLE,),
    ),
    "shoes": ObjectTemplate(
        "shoes",
        "shoes",
        "鞋",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False, "is_wet": False},
        ["pick", "place", "brush"],
        "rack",
    ),
    "box": ObjectTemplate(
        "box",
        "box",
        "箱子",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
    ),
    "cart": ObjectTemplate(
        "cart",
        "cart",
        "推车",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["move", "pick", "place"],
        "room",
    ),
    "computer": ObjectTemplate(
        "computer",
        "computer",
        "电脑",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "table",
    ),
    "dishwasher": ObjectTemplate(
        "dishwasher",
        "dishwasher",
        "洗碗机",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(SWITCHABLE, OPENABLE, CLEANABLE, CONTAINMENT_BLOCKER, START_REQUIRES_CLOSED),
    ),
    "dispenser": ObjectTemplate(
        "dispenser",
        "dispenser",
        "分配器",
        NodeType.FIXED_OBJECT,
        {"is_dirty": False, "fill_level": 1.0},
        ["move", "press"],
        "wall",
        capabilities=(FILLABLE,),
    ),
    "doctor_coat": ObjectTemplate(
        "doctor_coat",
        "doctor coat",
        "医生白大褂",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "container",
    ),
    "drink": ObjectTemplate(
        "drink",
        "drink",
        "饮料",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "shelf",
        capabilities=(PICKABLE, OPENABLE, PERISHABLE),
    ),
    "fruit": ObjectTemplate(
        "fruit",
        "fruit",
        "水果",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "shelf",
        capabilities=(PICKABLE, PERISHABLE),
    ),
    "hand_sanitizer_dispenser": ObjectTemplate(
        "hand_sanitizer_dispenser",
        "hand sanitizer dispenser",
        "免洗洗手液机",
        NodeType.FIXED_OBJECT,
        {"fill_level": 1.0, "is_dirty": False},
        ["move", "press"],
        "wall",
        capabilities=(FILLABLE,),
    ),
    "juice": ObjectTemplate(
        "juice",
        "juice",
        "果汁",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "container",
        capabilities=(PICKABLE, OPENABLE, PERISHABLE),
    ),
    "knob": ObjectTemplate(
        "knob",
        "knob",
        "旋钮",
        NodeType.FIXED_OBJECT,
        {"is_on": False},
        ["move", "press"],
        "appliance",
    ),
    "locker": ObjectTemplate(
        "locker",
        "locker",
        "储物柜",
        NodeType.FIXED_OBJECT,
        {"is_open": False, "is_dirty": False},
        ["move", "open", "close"],
        "wall",
    ),
    "machine": ObjectTemplate(
        "machine",
        "machine",
        "机器",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "room",
    ),
    "medical_cart": ObjectTemplate(
        "medical_cart",
        "medical cart",
        "医疗推车",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["move", "pick", "place"],
        "room",
    ),
    "medical_form": ObjectTemplate(
        "medical_form",
        "medical form",
        "医疗表单",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
    ),
    "medicine_box": ObjectTemplate(
        "medicine_box",
        "medicine box",
        "药盒",
        NodeType.MOVABLE_OBJECT,
        {"is_open": False},
        ["pick", "place", "open", "close"],
        "shelf",
    ),
    "medicine_fridge": ObjectTemplate(
        "medicine_fridge",
        "medicine fridge",
        "药品冰箱",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        capabilities=(OPENABLE, CLEANABLE, CONTAINMENT_BLOCKER),
    ),
    "milk": ObjectTemplate(
        "milk",
        "milk",
        "牛奶",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "container",
        capabilities=(PICKABLE, OPENABLE, PERISHABLE),
    ),
    "nurse_uniform": ObjectTemplate(
        "nurse_uniform",
        "nurse uniform",
        "护士制服",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "container",
    ),
    "prescription_sheet": ObjectTemplate(
        "prescription_sheet",
        "prescription sheet",
        "处方单",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
    ),
    "printer": ObjectTemplate(
        "printer",
        "printer",
        "打印机",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "table",
    ),
    "receipt": ObjectTemplate(
        "receipt",
        "receipt",
        "收据",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
    ),
    "refrigerated_medicine": ObjectTemplate(
        "refrigerated_medicine",
        "refrigerated medicine",
        "冷藏药品",
        NodeType.MOVABLE_OBJECT,
        {"temperature": "cold"},
        [],
        "container",
        capabilities=(PICKABLE, PERISHABLE),
    ),
    "shelf": ObjectTemplate(
        "shelf",
        "shelf",
        "货架",
        NodeType.FIXED_OBJECT,
        {"is_dirty": False},
        ["move", "place"],
        "wall",
    ),
    "signboard": ObjectTemplate(
        "signboard",
        "signboard",
        "标牌",
        NodeType.FIXED_OBJECT,
        {"is_dirty": False},
        ["move"],
        "wall",
    ),
    "stationery": ObjectTemplate(
        "stationery",
        "stationery",
        "文具",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
    ),
    "syringe": ObjectTemplate(
        "syringe",
        "syringe",
        "注射器",
        NodeType.MOVABLE_OBJECT,
        {},
        ["pick", "place"],
        "surface",
    ),
    "toilet_brush": ObjectTemplate(
        "toilet_brush",
        "toilet brush",
        "马桶刷",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place", "brush"],
        "bathroom",
    ),
    "toothbrush": ObjectTemplate(
        "toothbrush",
        "toothbrush",
        "牙刷",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place", "brush"],
        "surface",
    ),
    "toothpaste": ObjectTemplate(
        "toothpaste",
        "toothpaste",
        "牙膏",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
    ),
    "trash_bin": ObjectTemplate(
        "trash_bin",
        "trash bin",
        "垃圾桶",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "room",
        capabilities=(PLACE_TARGET,),
    ),
    "vegetable": ObjectTemplate(
        "vegetable",
        "vegetable",
        "蔬菜",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "shelf",
        capabilities=(PICKABLE, PERISHABLE),
    ),
    "water_dispenser": ObjectTemplate(
        "water_dispenser",
        "water dispenser",
        "饮水机",
        NodeType.FIXED_OBJECT,
        {"is_on": True, "is_dirty": False, "fill_level": 1.0},
        ["move", "press"],
        "wall",
        capabilities=(FILLABLE,),
    ),
    "wheelchair": ObjectTemplate(
        "wheelchair",
        "wheelchair",
        "轮椅",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["move", "pick", "place"],
        "room",
    ),
}

OBJECT_TYPE_ALIASES = {
    "book_stack": "book",
    "fridge": "refrigerator",
    "stationery_set": "stationery",
    "tv": "television",
}


def resolve_object_key(object_type: str) -> str:
    key = str(object_type or "").strip()
    return OBJECT_TYPE_ALIASES.get(key, key)


def get_object_spec(object_type: str) -> Dict[str, Any]:
    key = resolve_object_key(object_type)
    if key not in OBJECT_LIBRARY:
        return {
            "semantic_type": object_type,
            "name": object_type.replace("_", " "),
            "name_cn": object_type,
            "node_type": NodeType.MOVABLE_OBJECT.value,
            "default_states": {},
            "interactive_actions": ["pick", "place"],
            "placement": "room",
        }
    spec = OBJECT_LIBRARY[key]
    return spec.to_spec()


def build_object_node(node_id: str, object_type: str, *, parent: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    key = resolve_object_key(object_type)
    if key in OBJECT_LIBRARY:
        return OBJECT_LIBRARY[key].instantiate(node_id, parent=parent, overrides=overrides)
    fallback = ObjectTemplate(
        semantic_type=object_type,
        name=object_type.replace("_", " "),
        name_cn=object_type,
        node_type=NodeType.MOVABLE_OBJECT,
        default_states={},
        interactive_actions=["pick", "place"],
        placement="room",
    )
    return fallback.instantiate(node_id, parent=parent, overrides=overrides)


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
        "door_kind": spec.get("door_kind"),
        "blocks_visibility": spec.get("blocks_visibility"),
        "blocks_navigation": spec.get("blocks_navigation"),
        "blocks_containment": spec.get("blocks_containment"),
        "requires_closed_to_start": spec.get("requires_closed_to_start"),
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
            "toothpaste",
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
            "drying_rack",
            "clothes",
            "plant",
        ],
    }
    return list(room_map.get(room_type, []))
