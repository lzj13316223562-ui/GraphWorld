from __future__ import annotations

import copy
from typing import Any

from backend.core.actions import ActionType
from backend.core.edges import PARENT_RELATIONS, ROOM_CONNECTIVITY_RELATIONS
from backend.core.assets.npc_library import get_event_spec
from backend.core.transition_rules import apply_action_transition, apply_timed_transitions
from .validator import validate_action


def _scene_nodes(scene: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(scene.get("nodes"), list):
        return copy.deepcopy(scene.get("nodes") or [])
    if isinstance(scene.get("node"), dict):
        return copy.deepcopy(list((scene.get("node") or {}).values()))
    return []


def _scene_edges(scene: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(scene.get("edges"), list):
        return copy.deepcopy(scene.get("edges") or [])
    if isinstance(scene.get("edge"), dict):
        return copy.deepcopy(list((scene.get("edge") or {}).values()))
    return []


class SceneGraph:
    def __init__(self, scene: dict[str, Any]):
        self.scene_name = str(scene.get("scene_name") or "scene")
        self.nodes = {str(node["id"]): node for node in _scene_nodes(scene) if node.get("id")}
        self.edges = _scene_edges(scene)
        self.world_state = copy.deepcopy(scene.get("world_state") or {})
        self.world_state.setdefault("step", 0)
        self.world_state.setdefault("event_log", [])
        self.refresh_indices()

    def refresh_indices(self) -> None:
        self.parent_of: dict[str, str] = {}
        self.relation_of: dict[str, str] = {}
        for node_id, node in self.nodes.items():
            parent = str(node.get("parent") or "")
            if parent:
                self.parent_of[node_id] = parent
                self.relation_of[node_id] = str(node.get("runtime_relation") or "in")
        for edge in self.edges:
            if (edge.get("properties") or {}).get("runtime") is True:
                continue
            relation = str(edge.get("relation") or "").lower()
            source = str(edge.get("source_id") or "")
            target = str(edge.get("target_id") or "")
            if relation in PARENT_RELATIONS and source and target and target not in self.parent_of:
                self.parent_of[target] = source
                self.relation_of[target] = relation
        self.room_of = {node_id: self.room_for(node_id) for node_id in self.nodes}
        self.control_edges = [edge for edge in self.edges if str(edge.get("relation") or "").lower() == "controls"]
        self.room_edges = [
            edge
            for edge in self.edges
            if str(edge.get("relation") or "").lower() in ROOM_CONNECTIVITY_RELATIONS
        ]

    def room_for(self, node_id: str) -> str:
        current = node_id
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            node = self.nodes.get(current) or {}
            if str(node.get("node_type") or "") == "room":
                return current
            current = self.parent_of.get(current, "")
        return ""

    def state_for_rules(self) -> dict[str, Any]:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "world_state": self.world_state,
            "parent_of": self.parent_of,
            "relation_of": self.relation_of,
            "room_of": self.room_of,
            "control_edges": self.control_edges,
            "room_edges": self.room_edges,
        }

    def node(self, node_id: str) -> dict[str, Any]:
        return self.nodes.get(str(node_id)) or {}

    def nodes_by_semantic(self, semantic_type: str, room_id: str = "") -> list[str]:
        node_ids = []
        for node_id, node in self.nodes.items():
            if str(node.get("semantic_type") or "") != semantic_type:
                continue
            if room_id and self.room_of.get(node_id) != room_id:
                continue
            node_ids.append(node_id)
        return node_ids

    def adjacent_rooms(self, room_id: str) -> set[str]:
        adjacent: set[str] = set()
        for edge in self.room_edges:
            source = str(edge.get("source_id") or "")
            target = str(edge.get("target_id") or "")
            if source == room_id:
                adjacent.add(target)
            if target == room_id:
                adjacent.add(source)
        return adjacent

    def target_reachable_from_room(self, target_id: str, room_id: str) -> bool:
        if not room_id:
            return False
        if self.room_of.get(target_id) == room_id:
            return True
        target = self.node(target_id)
        return room_id in {str(item) for item in target.get("connected_rooms") or []}

    def has_structural_door_between(self, room_a: str, room_b: str) -> bool:
        pair = {room_a, room_b}
        for node in self.nodes.values():
            if str(node.get("door_kind") or "") != "structural":
                continue
            if pair.issubset({str(room_id) for room_id in node.get("connected_rooms") or []}):
                return True
        return False

    def log(self, event_type: str, detail: str, **payload: Any) -> None:
        item = {
            "step": int(self.world_state.get("step") or 0),
            "type": event_type,
            "detail": detail,
        }
        item.update(payload)
        self.world_state.setdefault("event_log", []).append(item)

    def move_node(self, node_id: str, parent_id: str, relation: str) -> None:
        node = self.nodes.get(node_id)
        if not node:
            return
        node["parent"] = parent_id
        node["runtime_relation"] = relation
        self.parent_of[node_id] = parent_id
        self.relation_of[node_id] = relation
        self.room_of[node_id] = parent_id if str(self.node(parent_id).get("node_type") or "") == "room" else self.room_for(parent_id)

    def set_node_states(self, node_id: str, **updates: Any) -> None:
        node = self.nodes.get(node_id)
        if node:
            node.setdefault("states", {}).update(updates)

    def held_by(self, agent_id: str) -> str:
        for node_id, parent_id in self.parent_of.items():
            if parent_id == agent_id and self.relation_of.get(node_id) == "held_by":
                return node_id
        return ""

    def sync_runtime_edges(self) -> None:
        runtime_relations = {"at", "in", "on", "near", "held_by"}
        self.edges = [
            edge
            for edge in self.edges
            if (edge.get("properties") or {}).get("runtime") is not True
            and not (
                str(edge.get("relation") or "").lower() in runtime_relations
                and str(edge.get("target_id") or "") in self.parent_of
            )
        ]
        for node_id, parent_id in sorted(self.parent_of.items()):
            if node_id not in self.nodes or parent_id not in self.nodes:
                continue
            self.edges.append(
                {
                    "source_id": parent_id,
                    "target_id": node_id,
                    "relation": self.relation_of.get(node_id, "in"),
                    "edge_type": "runtime_edge",
                    "category": "runtime",
                    "properties": {"runtime": True},
                }
            )

    def to_scene(self) -> dict[str, Any]:
        self.refresh_indices()
        self.sync_runtime_edges()
        return {
            "scene_name": self.scene_name,
            "world_state": copy.deepcopy(self.world_state),
            "nodes": [copy.deepcopy(node) for node in self.nodes.values()],
            "edges": copy.deepcopy(self.edges),
        }


class System:
    def __init__(self, graph: SceneGraph):
        self.graph = graph


class RobotActionSystem(System):
    def validate(self, action: dict[str, Any]):
        return validate_action(self.graph.state_for_rules(), action)

    def apply_action(self, action: dict[str, Any]) -> dict[str, Any]:
        action_name = str(action.get("action") or "").lower()
        agent_id = str(action.get("agent") or "robot_01")
        target_id = str(action.get("target") or "")
        object_id = str(action.get("object") or target_id)
        if not action_name:
            return {"ok": False, "reason": "missing action"}
        validation = self.validate(action)
        if not validation.ok:
            self.graph.log("robot_action_failed", validation.reason, action=copy.deepcopy(action))
            return {"ok": False, "reason": validation.reason}
        if action_name in {ActionType.OPEN.value, ActionType.CLOSE.value, ActionType.PRESS.value, ActionType.BRUSH.value, ActionType.FOLD.value, ActionType.DUMP.value}:
            failures = apply_action_transition(
                self.graph.state_for_rules(),
                action_name,
                agent_id,
                target_id,
                object_id=object_id,
                step=int(self.graph.world_state.get("step") or 0),
            )
            if failures:
                reason = "; ".join(failures)
                self.graph.log("robot_action_failed", reason, action=copy.deepcopy(action))
                return {"ok": False, "reason": reason}
            self.graph.log("robot_action", f"{agent_id} {action_name} {target_id}", action=copy.deepcopy(action))
            return {"ok": True}
        if action_name == ActionType.MOVE.value:
            relation = "at" if str(self.graph.node(target_id).get("node_type") or "") == "room" else "near"
            self.graph.move_node(agent_id, target_id, relation)
            self.graph.log("robot_action", f"{agent_id} moved to {target_id}", action=copy.deepcopy(action))
            return {"ok": True}
        if action_name == ActionType.PICK.value:
            self.graph.move_node(object_id, agent_id, "held_by")
            self.graph.log("robot_action", f"{agent_id} picked {object_id}", action=copy.deepcopy(action))
            return {"ok": True}
        if action_name == ActionType.PLACE.value:
            held = str(action.get("object") or self.graph.held_by(agent_id))
            if not held:
                return {"ok": False, "reason": "agent holds nothing"}
            target_semantic = str(self.graph.node(target_id).get("semantic_type") or "").lower()
            relation = "on" if target_semantic in {"drying_rack", "rack", "table", "counter", "shelf"} else "in"
            self.graph.move_node(held, target_id, relation)
            held_node = self.graph.node(held)
            held_semantic = str(held_node.get("semantic_type") or "").lower()
            held_states = held_node.setdefault("states", {})
            if held_semantic in {"shoes", "shoe"} and target_semantic in {"shoe_rack", "rack", "shelf"}:
                held_states["scattered"] = False
            if target_id in {"sink_bathroom", "sink_kitchen"} or target_semantic == "sink":
                held_states.pop("misplaced_near", None)
            if target_semantic == "trash_bin":
                target_states = self.graph.node(target_id).setdefault("states", {})
                target_states["is_dirty"] = True
            self.graph.log("robot_action", f"{agent_id} placed {held} {relation} {target_id}", action=copy.deepcopy(action))
            return {"ok": True}
        return {"ok": False, "reason": f"unsupported action: {action_name}"}


class HumanEventSystem(System):
    def _matches_states(self, node_id: str, expected: dict[str, Any]) -> bool:
        states = self.graph.node(node_id).get("states") or {}
        return all(states.get(key) == value for key, value in expected.items())

    def matching_nodes(self, query: Any, actor_id: str = "", *, states_are_match: bool = False) -> list[str]:
        is_precondition = query.__class__.__name__ == "EventPrecondition"
        target_id = str(getattr(query, "target", "") or "")
        match_parent = str(getattr(query, "match_parent", "") or "")
        if target_id and target_id != "human":
            if target_id not in self.graph.nodes:
                return []
            parent = str(getattr(query, "parent", "") or "")
            source_parent = parent if is_precondition else match_parent
            if source_parent and self.graph.parent_of.get(target_id) != source_parent:
                return []
            room = str(getattr(query, "room", "") or "")
            if is_precondition and room and self.graph.room_of.get(target_id) != room:
                return []
            relation_not = str(getattr(query, "relation_not", "") or "")
            if is_precondition and relation_not and self.graph.relation_of.get(target_id) == relation_not:
                return []
            match_states = dict(getattr(query, "match_states", {}) or {})
            if states_are_match and not match_states:
                match_states = dict(getattr(query, "states", {}) or {})
            if match_states and not self._matches_states(target_id, match_states):
                return []
            return [target_id]
        semantic_type = str(getattr(query, "semantic_type", "") or "")
        room = str(getattr(query, "room", "") or "")
        parent = str(getattr(query, "parent", "") or "")
        source_parent = parent if is_precondition else match_parent
        relation_not = str(getattr(query, "relation_not", "") or "")
        match_states = dict(getattr(query, "match_states", {}) or {})
        if states_are_match and not match_states:
            match_states = dict(getattr(query, "states", {}) or {})
        matches: list[str] = []
        for node_id, node in self.graph.nodes.items():
            if semantic_type and str(node.get("semantic_type") or "") != semantic_type:
                continue
            if source_parent and self.graph.parent_of.get(node_id) != source_parent:
                continue
            if room and self.graph.room_of.get(node_id) != room:
                continue
            if relation_not and self.graph.relation_of.get(node_id) == relation_not:
                continue
            if match_states and not self._matches_states(node_id, match_states):
                continue
            matches.append(node_id)
        return sorted(matches)

    def worn_matching_node(self, actor_id: str, semantic_type: str) -> str:
        fallback = ""
        for node_id in sorted(self.graph.nodes):
            if self.graph.parent_of.get(node_id) != actor_id:
                continue
            node = self.graph.node(node_id)
            if str(node.get("semantic_type") or "") != semantic_type:
                continue
            fallback = fallback or node_id
            if self.graph.relation_of.get(node_id) == "worn_by":
                return node_id
        return fallback

    def precondition_failures(self, event_id: str, actor_id: str) -> list[str]:
        spec = get_event_spec(event_id)
        if not spec:
            return []
        failures: list[str] = []
        for precondition in spec.preconditions:
            if precondition.kind == "has_node":
                if not self.matching_nodes(precondition, actor_id, states_are_match=True):
                    failures.append(precondition.description or f"no {precondition.semantic_type or precondition.target} available")
            elif precondition.kind == "has_semantics":
                needed = set(precondition.semantic_types)
                available = {
                    str(node.get("semantic_type") or "")
                    for node_id, node in self.graph.nodes.items()
                    if not precondition.room or self.graph.room_of.get(node_id) == precondition.room
                }
                if not needed.issubset(available):
                    failures.append(precondition.description or f"missing semantics: {sorted(needed - available)}")
        return failures

    def _resolved_parent(self, effect: Any, actor_id: str) -> tuple[str, str]:
        options = tuple(getattr(effect, "parent_options", ()) or ())
        if options:
            step = int(self.graph.world_state.get("step") or 0)
            offset = int(getattr(effect, "parent_index_offset", 0) or 0)
            if str(getattr(effect, "parent_index_mode", "") or "") == "day":
                index = ((step // 144) + offset) % len(options)
            else:
                index = (step + offset) % len(options)
            parent_id = str(options[index])
            relation_options = tuple(getattr(effect, "relation_options", ()) or ())
            relation = str(relation_options[index]) if index < len(relation_options) else str(effect.relation or "near")
            return parent_id, relation
        parent_id = actor_id if str(effect.parent or "") == "human" else str(effect.parent or "")
        return parent_id, str(effect.relation or "near")

    def move_actor(self, effect: Any, actor_id: str) -> None:
        parent_id, relation = self._resolved_parent(effect, actor_id)
        if parent_id:
            self.graph.move_node(actor_id, parent_id, relation)

    def set_state(self, effect: Any, actor_id: str) -> None:
        target_id = actor_id if str(effect.target or "") == "human" else str(effect.target or "")
        updates = dict(getattr(effect, "states", {}) or {})
        if effect.state:
            updates[str(effect.state)] = effect.value
        if target_id and updates:
            self.graph.set_node_states(target_id, **updates)

    def move_matching_node(self, effect: Any, actor_id: str) -> None:
        node_ids = self.matching_nodes(effect, actor_id)
        if not node_ids:
            return
        node_id = node_ids[0]
        if self.graph.relation_of.get(node_id) == "held_by" and self.graph.parent_of.get(node_id) != actor_id:
            return
        parent_id, relation = self._resolved_parent(effect, actor_id)
        if parent_id:
            self.graph.move_node(node_id, parent_id, relation)
        updates = dict(getattr(effect, "states", {}) or {})
        updates.update((getattr(effect, "states_by_parent", {}) or {}).get(parent_id, {}))
        transient = getattr(effect, "transient_states_by_index", {}) or {}
        if transient:
            step = int(self.graph.world_state.get("step") or 0)
            index = (step + int(getattr(effect, "parent_index_offset", 0) or 0)) % len(tuple(getattr(effect, "parent_options", ()) or (1,)))
            transient_updates = transient.get(index, {})
            state_keys = set().union(*(dict(value).keys() for value in transient.values()))
            for key in state_keys:
                if key not in transient_updates:
                    self.graph.nodes[node_id].setdefault("states", {}).pop(key, None)
            updates.update({key: value for key, value in transient_updates.items() if value is not None})
        if updates:
            self.graph.set_node_states(node_id, **updates)

    def move_worn_node(self, effect: Any, actor_id: str) -> None:
        node_id = self.worn_matching_node(actor_id, str(effect.semantic_type or ""))
        if not node_id:
            return
        parent_id, relation = self._resolved_parent(effect, actor_id)
        if parent_id:
            self.graph.move_node(node_id, parent_id, relation)
        updates = dict(getattr(effect, "states", {}) or {})
        updates.update((getattr(effect, "states_by_parent", {}) or {}).get(parent_id, {}))
        if updates:
            self.graph.set_node_states(node_id, **updates)

    def set_semantic_state(self, effect: Any, actor_id: str) -> None:
        updates = dict(getattr(effect, "states", {}) or {})
        if effect.state:
            updates[str(effect.state)] = effect.value
        for node_id in self.matching_nodes(effect, actor_id):
            self.graph.set_node_states(node_id, **updates)

    def increment_state(self, effect: Any, actor_id: str) -> None:
        target_ids = [str(effect.target)] if effect.target else self.matching_nodes(effect, actor_id)
        for node_id in target_ids:
            if node_id not in self.graph.nodes or not effect.state:
                continue
            states = self.graph.nodes[node_id].setdefault("states", {})
            value = float(states.get(str(effect.state), 0.0)) + float(effect.amount or 0.0)
            if effect.min_value is not None:
                value = max(float(effect.min_value), value)
            if effect.max_value is not None:
                value = min(float(effect.max_value), value)
            value = round(value, 2)
            updates: dict[str, Any] = {str(effect.state): value}
            if effect.threshold_state:
                if effect.threshold_op == "<=":
                    updates[str(effect.threshold_state)] = value <= float(effect.threshold_value)
                elif effect.threshold_op == ">=":
                    updates[str(effect.threshold_state)] = value >= float(effect.threshold_value)
            self.graph.set_node_states(node_id, **updates)

    def apply_effect(self, effect: Any, actor_id: str) -> None:
        handlers = {
            "move_actor": lambda: self.move_actor(effect, actor_id),
            "set_state": lambda: self.set_state(effect, actor_id),
            "move_matching_node": lambda: self.move_matching_node(effect, actor_id),
            "move_worn_node": lambda: self.move_worn_node(effect, actor_id),
            "set_semantic_state": lambda: self.set_semantic_state(effect, actor_id),
            "increment_state": lambda: self.increment_state(effect, actor_id),
        }
        handler = handlers.get(str(effect.kind or ""))
        if handler:
            handler()

    def should_apply_effect(self, effect: Any, payload: dict[str, Any]) -> bool:
        timing = str(getattr(effect, "timing", "every_step") or "every_step")
        if timing == "period_start":
            return bool(payload.get("period_start", False))
        if timing == "period_end":
            return bool(payload.get("period_end", False))
        return True

    def apply_human_event(self, event: str | dict[str, Any]) -> dict[str, Any]:
        payload = {"event": event} if isinstance(event, str) else copy.deepcopy(event)
        event_id = str(payload.get("event") or payload.get("activity") or "")
        actor_id = str(payload.get("actor") or payload.get("agent") or "human_resident")
        spec = get_event_spec(event_id)
        failures = self.precondition_failures(event_id, actor_id)
        actor = self.graph.nodes.get(actor_id)
        if actor:
            actor.setdefault("states", {})["current_activity"] = event_id
        if spec:
            effects = spec.effects_on_failure if failures else spec.effects_on_success
            for effect in effects:
                if self.should_apply_effect(effect, payload):
                    self.apply_effect(effect, actor_id)
        self.graph.log(
            "human_event",
            f"{actor_id} event {event_id}",
            event=event_id,
            actor=actor_id,
            ok=not failures,
            failures=failures,
            period_start=bool(payload.get("period_start", False)),
            period_end=bool(payload.get("period_end", False)),
        )
        return {"ok": not failures, "failures": failures}


class EnvironmentSystem(System):
    def advance_time(self) -> list[str]:
        completed = apply_timed_transitions(self.graph.state_for_rules(), int(self.graph.world_state.get("step") or 0))
        for node_id in completed:
            self.graph.log("timed_transition", f"{node_id} completed")
        self.graph.world_state["step"] = int(self.graph.world_state.get("step") or 0) + 1
        self.graph.refresh_indices()
        self.graph.sync_runtime_edges()
        return completed


class Perception:
    def __init__(self, graph: SceneGraph, *, confidence_horizon: int = 12):
        self.graph = graph
        self.confidence_horizon = max(1, int(confidence_horizon))
        self.last_seen: dict[str, dict[str, int]] = {}

    def visible_room_ids(self, agent_id: str) -> set[str]:
        current_room = self.graph.room_of.get(agent_id, "")
        visible_rooms = {current_room} if current_room else set()
        for room_id in self.graph.adjacent_rooms(current_room):
            if not self.graph.has_structural_door_between(current_room, room_id):
                visible_rooms.add(room_id)
        for node_id, node in self.graph.nodes.items():
            if str(node.get("semantic_type") or "") != "door":
                continue
            if not self.graph.target_reachable_from_room(node_id, current_room):
                continue
            if not bool((node.get("states") or {}).get("is_open", False)):
                continue
            visible_rooms.update(str(room_id) for room_id in node.get("connected_rooms") or [] if room_id in self.graph.nodes)
        return visible_rooms

    def robot_view(self, agent_id: str = "robot_01") -> dict[str, Any]:
        step = int(self.graph.world_state.get("step") or 0)
        visible_rooms = self.visible_room_ids(agent_id)
        visible_ids = {
            node_id
            for node_id in self.graph.nodes
            if node_id == agent_id or self.graph.room_of.get(node_id) in visible_rooms or node_id in visible_rooms
        }
        for node_id, node in self.graph.nodes.items():
            if str(node.get("door_kind") or "") == "structural" and any(
                self.graph.target_reachable_from_room(node_id, room_id) for room_id in visible_rooms
            ):
                visible_ids.add(node_id)
        for node_id, node in self.graph.nodes.items():
            if str(node.get("door_kind") or "") != "device":
                continue
            parent_id = self.graph.parent_of.get(node_id, "")
            if parent_id in visible_ids and bool((node.get("states") or {}).get("is_open", False)):
                visible_ids.update(child_id for child_id, child_parent in self.graph.parent_of.items() if child_parent == parent_id)
        seen = self.last_seen.setdefault(agent_id, {})
        for room_id in visible_rooms:
            seen[room_id] = step
        confidence = {}
        for node_id, node in self.graph.nodes.items():
            if str(node.get("node_type") or "") != "room":
                continue
            age = step - seen.get(node_id, -self.confidence_horizon)
            confidence[node_id] = round(max(0.0, 1.0 - (age / self.confidence_horizon)), 4)
        return {
            "scene_name": self.graph.scene_name,
            "world_state": {**copy.deepcopy(self.graph.world_state), "visible_rooms": sorted(visible_rooms), "confidence_by_room": confidence},
            "nodes": [copy.deepcopy(self.graph.nodes[node_id]) for node_id in sorted(visible_ids)],
            "edges": [
                copy.deepcopy(edge)
                for edge in self.graph.edges
                if str(edge.get("source_id") or "") in visible_ids and str(edge.get("target_id") or "") in visible_ids
            ],
        }


class Orchestrator:
    def __init__(self, scene: dict[str, Any], *, confidence_horizon: int = 12):
        self.graph = SceneGraph(scene)
        self.robot_actions = RobotActionSystem(self.graph)
        self.human_events = HumanEventSystem(self.graph)
        self.environment = EnvironmentSystem(self.graph)
        self.perception = Perception(self.graph, confidence_horizon=confidence_horizon)

    def step(
        self,
        robot_actions: list[dict[str, Any]] | None = None,
        human_events: list[str | dict[str, Any]] | None = None,
        *,
        capture_robot_scene: bool = True,
        capture_scene: bool = True,
    ) -> dict[str, Any]:
        results = {"robot_actions": [], "human_events": []}
        for action in robot_actions or []:
            results["robot_actions"].append(self.robot_actions.apply_action(action))
        if capture_robot_scene:
            results["robot_scene"] = self.graph.to_scene()
        for event in human_events or []:
            results["human_events"].append(self.human_events.apply_human_event(event))
        self.environment.advance_time()
        if capture_scene:
            results["scene"] = self.graph.to_scene()
        return results


def run_runtime(
    scene: dict[str, Any],
    steps: int,
    *,
    robot_actions_by_step: list[list[dict[str, Any]]] | None = None,
    human_events_by_step: list[list[str | dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    orchestrator = Orchestrator(scene)
    history = [orchestrator.graph.to_scene()]
    for step in range(max(0, int(steps))):
        actions = (robot_actions_by_step or [])[step] if step < len(robot_actions_by_step or []) else []
        events = (human_events_by_step or [])[step] if step < len(human_events_by_step or []) else []
        orchestrator.step(actions, events)
        history.append(orchestrator.graph.to_scene())
    return {"scene": orchestrator.graph.to_scene(), "history": history, "orchestrator": orchestrator}


__all__ = [
    "EnvironmentSystem",
    "HumanEventSystem",
    "Orchestrator",
    "Perception",
    "RobotActionSystem",
    "SceneGraph",
    "System",
    "run_runtime",
]
