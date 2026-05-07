from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    FLOOR = "floor"
    ROOM = "room"
    FIXED_OBJECT = "fixed_object"
    MOVABLE_OBJECT = "movable_object"
    CONTROL_OBJECT = "control_object"
    ROBOT = "robot"
    HUMAN = "human"


@dataclass
class Node:
    id: str
    semantic_type: str
    name: str
    name_cn: str
    node_type: NodeType
    states: dict[str, Any] = field(default_factory=dict)
    interactive_actions: list[str] = field(default_factory=list)
    parent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "name_cn": self.name_cn,
            "node_type": self.node_type.value,
            "semantic_type": self.semantic_type,
            "parent": self.parent,
            "states": deepcopy(self.states),
            "interactive_actions": list(self.interactive_actions),
        }


@dataclass
class Floor(Node):
    floor_number: int = 1

    def __init__(
        self,
        id: str,
        semantic_type: str = "floor",
        name: str = "floor",
        name_cn: str = "楼层",
        *,
        states: dict[str, Any] | None = None,
        interactive_actions: list[str] | None = None,
        parent: str | None = None,
        floor_number: int = 1,
    ) -> None:
        super().__init__(id, semantic_type, name, name_cn, NodeType.FLOOR, dict(states or {}), list(interactive_actions or []), parent)
        self.floor_number = floor_number

    def to_dict(self) -> dict[str, Any]:
        node = super().to_dict()
        node["floor_number"] = self.floor_number
        return node


@dataclass
class Room(Node):
    floor_id: str | None = None

    def __init__(
        self,
        id: str,
        semantic_type: str = "room",
        name: str = "room",
        name_cn: str = "房间",
        *,
        states: dict[str, Any] | None = None,
        interactive_actions: list[str] | None = None,
        parent: str | None = None,
        floor_id: str | None = None,
    ) -> None:
        super().__init__(id, semantic_type, name, name_cn, NodeType.ROOM, dict(states or {}), list(interactive_actions or []), parent)
        self.floor_id = floor_id

    def to_dict(self) -> dict[str, Any]:
        node = super().to_dict()
        if self.floor_id:
            node["floor_id"] = self.floor_id
        return node


@dataclass
class FixedObject(Node):
    def __init__(
        self,
        id: str,
        semantic_type: str,
        name: str,
        name_cn: str,
        *,
        states: dict[str, Any] | None = None,
        interactive_actions: list[str] | None = None,
        parent: str | None = None,
    ) -> None:
        super().__init__(id, semantic_type, name, name_cn, NodeType.FIXED_OBJECT, dict(states or {}), list(interactive_actions or []), parent)


@dataclass
class MovableObject(Node):
    def __init__(
        self,
        id: str,
        semantic_type: str,
        name: str,
        name_cn: str,
        *,
        states: dict[str, Any] | None = None,
        interactive_actions: list[str] | None = None,
        parent: str | None = None,
    ) -> None:
        super().__init__(id, semantic_type, name, name_cn, NodeType.MOVABLE_OBJECT, dict(states or {}), list(interactive_actions or []), parent)


@dataclass
class ControlObject(Node):
    door_kind: str | None = None
    blocks_visibility: bool = False
    blocks_navigation: bool = False
    blocks_containment: bool = False
    requires_closed_to_start: bool = False
    parent_device_type: str | None = None

    def __init__(
        self,
        id: str,
        semantic_type: str,
        name: str,
        name_cn: str,
        *,
        states: dict[str, Any] | None = None,
        interactive_actions: list[str] | None = None,
        parent: str | None = None,
        door_kind: str | None = None,
        blocks_visibility: bool = False,
        blocks_navigation: bool = False,
        blocks_containment: bool = False,
        requires_closed_to_start: bool = False,
        parent_device_type: str | None = None,
    ) -> None:
        super().__init__(id, semantic_type, name, name_cn, NodeType.CONTROL_OBJECT, dict(states or {}), list(interactive_actions or []), parent)
        self.door_kind = door_kind
        self.blocks_visibility = blocks_visibility
        self.blocks_navigation = blocks_navigation
        self.blocks_containment = blocks_containment
        self.requires_closed_to_start = requires_closed_to_start
        self.parent_device_type = parent_device_type

    def to_dict(self) -> dict[str, Any]:
        node = super().to_dict()
        if self.door_kind:
            node["door_kind"] = self.door_kind
        if self.blocks_visibility:
            node["blocks_visibility"] = self.blocks_visibility
        if self.blocks_navigation:
            node["blocks_navigation"] = self.blocks_navigation
        if self.blocks_containment:
            node["blocks_containment"] = self.blocks_containment
        if self.requires_closed_to_start:
            node["requires_closed_to_start"] = self.requires_closed_to_start
        if self.parent_device_type:
            node["parent_device_type"] = self.parent_device_type
        return node


@dataclass
class Robot(Node):
    inventory: list[str] = field(default_factory=list)

    def __init__(
        self,
        id: str,
        semantic_type: str = "robot",
        name: str = "robot",
        name_cn: str = "机器人",
        *,
        states: dict[str, Any] | None = None,
        interactive_actions: list[str] | None = None,
        parent: str | None = None,
        inventory: list[str] | None = None,
    ) -> None:
        super().__init__(id, semantic_type, name, name_cn, NodeType.ROBOT, dict(states or {}), list(interactive_actions or []), parent)
        self.inventory = list(inventory or [])

    def to_dict(self) -> dict[str, Any]:
        node = super().to_dict()
        node["inventory"] = list(self.inventory)
        return node


@dataclass
class Human(Node):
    role: str = "human"

    def __init__(
        self,
        id: str,
        semantic_type: str = "human",
        name: str = "human",
        name_cn: str = "人类",
        *,
        states: dict[str, Any] | None = None,
        interactive_actions: list[str] | None = None,
        parent: str | None = None,
        role: str = "human",
    ) -> None:
        super().__init__(id, semantic_type, name, name_cn, NodeType.HUMAN, dict(states or {}), list(interactive_actions or []), parent)
        self.role = role

    def to_dict(self) -> dict[str, Any]:
        node = super().to_dict()
        node["role"] = self.role
        return node


CONTROL_OBJECT_TYPES = frozenset({"button", "door"})


def node_type_from_legacy(value: str) -> NodeType:
    normalized = str(value or "").strip().lower()
    if normalized in {"floor"}:
        return NodeType.FLOOR
    if normalized in {"room", "space"}:
        return NodeType.ROOM
    if normalized in {"movable", "movable_object"}:
        return NodeType.MOVABLE_OBJECT
    if normalized in {"control", "control_object"}:
        return NodeType.CONTROL_OBJECT
    if normalized in {"robot"}:
        return NodeType.ROBOT
    if normalized in {"human", "agent"}:
        return NodeType.HUMAN
    return NodeType.FIXED_OBJECT


__all__ = [
    "CONTROL_OBJECT_TYPES",
    "ControlObject",
    "FixedObject",
    "Floor",
    "Human",
    "MovableObject",
    "Node",
    "NodeType",
    "Robot",
    "Room",
    "node_type_from_legacy",
]
