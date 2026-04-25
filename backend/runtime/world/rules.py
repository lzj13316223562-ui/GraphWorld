from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable

from ..engine.events import log_event
from ..schema.home_schema import canonical_semantic_type


RuleFn = Callable[[dict, int], None]


class RuntimeRules(ABC):
    @abstractmethod
    def apply(self, state: dict, step: int) -> None:
        raise NotImplementedError


class HomeRules(RuntimeRules):
    def _node(self, state: dict, node_id: str) -> dict | None:
        return state.get("nodes", {}).get(node_id)

    def _states(self, state: dict, node_id: str) -> dict:
        node = self._node(state, node_id)
        if not node:
            return {}
        return node.setdefault("states", {})

    def _children(self, state: dict, parent_id: str) -> list[str]:
        node = self._node(state, parent_id)
        return list((node or {}).get("child") or [])

    def _parent_id(self, state: dict, node_id: str) -> str:
        return str(state.get("parent_of", {}).get(node_id) or "")

    def _apply_appliance_rules(self, state: dict, step: int) -> None:
        for node_id, node in state.get("nodes", {}).items():
            semantic_type = canonical_semantic_type(node)
            if semantic_type not in {"washer", "dishwasher"}:
                continue
            states = node.setdefault("states", {})
            if not bool(states.get("is_on", False)):
                continue
            remaining = max(0, int(states.get("cycle_remaining", 0)))
            if remaining <= 0:
                remaining = 3
            remaining -= 1
            states["cycle_remaining"] = remaining
            if remaining > 0:
                continue
            states["is_on"] = False
            for child_id in self._children(state, node_id):
                child = self._node(state, child_id)
                if not child:
                    continue
                child_states = child.setdefault("states", {})
                child_semantic = canonical_semantic_type(child)
                if semantic_type == "washer" and child_semantic in {"clothes", "socks", "towel"}:
                    child_states["is_dirty"] = False
                    child_states["is_wet"] = True
                    child_states["is_dry"] = False
                if semantic_type == "dishwasher" and child_semantic in {"bowl", "plate", "cup"}:
                    child_states["is_dirty"] = False
                    child_states["is_clean"] = True
                    child_states["is_wet"] = False
                    child_states["is_dry"] = True
            log_event(state, step, "appliance_cycle_complete", f"{node_id} completed its cycle")

    def _apply_clothes_rules(self, state: dict, step: int) -> None:
        for node_id, node in state.get("nodes", {}).items():
            if canonical_semantic_type(node) not in {"clothes", "socks", "towel"}:
                continue
            states = node.setdefault("states", {})
            parent_id = self._parent_id(state, node_id)
            parent = self._node(state, parent_id) or {}
            if canonical_semantic_type(parent) == "drying_rack" and bool(states.get("is_wet", False)):
                dry_remaining = max(0, int(states.get("dry_remaining", 2)))
                dry_remaining -= 1
                states["dry_remaining"] = dry_remaining
                if dry_remaining <= 0:
                    states["is_wet"] = False
                    states["is_dry"] = True
                    states.pop("dry_remaining", None)
                    log_event(state, step, "clothes_dried", f"{node_id} dried on {parent_id}")

    def _apply_food_rules(self, state: dict, step: int) -> None:
        supported = {"vegetable", "fruit", "yogurt", "drink", "milk", "juice", "raw_food", "cooked_food"}
        for node_id, node in state.get("nodes", {}).items():
            semantic_type = canonical_semantic_type(node)
            if semantic_type not in supported:
                continue
            states = node.setdefault("states", {})
            parent_id = self._parent_id(state, node_id)
            parent = self._node(state, parent_id) or {}
            in_fridge = canonical_semantic_type(parent) in {"refrigerator", "fridge"}
            freshness = float(states.get("freshness", 1.0))
            was_rotten = bool(states.get("is_rotten", False))
            freshness_loss = 0.01 if in_fridge else 0.04
            freshness = max(0.0, freshness - freshness_loss)
            states["freshness"] = round(freshness, 4)
            states["temperature"] = "cold" if in_fridge else "room"
            states["is_rotten"] = freshness <= 0.25
            if states["is_rotten"] and not was_rotten:
                log_event(state, step, "food_rotten", f"{node_id} has become rotten")

    def _apply_air_conditioner_rules(self, state: dict, step: int) -> None:
        for node_id, node in state.get("nodes", {}).items():
            if canonical_semantic_type(node) != "air_conditioner":
                continue
            states = node.setdefault("states", {})
            states.setdefault("target_temperature", 24.0)
            states.setdefault("mode", "cool")
            states.setdefault("fan_level", 2)
            if not bool(states.get("is_on", False)):
                continue
            mode = str(states.get("mode") or "cool").lower()
            if mode not in {"cool", "heat", "fan"}:
                states["mode"] = "cool"
            states["fan_level"] = max(1, min(4, int(states.get("fan_level", 2))))

    def _apply_sink_rules(self, state: dict, step: int) -> None:
        for node_id, node in state.get("nodes", {}).items():
            if canonical_semantic_type(node) != "sink":
                continue
            states = node.setdefault("states", {})
            controlled_by_on = False
            for edge in state.get("control_edges", []):
                if str(edge.get("target_id") or "") != node_id:
                    continue
                source_id = str(edge.get("source_id") or "")
                source_states = self._states(state, source_id)
                controlled_by_on = controlled_by_on or bool(source_states.get("is_on", False))
            fill_level = float(states.get("fill_level", 0.0))
            fill_level += 0.25 if controlled_by_on else -0.12
            fill_level = min(1.0, max(0.0, fill_level))
            states["fill_level"] = round(fill_level, 4)
            states["is_full"] = fill_level >= 0.85
            for child_id in self._children(state, node_id):
                child = self._node(state, child_id)
                if not child:
                    continue
                child_states = child.setdefault("states", {})
                if canonical_semantic_type(child) in {"bowl", "plate", "cup"} and controlled_by_on:
                    child_states["is_dirty"] = False
                    child_states["is_clean"] = True
                    child_states["is_wet"] = True
                    child_states["is_dry"] = False

    def _apply_plant_rules(self, state: dict, step: int) -> None:
        for node_id, node in state.get("nodes", {}).items():
            if canonical_semantic_type(node) != "plant":
                continue
            states = node.setdefault("states", {})
            vitality = float(states.get("vitality", 1.0))
            was_wilted = bool(states.get("is_wilted", False))
            vitality = max(0.0, vitality - 0.015)
            states["vitality"] = round(vitality, 4)
            states["is_wilted"] = vitality <= 0.3
            if states["is_wilted"] and not was_wilted:
                log_event(state, step, "plant_wilted", f"{node_id} is wilted")

    def _apply_sanitary_rules(self, state: dict, step: int) -> None:
        for node_id, node in state.get("nodes", {}).items():
            semantic_type = canonical_semantic_type(node)
            if semantic_type not in {"toilet", "trash_bin"}:
                continue
            states = node.setdefault("states", {})
            if semantic_type == "toilet":
                cleanliness = float(states.get("cleanliness", 1.0))
                states.setdefault("is_dirty", cleanliness <= 0.45)
            if semantic_type == "trash_bin":
                fill_level = float(states.get("fill_level", 0.0))
                states["is_full"] = fill_level >= 0.75

    def _apply_dishware_rules(self, state: dict, step: int) -> None:
        for node_id, node in state.get("nodes", {}).items():
            if canonical_semantic_type(node) not in {"bowl", "plate", "cup"}:
                continue
            states = node.setdefault("states", {})
            parent = self._node(state, self._parent_id(state, node_id)) or {}
            if canonical_semantic_type(parent) == "counter" and bool(states.get("is_wet", False)):
                states["is_wet"] = False
                states["is_dry"] = True

    def apply(self, state: dict, step: int) -> None:
        for rule in (
            self._apply_appliance_rules,
            self._apply_air_conditioner_rules,
            self._apply_clothes_rules,
            self._apply_food_rules,
            self._apply_sink_rules,
            self._apply_plant_rules,
            self._apply_sanitary_rules,
            self._apply_dishware_rules,
        ):
            rule(state, step)


_DEFAULT_RULES = HomeRules()


def apply_runtime_rules(state: dict, step: int) -> None:
    _DEFAULT_RULES.apply(state, step)


__all__ = ["HomeRules", "RuntimeRules", "apply_runtime_rules"]
