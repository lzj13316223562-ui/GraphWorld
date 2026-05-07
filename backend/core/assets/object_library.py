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
    image_path: Optional[str] = None
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
            "image_path": self.image_path,
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
        if self.image_path:
            node["image_path"] = self.image_path
        if overrides:
            for key, value in overrides.items():
                if key == "states" and isinstance(value, dict):
                    node["states"].update(value)
                else:
                    node[key] = value
        return node


def object_image(object_key: str, *_unused: str) -> Dict[str, str]:
    return {
        "image_path": f"/assets/object_images/{object_key}.jpg",
    }


def commons_image(object_key: str, *_unused: str) -> Dict[str, str]:
    return object_image(object_key)


OBJECT_LIBRARY: Dict[str, ObjectTemplate] = {
    "door": ObjectTemplate(
        "door",
        "door",
        "门",
        NodeType.CONTROL_OBJECT,
        {"is_dirty": False},
        ["move"],
        "wall",
        **commons_image("door", "Door, 120 rue du Bac, Paris 10 December 2016.jpg", "CC BY 2.0"),
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
        **commons_image("button", "SparkFun push-button-33mm---pink 16094491018 o.jpg", "CC BY 2.0"),
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
        **commons_image("room_light", "Ceiling Light (207872861).jpeg", "CC BY 3.0"),
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
        **commons_image("air_conditioner", "Air conditioners on apartment walls.jpg", "CC BY-SA 2.0"),
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
        **commons_image("rack", "Rental Shoe rack (6793993769).jpg", "CC BY-SA 2.0"),
    ),
    "shoe_rack": ObjectTemplate(
        "shoe_rack",
        "shoe rack",
        "鞋架",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        **commons_image("shoes", "Pair of Camper shoes (2).jpg", "CC BY-SA 2.0"),
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
        **commons_image("seat", "Antique chair with caning seat 01.jpg", "CC BY-SA 4.0"),
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
        **commons_image("seat", "Antique chair with caning seat 01.jpg", "CC BY-SA 4.0"),
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
        **commons_image("table", "Carleson Solid Wood Coffee Table In Provincial Tea (264060733).jpeg", "CC0"),
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
        **commons_image("table", "Carleson Solid Wood Coffee Table In Provincial Tea (264060733).jpeg", "CC0"),
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
        **commons_image("counter"),
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
        **commons_image("desk"),
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
        **commons_image("drawer"),
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
        **commons_image("sofa"),
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
        **commons_image("bed", "Ming Canopy Bed.jpg", "CC0"),
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
        **commons_image("wardrobe", "Wardrobe in the palace of the Grand Dukes of Lithuania.jpg", "CC BY-SA 4.0"),
    ),
    "cabinet": ObjectTemplate(
        "cabinet",
        "cabinet",
        "柜子",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        **commons_image("cabinet"),
        capabilities=(OPENABLE, CLEANABLE, PLACE_TARGET),
    ),
    "sink": ObjectTemplate(
        "sink",
        "sink",
        "水槽",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        **commons_image("sink", "Kitchen Sink Fazimoto.jpg", "CC BY 2.0"),
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
        **commons_image("faucet"),
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
        **commons_image("toilet", "Premier Inn bathroom toilet, Horsham, West Sussex.jpg", "CC BY-SA 4.0"),
    ),
    "shower": ObjectTemplate(
        "shower",
        "shower",
        "淋浴",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "wall",
        **commons_image("shower", "Dual-head shower - Flickr - andrechinn.jpg", "CC BY 2.0"),
    ),
    "refrigerator": ObjectTemplate(
        "refrigerator",
        "refrigerator",
        "冰箱",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        **commons_image("refrigerator", "Open refrigerator with food at night.jpg", "CC BY-SA 4.0"),
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
        **commons_image("microwave", "Ikea Sektion Microwave Oven Installation 01.jpg", "CC BY-SA 4.0"),
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
        **commons_image("stove", "Gas stove.jpg", "CC BY-SA 3.0"),
    ),
    "washing_machine": ObjectTemplate(
        "washing_machine",
        "washing machine",
        "洗衣机",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        **commons_image("washing_machine", "Old Maytag wringer washing machine clothes washer.jpg", "CC BY 2.0"),
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
        **commons_image("washing_machine", "Old Maytag wringer washing machine clothes washer.jpg", "CC BY 2.0"),
        capabilities=(SWITCHABLE, OPENABLE, CLEANABLE, CONTAINMENT_BLOCKER, START_REQUIRES_CLOSED),
    ),
    "television": ObjectTemplate(
        "television",
        "television",
        "电视",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "wall",
        **commons_image("television", "Koryo Hotel - Flat Screen Arirang TV with access to BBC and other international news (11416726563).jpg", "CC BY-SA 2.0"),
    ),
    "display": ObjectTemplate(
        "display",
        "display",
        "显示屏",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        **commons_image("television", "Koryo Hotel - Flat Screen Arirang TV with access to BBC and other international news (11416726563).jpg", "CC BY-SA 2.0"),
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
        **commons_image("plant", "Potted plant. (Maceta).jpg", "CC0"),
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
        **commons_image("mug", "Coffee mug - Flickr - Stiller Beobachter.jpg", "CC BY 2.0"),
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
        **commons_image("mug", "Coffee mug - Flickr - Stiller Beobachter.jpg", "CC BY 2.0"),
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
        **commons_image("plate", "031 Ceramic Plate (9171281977).jpg", "CC BY 2.0"),
    ),
    "bowl": ObjectTemplate(
        "bowl",
        "bowl",
        "碗",
        NodeType.MOVABLE_OBJECT,
        {DiscreteState.IS_WET.value: False},
        [],
        "surface",
        **commons_image("plate", "031 Ceramic Plate (9171281977).jpg", "CC BY 2.0"),
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
        **commons_image("book", "Stack of journals and books in the Central Geological Survey Library, MOEA.jpg", "CC BY-SA 4.0"),
    ),
    "remote": ObjectTemplate(
        "remote",
        "remote",
        "遥控器",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
        **commons_image("remote", "Philips television ultrasonic remote control 01.jpg", "CC BY-SA 4.0"),
    ),
    "clothes": ObjectTemplate(
        "clothes",
        "clothes",
        "衣物",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False, "is_wet": False},
        ["pick", "place", "brush"],
        "container",
        **commons_image("clothes", "Pile of clothes.jpg", "CC BY-SA 2.0"),
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
        **commons_image("shoes", "Pair of Camper shoes (2).jpg", "CC BY-SA 2.0"),
    ),
    "box": ObjectTemplate(
        "box",
        "box",
        "箱子",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
        **commons_image("box", "Box, cardboard (AM 2014.69.9-10).jpg", "CC BY 4.0"),
    ),
    "cart": ObjectTemplate(
        "cart",
        "cart",
        "推车",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["move", "pick", "place"],
        "room",
        **commons_image("cart", "A Grey Wooden Furniture Dolly (46138039674).jpg", "CC BY 2.0"),
    ),
    "computer": ObjectTemplate(
        "computer",
        "computer",
        "电脑",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "table",
        **commons_image("computer", "Louisiana - Hollie Desktop Computer 2014.jpg", "CC BY 2.0"),
    ),
    "dishwasher": ObjectTemplate(
        "dishwasher",
        "dishwasher",
        "洗碗机",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        **commons_image("dishwasher", "General Electric Dishwasher Model GSD500D-03AW, img01.jpg", "CC BY-SA 4.0"),
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
        **commons_image("dispenser", "Luron soap dispenser (24048336072).jpg", "CC BY-SA 2.0"),
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
        **object_image(
            "doctor_coat",
            "https://live.staticflickr.com/75/157578783_150c8a5003_b.jpg",
            "https://www.flickr.com/photos/11831132@N00/157578783",
            "CC BY 2.0",
        ),
    ),
    "drink": ObjectTemplate(
        "drink",
        "drink",
        "饮料",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "shelf",
        **object_image(
            "drink",
            "https://live.staticflickr.com/5556/15074776349_7eea580ce8_b.jpg",
            "https://www.flickr.com/photos/10710442@N08/15074776349",
            "CC BY 2.0",
        ),
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
        **object_image(
            "fruit",
            "https://live.staticflickr.com/2684/4346215644_77828bf5dc_b.jpg",
            "https://www.flickr.com/photos/62938898@N00/4346215644",
            "CC BY 2.0",
        ),
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
        **object_image(
            "hand_sanitizer_dispenser",
            "https://live.staticflickr.com/2504/3986339020_6e934eeaf2_b.jpg",
            "https://www.flickr.com/photos/35213476@N08/3986339020",
            "CC BY 2.0",
        ),
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
        **object_image(
            "juice",
            "https://live.staticflickr.com/66/179905136_e39986ab35_b.jpg",
            "https://www.flickr.com/photos/85563234@N00/179905136",
            "CC BY-SA 2.0",
        ),
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
        **object_image(
            "knob",
            "https://live.staticflickr.com/8252/8636584683_7655894912_b.jpg",
            "https://www.flickr.com/photos/33907867@N02/8636584683",
            "CC BY 2.0",
        ),
    ),
    "locker": ObjectTemplate(
        "locker",
        "locker",
        "储物柜",
        NodeType.FIXED_OBJECT,
        {"is_open": False, "is_dirty": False},
        ["move", "open", "close"],
        "wall",
        **object_image(
            "locker",
            "https://live.staticflickr.com/2652/4049890918_0d59cffa8b_b.jpg",
            "https://www.flickr.com/photos/10559879@N00/4049890918",
            "CC BY-SA 2.0",
        ),
    ),
    "machine": ObjectTemplate(
        "machine",
        "machine",
        "机器",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "room",
        **object_image(
            "machine",
            "https://live.staticflickr.com/4126/5084396399_099ae9052a_b.jpg",
            "https://www.flickr.com/photos/35387910@N04/5084396399",
            "CC BY 2.0",
        ),
    ),
    "medical_cart": ObjectTemplate(
        "medical_cart",
        "medical cart",
        "医疗推车",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["move", "pick", "place"],
        "room",
        **commons_image("medical_cart", "A Grey Wooden Furniture Dolly (46138039674).jpg", "CC BY 2.0"),
    ),
    "medical_form": ObjectTemplate(
        "medical_form",
        "medical form",
        "医疗表单",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
        **object_image(
            "medical_form",
            "https://live.staticflickr.com/44/182613360_6d76db726a_b.jpg",
            "https://www.flickr.com/photos/95728450@N00/182613360",
            "CC BY 2.0",
        ),
    ),
    "medicine_box": ObjectTemplate(
        "medicine_box",
        "medicine box",
        "药盒",
        NodeType.MOVABLE_OBJECT,
        {"is_open": False},
        ["pick", "place", "open", "close"],
        "shelf",
        **object_image(
            "medicine_box",
            "https://live.staticflickr.com/7358/16401904015_63d28b93ff_b.jpg",
            "https://www.flickr.com/photos/50398299@N08/16401904015",
            "CC BY 2.0",
        ),
    ),
    "medicine_fridge": ObjectTemplate(
        "medicine_fridge",
        "medicine fridge",
        "药品冰箱",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "wall",
        **object_image(
            "medicine_fridge",
            "https://commons.wikimedia.org/wiki/Special:FilePath/Open%20refrigerator%20with%20food%20at%20night.jpg?width=256",
            "https://commons.wikimedia.org/wiki/File:Open_refrigerator_with_food_at_night.jpg",
            "CC BY-SA 4.0",
        ),
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
        **object_image(
            "milk",
            "https://live.staticflickr.com/28/57868022_2e7a61745f_b.jpg",
            "https://www.flickr.com/photos/20214151@N00/57868022",
            "CC BY 2.0",
        ),
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
        **object_image(
            "nurse_uniform",
            "https://live.staticflickr.com/7419/8730971487_0bfe22f4f6_b.jpg",
            "https://www.flickr.com/photos/95527077@N05/8730971487",
            "CC BY 2.0",
        ),
    ),
    "prescription_sheet": ObjectTemplate(
        "prescription_sheet",
        "prescription sheet",
        "处方单",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
        **object_image(
            "prescription_sheet",
            "https://upload.wikimedia.org/wikipedia/commons/2/24/Drug_prescription_paper.jpg",
            "https://commons.wikimedia.org/w/index.php?curid=147671317",
            "CC0 1.0",
        ),
    ),
    "printer": ObjectTemplate(
        "printer",
        "printer",
        "打印机",
        NodeType.FIXED_OBJECT,
        {"is_on": False, "is_dirty": False},
        ["move", "press", "brush"],
        "table",
        **object_image(
            "printer",
            "https://live.staticflickr.com/5137/5391086354_1a425d89b6.jpg",
            "https://www.flickr.com/photos/77071923@N00/5391086354",
            "CC BY 2.0",
        ),
    ),
    "receipt": ObjectTemplate(
        "receipt",
        "receipt",
        "收据",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
        **object_image(
            "receipt",
            "https://live.staticflickr.com/2787/4391281523_5eb55604cb_b.jpg",
            "https://www.flickr.com/photos/23269701@N02/4391281523",
            "CC BY 2.0",
        ),
    ),
    "refrigerated_medicine": ObjectTemplate(
        "refrigerated_medicine",
        "refrigerated medicine",
        "冷藏药品",
        NodeType.MOVABLE_OBJECT,
        {"temperature": "cold"},
        [],
        "container",
        **object_image(
            "refrigerated_medicine",
            "https://live.staticflickr.com/3210/2988216443_9e1af5375f_b.jpg",
            "https://www.flickr.com/photos/31064702@N05/2988216443",
            "CC BY 2.0",
        ),
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
        **object_image(
            "shelf",
            "https://live.staticflickr.com/7181/7044914609_075f5fb689_b.jpg",
            "https://www.flickr.com/photos/22526649@N03/7044914609",
            "CC BY-SA 2.0",
        ),
    ),
    "signboard": ObjectTemplate(
        "signboard",
        "signboard",
        "标牌",
        NodeType.FIXED_OBJECT,
        {"is_dirty": False},
        ["move"],
        "wall",
        **object_image(
            "signboard",
            "https://live.staticflickr.com/65535/52413992057_93376397ba_b.jpg",
            "https://www.flickr.com/photos/92842970@N00/52413992057",
            "CC BY-SA 2.0",
        ),
    ),
    "stationery": ObjectTemplate(
        "stationery",
        "stationery",
        "文具",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
        **object_image(
            "stationery",
            "https://live.staticflickr.com/5135/5418393428_35cfcdd95b_b.jpg",
            "https://www.flickr.com/photos/42931449@N07/5418393428",
            "CC BY 2.0",
        ),
    ),
    "syringe": ObjectTemplate(
        "syringe",
        "syringe",
        "注射器",
        NodeType.MOVABLE_OBJECT,
        {},
        ["pick", "place"],
        "surface",
        **object_image(
            "syringe",
            "https://upload.wikimedia.org/wikipedia/commons/6/66/Syringe_medicine.jpg",
            "https://commons.wikimedia.org/w/index.php?curid=77380406",
            "CC0 1.0",
        ),
    ),
    "toilet_brush": ObjectTemplate(
        "toilet_brush",
        "toilet brush",
        "马桶刷",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place", "brush"],
        "bathroom",
        **object_image(
            "toilet_brush",
            "https://live.staticflickr.com/7269/7128609703_813bc5a86b.jpg",
            "https://www.flickr.com/photos/28040596@N08/7128609703",
            "CC BY 2.0",
        ),
    ),
    "toothbrush": ObjectTemplate(
        "toothbrush",
        "toothbrush",
        "牙刷",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place", "brush"],
        "surface",
        **object_image(
            "toothbrush",
            "https://live.staticflickr.com/65535/11693757123_3dae068266_b.jpg",
            "https://www.flickr.com/photos/26782864@N00/11693757123",
            "CC BY 2.0",
        ),
    ),
    "toothpaste": ObjectTemplate(
        "toothpaste",
        "toothpaste",
        "牙膏",
        NodeType.MOVABLE_OBJECT,
        {"is_dirty": False},
        ["pick", "place"],
        "surface",
        **object_image("toothpaste"),
    ),
    "trash_bin": ObjectTemplate(
        "trash_bin",
        "trash bin",
        "垃圾桶",
        NodeType.FIXED_OBJECT,
        {},
        ["move"],
        "room",
        **object_image(
            "trash_bin",
            "https://live.staticflickr.com/7014/6448517855_2822c7022b_b.jpg",
            "https://www.flickr.com/photos/14818554@N05/6448517855",
            "CC BY 2.0",
        ),
        capabilities=(CLEANABLE, FILLABLE, PLACE_TARGET),
    ),
    "vegetable": ObjectTemplate(
        "vegetable",
        "vegetable",
        "蔬菜",
        NodeType.MOVABLE_OBJECT,
        {},
        [],
        "shelf",
        **object_image(
            "vegetable",
            "https://live.staticflickr.com/2281/2409582661_22387a9d53.jpg",
            "https://www.flickr.com/photos/19475163@N00/2409582661",
            "CC BY-SA 2.0",
        ),
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
        **object_image(
            "water_dispenser",
            "https://live.staticflickr.com/2/2327979_19d7b1f323_b.jpg",
            "https://www.flickr.com/photos/84108876@N00/2327979",
            "CC BY 2.0",
        ),
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
        **object_image(
            "wheelchair",
            "https://live.staticflickr.com/7548/27014559330_864474fd46_b.jpg",
            "https://www.flickr.com/photos/141290938@N03/27014559330",
            "CC BY 2.0",
        ),
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
            "image_path": None,
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
        "image_path": spec.get("image_path"),
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
            "clothes",
            "plant",
        ],
    }
    return list(room_map.get(room_type, []))
