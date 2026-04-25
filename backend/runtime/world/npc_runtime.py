from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
import copy

from backend.core.npc_library import DEFAULT_ROLE, get_default_npcs, planned_activity

from ..engine.events import log_event, move_actor, move_item, set_node_state
from ..schema.home_schema import canonical_semantic_type


def minute_of_day(world_state: dict, step: int | None = None) -> int:
    del step
    return int(world_state.get("time_min") or 0) % (24 * 60)


class NpcPolicy(ABC):
    def __init__(self, role: str) -> None:
        self.role = role

    def scheduled_activity(self, minute: int, day: int = 1) -> tuple[str, str, str]:
        return planned_activity(self.role, minute, day)

    @abstractmethod
    def step(self, state: dict, actor_id: str, step: int, minute: int) -> None:
        raise NotImplementedError


def _scene_type(state: dict) -> str:
    world = state.get("world_state") or {}
    name = str(world.get("scene_name") or state.get("scene_name") or "").lower()
    if "hospital" in name:
        return "hospital"
    return "home"


def _npc_specs_for_state(state: dict) -> list[dict]:
    return get_default_npcs(_scene_type(state))


def _schedule_role(node: dict) -> str:
    operation = str((node.get("property") or {}).get("operation") or "")
    for part in operation.split(";"):
        text = part.strip()
        if text.startswith("schedule_role="):
            return text.split("=", 1)[1].strip() or "resident"
    return "resident"


def ensure_default_npcs(state: dict) -> None:
    nodes = state.setdefault("nodes", {})
    parent_of = state.setdefault("parent_of", {})
    room_of = state.setdefault("room_of", {})
    for spec in _npc_specs_for_state(state):
        actor_id = spec["id"]
        node = nodes.get(actor_id)
        if node is None:
            node = {
                "id": actor_id,
                "name": spec["name"],
                "name_cn": spec["name_cn"],
                "node_type": "agent",
                "semantic_type": "human",
                "mobility": "agent",
                "property": {
                    "appearance": "",
                    "physical": "",
                    "operation": f"schedule_role={spec['role']}",
                },
                "affordance_count": 0,
                "parent": spec["parent"],
                "child": [],
                "interactive_actions": [],
                "states": {
                    "mood": 1.0,
                    "is_home": spec["room"] != "outside_home",
                    "current_activity": spec["activity"],
                    "role": spec["role"],
                    "persona": spec.get("persona") or spec["role"],
                    "needs_profile": ["food", "clothing", "hygiene"] if spec["role"] == "resident" else [],
                },
            }
            nodes[actor_id] = node
        else:
            node.setdefault("property", {})
            operation = str(node["property"].get("operation") or "")
            if "schedule_role=" not in operation:
                node["property"]["operation"] = (operation + "; " if operation else "") + f"schedule_role={spec['role']}"
        parent_of.setdefault(actor_id, spec["parent"])
        room_of.setdefault(actor_id, spec["room"])
        nodes[actor_id]["parent"] = parent_of[actor_id]


def _node(state: dict, node_id: str) -> dict | None:
    return state.get("nodes", {}).get(node_id)


def _actor_role(state: dict, actor_id: str) -> str:
    actor = state.get("nodes", {}).get(actor_id) or {}
    return str((actor.get("states") or {}).get("role") or "")


def _actors_in_room(state: dict, room_id: str, *, role: str | None = None) -> list[str]:
    room_of = state.get("room_of", {})
    nodes = state.get("nodes", {})
    matches: list[str] = []
    for actor_id, current_room in room_of.items():
        if current_room != room_id:
            continue
        node = nodes.get(actor_id) or {}
        if str(node.get("node_type") or "") != "agent":
            continue
        if role and _actor_role(state, actor_id) != role:
            continue
        matches.append(actor_id)
    return sorted(matches)


def _patient_needs_service(state: dict, actor_id: str) -> bool:
    actor = state.get("nodes", {}).get(actor_id) or {}
    activity = str((actor.get("states") or {}).get("current_activity") or "")
    return activity not in {"away", "departed", "departing", "off_shift"}


def _patient_service_flags(actor_states: dict) -> dict[str, bool]:
    return {
        "registration_done": bool(actor_states.get("registration_done", False)),
        "triage_done": bool(actor_states.get("triage_done", False)),
        "consultation_done": bool(actor_states.get("consultation_done", False)),
        "treatment_done": bool(actor_states.get("treatment_done", False)),
        "payment_done": bool(actor_states.get("payment_done", False)),
        "dispensing_done": bool(actor_states.get("dispensing_done", False)),
    }


def _mark_patient_stage_done(state: dict, patient_id: str, *, key: str, activity: str, step: int, message: str) -> None:
    actor = state.get("nodes", {}).get(patient_id) or {}
    actor_states = actor.setdefault("states", {})
    if bool(actor_states.get(key, False)):
        return
    actor_states[key] = True
    actor_states["current_activity"] = activity
    log_event(state, step, "hospital_service", message)


def _service_patients_in_room(state: dict, room_id: str) -> list[str]:
    return [
        actor_id
        for actor_id in _actors_in_room(state, room_id, role="patient")
        if _patient_needs_service(state, actor_id)
    ]


def _room_graph(state: dict) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = {}
    for edge in state.get("structural_edges", []):
        relation = str(edge.get("relation") or "").lower()
        if relation != "adjacent_to":
            continue
        source = str(edge.get("source_id") or "")
        target = str(edge.get("target_id") or "")
        if not source or not target:
            continue
        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)
    return adjacency


def _bfs_next_room(graph: dict[str, set[str]], current_room: str, target_room: str) -> str:
    if current_room == target_room:
        return current_room
    if current_room not in graph or target_room not in graph:
        return target_room
    queue = deque([(current_room, current_room)])
    visited = {current_room}
    while queue:
        room, first_hop = queue.popleft()
        for neighbor in sorted(graph.get(room, ())):
            if neighbor in visited:
                continue
            next_hop = neighbor if room == current_room else first_hop
            if neighbor == target_room:
                return next_hop
            visited.add(neighbor)
            queue.append((neighbor, next_hop))
    return target_room


def _door_for_room(state: dict, room_id: str) -> str:
    candidate = f"door_{room_id}"
    if candidate in state.get("nodes", {}):
        return candidate
    return ""


def _is_open(state: dict, node_id: str) -> bool:
    states = (state.get("nodes", {}).get(node_id) or {}).get("states") or {}
    if "is_open" in states:
        return bool(states["is_open"])
    if "isOpen" in states:
        return bool(states["isOpen"])
    return False


def _open_door_if_needed(state: dict, actor_id: str, room_id: str, step: int) -> bool:
    door_id = _door_for_room(state, room_id)
    if not door_id or _is_open(state, door_id):
        return False
    set_node_state(state, door_id, is_open=True, isOpen=True)
    log_event(state, step, "npc_open_door", f"{actor_id} opened {door_id} before entering {room_id}")
    return True


def _move_one_hop_towards_target(state: dict, actor_id: str, current_room: str, target_room: str, activity: str, step: int) -> bool:
    if current_room == target_room:
        return False
    if target_room == "outside_home":
        if current_room != "entrance":
            next_room = _bfs_next_room(_room_graph(state), current_room, "entrance")
            if next_room != current_room:
                if _open_door_if_needed(state, actor_id, next_room, step):
                    return True
                move_actor(state, actor_id, next_room, next_room, activity)
                log_event(state, step, "npc_move", f"{actor_id} moved from {current_room} to {next_room}")
                return True
        move_actor(state, actor_id, "outside_home", "outside_home", activity)
        log_event(state, step, "npc_move", f"{actor_id} left the scene")
        return True
    if current_room == "outside_home":
        move_actor(state, actor_id, "entrance", "entrance", activity)
        log_event(state, step, "npc_move", f"{actor_id} entered through entrance")
        return True

    next_room = _bfs_next_room(_room_graph(state), current_room, target_room)
    if next_room == current_room:
        return False
    if _open_door_if_needed(state, actor_id, next_room, step):
        return True
    move_actor(state, actor_id, next_room, next_room, activity)
    log_event(state, step, "npc_move", f"{actor_id} moved from {current_room} to {next_room}")
    return True


class ScheduledNpcPolicy(NpcPolicy):
    def on_arrival(self, state: dict, actor_id: str, activity: str, step: int) -> None:
        return

    def step(self, state: dict, actor_id: str, step: int, minute: int) -> None:
        day = int((state.get("world_state") or {}).get("day") or 1)
        target_parent, target_room, activity = self.scheduled_activity(minute, day)
        actor = state.get("nodes", {}).get(actor_id) or {}
        actor_states = actor.setdefault("states", {})
        actor_states["current_activity"] = activity
        current_room = state.get("room_of", {}).get(actor_id, "")
        if _move_one_hop_towards_target(state, actor_id, current_room, target_room, activity, step):
            return
        move_actor(state, actor_id, target_parent, target_room, activity)
        self.on_arrival(state, actor_id, activity, step)


class HospitalPatientPolicy(NpcPolicy):
    CARE_STAGE_PLAN = [
        ("registration_done", "registration", "registration", "waiting_registration"),
        ("triage_done", "triage", "triage", "waiting_triage"),
        ("consultation_done", "outpatient_clinic_1", "outpatient_clinic_1", "waiting_consultation"),
        ("treatment_done", "treatment_room", "treatment_room", "waiting_treatment"),
        ("payment_done", "payment", "payment", "payment"),
        ("dispensing_done", "pharmacy", "pharmacy", "waiting_pharmacy"),
    ]

    def step(self, state: dict, actor_id: str, step: int, minute: int) -> None:
        day = int((state.get("world_state") or {}).get("day") or 1)
        _, _, scheduled_activity = self.scheduled_activity(minute, day)
        actor = state.get("nodes", {}).get(actor_id) or {}
        actor_states = actor.setdefault("states", {})
        current_room = state.get("room_of", {}).get(actor_id, "")

        if scheduled_activity in {"away", "departed"}:
            actor_states["current_activity"] = scheduled_activity
            if current_room != "outside_home":
                _move_one_hop_towards_target(state, actor_id, current_room, "outside_home", scheduled_activity, step)
            return

        if scheduled_activity == "arriving":
            actor_states["current_activity"] = "arriving"
            if current_room != "entrance":
                _move_one_hop_towards_target(state, actor_id, current_room, "entrance", "arriving", step)
            else:
                move_actor(state, actor_id, "entrance", "entrance", "arriving")
            return

        flags = _patient_service_flags(actor_states)
        next_stage = next((item for item in self.CARE_STAGE_PLAN if not flags[item[0]]), None)
        if next_stage is None:
            actor_states["current_activity"] = "departing"
            _move_one_hop_towards_target(state, actor_id, current_room, "outside_home", "departing", step)
            return

        done_key, target_parent, target_room, waiting_activity = next_stage
        actor_states["current_activity"] = waiting_activity
        if current_room != target_room:
            _move_one_hop_towards_target(state, actor_id, current_room, target_room, waiting_activity, step)
            return
        if state.get("parent_of", {}).get(actor_id) != target_parent:
            move_actor(state, actor_id, target_parent, target_room, waiting_activity)

        if done_key == "payment_done":
            _mark_patient_stage_done(
                state,
                actor_id,
                key="payment_done",
                activity="payment_complete",
                step=step,
                message=f"{actor_id} completed payment",
            )


class HospitalStaffPolicy(NpcPolicy):
    TRANSIT_ACTIVITIES = {
        "off_shift",
        "walking_to_staff_room",
        "walking_to_registration",
        "walking_to_clinic",
        "walking_to_triage",
        "walking_to_waiting",
        "walking_to_treatment",
        "departing",
        "break",
    }

    SERVICE_IDLE_LABELS = {
        "registration_desk": "idle_at_registration",
        "consulting": "idle_in_clinic",
        "triage_support": "idle_at_triage",
        "patient_support": "idle_at_waiting_area",
        "treatment_support": "idle_at_treatment_room",
        "clinic_support": "idle_in_clinic",
        "pharmacy_dispensing": "idle_at_pharmacy",
    }

    SERVICE_ACTIVE_LABELS = {
        "registration_desk": "serving_registration",
        "consulting": "consulting",
        "triage_support": "triage_support",
        "patient_support": "patient_support",
        "treatment_support": "treatment_support",
        "clinic_support": "clinic_support",
        "pharmacy_dispensing": "dispensing",
    }

    def __init__(self, role: str, *, uniform_id: str = "", prep_parent: str = "staff_room") -> None:
        super().__init__(role)
        self.uniform_id = uniform_id
        self.prep_parent = prep_parent

    def _move_or_place(self, state: dict, actor_id: str, target_parent: str, target_room: str, activity: str, step: int) -> bool:
        current_room = state.get("room_of", {}).get(actor_id, "")
        if _move_one_hop_towards_target(state, actor_id, current_room, target_room, activity, step):
            return True
        if state.get("parent_of", {}).get(actor_id) != target_parent or state.get("room_of", {}).get(actor_id) != target_room:
            move_actor(state, actor_id, target_parent, target_room, activity)
            log_event(state, step, "npc_move", f"{actor_id} moved within {target_room} to {target_parent}")
            return True
        return False

    def _ensure_uniform(self, state: dict, actor_id: str, step: int) -> None:
        if not self.uniform_id:
            return
        if state.get("parent_of", {}).get(self.uniform_id) == actor_id:
            return
        if state.get("room_of", {}).get(self.uniform_id) != state.get("room_of", {}).get(actor_id):
            return
        move_item(state, self.uniform_id, actor_id, "worn_by")
        log_event(state, step, "npc_wear", f"{actor_id} wore {self.uniform_id}")

    def _service_label(self, state: dict, scheduled_activity: str, station_room: str) -> str:
        patients = _service_patients_in_room(state, station_room)
        if patients:
            return self.SERVICE_ACTIVE_LABELS.get(scheduled_activity, scheduled_activity)
        return self.SERVICE_IDLE_LABELS.get(scheduled_activity, scheduled_activity)

    def _service_target(self, state: dict, scheduled_activity: str, base_room: str) -> tuple[str, str]:
        if scheduled_activity == "clinic_station":
            if _service_patients_in_room(state, "treatment_room"):
                return ("treatment_room", "treatment_room")
            return ("outpatient_clinic_1", "outpatient_clinic_1")
        if scheduled_activity == "triage_station":
            return ("triage", "triage")
        if scheduled_activity == "treatment_station":
            if _service_patients_in_room(state, "treatment_room"):
                return ("treatment_room", "treatment_room")
            return ("triage", "triage")
        if scheduled_activity == "pharmacy_station":
            return ("pharmacy", "pharmacy")
        return (base_room, base_room)

    def _apply_service_event(self, state: dict, actor_id: str, scheduled_activity: str, station_room: str, step: int) -> None:
        patients = _service_patients_in_room(state, station_room)
        if not patients:
            return
        patient_id = patients[0]
        if scheduled_activity == "registration_desk":
            _mark_patient_stage_done(
                state,
                patient_id,
                key="registration_done",
                activity="registration_complete",
                step=step,
                message=f"{actor_id} completed registration for {patient_id}",
            )
            return
        if scheduled_activity == "triage_station":
            _mark_patient_stage_done(
                state,
                patient_id,
                key="triage_done",
                activity="triage_complete",
                step=step,
                message=f"{actor_id} completed triage for {patient_id}",
            )
            return
        if scheduled_activity == "clinic_station" and station_room == "outpatient_clinic_1":
            _mark_patient_stage_done(
                state,
                patient_id,
                key="consultation_done",
                activity="consultation_complete",
                step=step,
                message=f"{actor_id} completed consultation for {patient_id}",
            )
            return
        if scheduled_activity in {"clinic_station", "treatment_station"} and station_room == "treatment_room":
            _mark_patient_stage_done(
                state,
                patient_id,
                key="treatment_done",
                activity="treatment_complete",
                step=step,
                message=f"{actor_id} completed treatment for {patient_id}",
            )
            return
        if scheduled_activity == "pharmacy_station":
            _mark_patient_stage_done(
                state,
                patient_id,
                key="dispensing_done",
                activity="dispensing_complete",
                step=step,
                message=f"{actor_id} dispensed medicine to {patient_id}",
            )
            return

    def step(self, state: dict, actor_id: str, step: int, minute: int) -> None:
        day = int((state.get("world_state") or {}).get("day") or 1)
        target_parent, target_room, scheduled_activity = self.scheduled_activity(minute, day)
        actor = state.get("nodes", {}).get(actor_id) or {}
        actor_states = actor.setdefault("states", {})

        if scheduled_activity in self.TRANSIT_ACTIVITIES:
            actor_states["current_activity"] = scheduled_activity
            self._move_or_place(state, actor_id, target_parent, target_room, scheduled_activity, step)
            return

        if scheduled_activity == "preparing":
            actor_states["current_activity"] = "preparing"
            self._move_or_place(state, actor_id, target_parent or self.prep_parent, target_room, "preparing", step)
            self._ensure_uniform(state, actor_id, step)
            return

        service_parent, service_room = self._service_target(state, scheduled_activity, target_room)
        self._move_or_place(state, actor_id, service_parent, service_room, scheduled_activity, step)
        self._ensure_uniform(state, actor_id, step)

        label_key = scheduled_activity
        if scheduled_activity == "clinic_station":
            label_key = "consulting" if service_room == "outpatient_clinic_1" else "treatment_support"
        elif scheduled_activity == "triage_station":
            label_key = "triage_support"
        elif scheduled_activity == "treatment_station":
            label_key = "treatment_support"
        elif scheduled_activity == "pharmacy_station":
            label_key = "pharmacy_dispensing"
        actor_states["current_activity"] = self._service_label(state, label_key, service_room)
        self._apply_service_event(state, actor_id, scheduled_activity, service_room, step)


class ResidentPolicy(NpcPolicy):
    STAPLE_FOOD_IDS = ("milk_fridge_kitchen", "juice_fridge_kitchen", "vegetables_fridge_kitchen")

    def _resident_clothing_candidates(self, state: dict) -> list[str]:
        nodes = state.get("nodes", {})
        return [node_id for node_id in sorted(nodes) if canonical_semantic_type(nodes.get(node_id) or {}) == "clothes"]

    def _resident_worn_clothes(self, state: dict, actor_id: str) -> str:
        for node_id, parent_id in state.get("parent_of", {}).items():
            if parent_id != actor_id:
                continue
            node = state.get("nodes", {}).get(node_id) or {}
            if canonical_semantic_type(node) != "clothes":
                continue
            if self._current_relation(state, node_id) == "worn_by":
                return node_id
        return ""

    def _resident_next_clothing(self, state: dict) -> str:
        parent_of = state.get("parent_of", {})
        nodes = state.get("nodes", {})
        actor_id = "human_resident"

        worn_id = self._resident_worn_clothes(state, actor_id)
        if worn_id:
            worn_states = (nodes.get(worn_id) or {}).get("states") or {}
            if not bool(worn_states.get("is_dirty", False)):
                return worn_id

        for node_id in self._resident_clothing_candidates(state):
            if parent_of.get(node_id) == "wardrobe_bedroom":
                node_states = (nodes.get(node_id) or {}).get("states") or {}
                if not bool(node_states.get("is_dirty", False)):
                    return node_id
        for node_id in self._resident_clothing_candidates(state):
            room_id = state.get("room_of", {}).get(node_id, "")
            node_states = (nodes.get(node_id) or {}).get("states") or {}
            if room_id == "bedroom" and not bool(node_states.get("is_dirty", False)):
                return node_id
        for node_id in self._resident_clothing_candidates(state):
            node_states = (nodes.get(node_id) or {}).get("states") or {}
            if not bool(node_states.get("is_dirty", False)):
                return node_id
        for node_id in self._resident_clothing_candidates(state):
            if parent_of.get(node_id) == "wardrobe_bedroom":
                return node_id
        return worn_id or "clothes_bedroom_1"

    def _current_relation(self, state: dict, node_id: str) -> str:
        return str(((state.get("nodes", {}).get(node_id) or {}).get("runtime") or {}).get("relation") or "")

    def _resident_worn_shoes(self, state: dict, actor_id: str) -> str:
        for node_id, parent_id in state.get("parent_of", {}).items():
            if parent_id != actor_id:
                continue
            node = state.get("nodes", {}).get(node_id) or {}
            if canonical_semantic_type(node) == "shoes" and self._current_relation(state, node_id) == "worn_by":
                return node_id
        return "shoes_entrance_1"

    def _resident_departure_shoe_location(self, state: dict) -> tuple[str, str, str]:
        shoe_id = "shoes_entrance_1"
        parent_id = state.get("parent_of", {}).get(shoe_id, "shoe_rack_entrance")
        room_id = state.get("room_of", {}).get(shoe_id, "entrance")
        return shoe_id, parent_id, room_id

    def _apply_state_disturbance(self, state: dict, actor_id: str, state_name: str, step: int) -> None:
        if state_name not in {"washing_up_morning", "washing_up_night"}:
            return
        toothbrush_target = ["sink_bathroom", "faucet_bathroom", "counter_bathroom_proxy", "toilet_bathroom"][(step + 1) % 4]
        cup_target = ["sink_bathroom", "faucet_bathroom", "counter_bathroom_proxy"][(step + 3) % 3]
        if toothbrush_target == "counter_bathroom_proxy":
            toothbrush_target = "sink_bathroom"
            state["nodes"]["toothbrush_bathroom"].setdefault("states", {})["misplaced_near"] = "counter_bathroom"
        else:
            state["nodes"]["toothbrush_bathroom"].setdefault("states", {}).pop("misplaced_near", None)
        if cup_target == "counter_bathroom_proxy":
            cup_target = "sink_bathroom"
            state["nodes"]["cup_bathroom"].setdefault("states", {})["misplaced_near"] = "counter_bathroom"
        else:
            state["nodes"]["cup_bathroom"].setdefault("states", {}).pop("misplaced_near", None)
        move_item(state, "toothbrush_bathroom", toothbrush_target, "on")
        move_item(state, "cup_bathroom", cup_target, "on")
        set_node_state(state, "sink_bathroom", is_full=True)
        cleanliness = float(state["nodes"]["toilet_bathroom"].setdefault("states", {}).get("cleanliness", 0.92))
        cleanliness = max(0.0, round(cleanliness - 0.18, 2))
        set_node_state(state, "toilet_bathroom", cleanliness=cleanliness, is_dirty=cleanliness <= 0.45)
        log_event(state, step, "disturb_bathroom", f"{actor_id} disturbed bathroom items during {state_name}")

    def _apply_eating_effect(self, state: dict, step: int) -> None:
        move_item(state, "bowls_dishwasher_kitchen", "coffee_table_living_room", "on")
        set_node_state(state, "bowls_dishwasher_kitchen", is_clean=False)
        trash_states = state["nodes"].get("trash_bin_living_room", {}).setdefault("states", {})
        fill_level = min(1.0, round(float(trash_states.get("fill_level", 0.0)) + 0.22, 2))
        trash_states["fill_level"] = fill_level
        trash_states["is_full"] = fill_level >= 0.75
        log_event(state, step, "eat", "dirty bowls were left in living room")

    def _apply_night_laundry_effect(self, state: dict, step: int) -> None:
        clothing_id = self._resident_next_clothing(state)
        if not clothing_id:
            return
        move_item(state, clothing_id, "bathroom", "in")
        set_node_state(state, clothing_id, is_clean=False, folded=False)
        log_event(state, step, "laundry", "night washing generated dirty clothes in bathroom")

    def _take_out_trash(self, state: dict, step: int) -> None:
        trash = state.get("nodes", {}).get("trash_bin_living_room") or {}
        trash_states = trash.setdefault("states", {})
        trash_children = [
            node_id
            for node_id, parent_id in state.get("parent_of", {}).items()
            if parent_id == "trash_bin_living_room"
        ]
        if float(trash_states.get("fill_level", 0.0)) <= 0.0 and not bool(trash_states.get("is_full", False)) and not trash_children:
            return
        trash_states["fill_level"] = 0.0
        trash_states["is_full"] = False
        for node_id in trash_children:
            move_item(state, node_id, "trash_bin_living_room", "in")
            if node_id in self.STAPLE_FOOD_IDS:
                node = state.get("nodes", {}).get(node_id) or {}
                states = node.setdefault("states", {})
                move_item(state, node_id, "fridge_kitchen", "in")
                states["freshness"] = 1.0
                states["is_rotten"] = False
                states["temperature"] = "cold"
        log_event(state, step, "trash_emptied", "human_resident emptied trash before leaving home")

    def _restock_home_supplies(self, state: dict, step: int) -> None:
        restocked: list[str] = []
        for node_id in self.STAPLE_FOOD_IDS:
            node = state.get("nodes", {}).get(node_id) or {}
            states = node.setdefault("states", {})
            parent_id = state.get("parent_of", {}).get(node_id, "")
            needs_restock = not parent_id
            if not needs_restock:
                continue
            move_item(state, node_id, "fridge_kitchen", "in")
            states["freshness"] = 1.0
            states["is_rotten"] = False
            states["temperature"] = "cold"
            restocked.append(node_id)
        if restocked:
            log_event(state, step, "grocery_restock", f"human_resident restocked {', '.join(restocked)}")

    def _action_queue_for_phase(self, state: dict, actor_id: str, activity: str, step: int) -> list[dict]:
        clothing_id = self._resident_next_clothing(state)
        shoe_id = self._resident_worn_shoes(state, actor_id)
        departure_shoe_id, departure_shoe_parent, departure_shoe_room = self._resident_departure_shoe_location(state)
        shoe_target = "shoe_rack_entrance" if (step // 144) % 2 == 0 else "living_room"
        shoe_relation = "on" if shoe_target == "shoe_rack_entrance" else "in"
        queue_map = {
            "waking_up": [{"kind": "move_to", "parent": "bedroom", "room": "bedroom"}],
            "getting_dressed": [
                {"kind": "move_to", "parent": "wardrobe_bedroom", "room": "bedroom"},
                {"kind": "open", "target": "wardrobe_bedroom"},
                {"kind": "wear", "object": clothing_id},
                {"kind": "close", "target": "wardrobe_bedroom"},
            ],
            "washing_up_morning": [
                {"kind": "open", "target": "door_bedroom"},
                {"kind": "move_to", "parent": "sink_bathroom", "room": "bathroom"},
                {"kind": "press", "target": "faucet_bathroom", "is_on": True},
                {"kind": "wash_up"},
                {"kind": "press", "target": "faucet_bathroom", "is_on": False},
                {"kind": "move_to", "parent": "bathroom", "room": "bathroom"},
            ],
            "breakfast": [
                {"kind": "move_to", "parent": "dishwasher_kitchen", "room": "kitchen"},
                {"kind": "pick", "object": "bowls_dishwasher_kitchen"},
                {"kind": "move_to", "parent": "coffee_table_living_room", "room": "living_room"},
                {"kind": "place", "object": "bowls_dishwasher_kitchen", "target": "coffee_table_living_room", "relation": "on"},
                {"kind": "eat_meal"},
            ],
            "leaving_home": [
                {"kind": "move_to", "parent": departure_shoe_parent, "room": departure_shoe_room},
                {"kind": "wear", "object": departure_shoe_id},
                {"kind": "move_to", "parent": "entrance", "room": "entrance"},
                {"kind": "take_out_trash"},
                {"kind": "open", "target": "door_entrance"},
                {"kind": "leave_scene"},
            ],
            "returning_home": [
                {"kind": "open", "target": "door_entrance"},
                {"kind": "move_to", "parent": "shoe_rack_entrance", "room": "entrance"},
                {"kind": "remove_worn", "object": shoe_id, "target": shoe_target, "relation": shoe_relation},
                {"kind": "restock_supplies"},
                {"kind": "move_to", "parent": "sofa_living_room", "room": "living_room"},
            ],
            "waiting_for_dinner": [{"kind": "move_to", "parent": "sofa_living_room", "room": "living_room"}],
            "eating": [
                {"kind": "move_to", "parent": "coffee_table_living_room", "room": "living_room"},
                {"kind": "eat_meal"},
            ],
            "washing_up_night": [
                {"kind": "move_to", "parent": "sink_bathroom", "room": "bathroom"},
                {"kind": "press", "target": "faucet_bathroom", "is_on": True},
                {"kind": "wash_up"},
                {"kind": "press", "target": "faucet_bathroom", "is_on": False},
                {"kind": "night_laundry"},
            ],
            "sleeping": [{"kind": "move_to", "parent": "bed_bedroom", "room": "bedroom"}],
        }
        return copy.deepcopy(queue_map.get(activity, []))

    def _execute_action(self, state: dict, actor_id: str, action: dict, activity: str, step: int) -> bool:
        kind = action.get("kind")
        current_room = state.get("room_of", {}).get(actor_id, "")

        if kind == "move_to":
            target_parent = str(action.get("parent") or "")
            target_room = str(action.get("room") or "")
            if state.get("parent_of", {}).get(actor_id) == target_parent and current_room == target_room:
                return True
            if current_room != target_room:
                _move_one_hop_towards_target(state, actor_id, current_room, target_room, activity, step)
                return state.get("parent_of", {}).get(actor_id) == target_parent and state.get("room_of", {}).get(actor_id) == target_room
            move_actor(state, actor_id, target_parent, target_room, activity)
            log_event(state, step, "npc_move", f"{actor_id} moved within {target_room} to {target_parent}")
            return True

        if kind == "open":
            target = str(action.get("target") or "")
            node = state.get("nodes", {}).get(target) or {}
            if bool((node.get("states") or {}).get("is_open", False)):
                return True
            set_node_state(state, target, is_open=True, isOpen=True)
            log_event(state, step, "npc_open", f"{actor_id} opened {target}")
            return True

        if kind == "close":
            target = str(action.get("target") or "")
            node = state.get("nodes", {}).get(target) or {}
            if not bool((node.get("states") or {}).get("is_open", False)):
                return True
            set_node_state(state, target, is_open=False, isOpen=False)
            log_event(state, step, "npc_close", f"{actor_id} closed {target}")
            return True

        if kind == "wear":
            object_id = str(action.get("object") or "")
            if state.get("parent_of", {}).get(object_id) == actor_id and self._current_relation(state, object_id) == "worn_by":
                return True
            object_room = state.get("room_of", {}).get(object_id, "")
            if object_room and object_room != current_room:
                _move_one_hop_towards_target(state, actor_id, current_room, object_room, activity, step)
                return state.get("room_of", {}).get(actor_id) == object_room
            move_item(state, object_id, actor_id, "worn_by")
            if canonical_semantic_type(state["nodes"].get(object_id) or {}) == "shoes":
                set_node_state(state, object_id, scattered=False)
            log_event(state, step, "npc_wear", f"{actor_id} wore {object_id}")
            return True

        if kind == "pick":
            object_id = str(action.get("object") or "")
            if state.get("parent_of", {}).get(object_id) == actor_id and self._current_relation(state, object_id) == "held_by":
                return True
            move_item(state, object_id, actor_id, "held_by")
            log_event(state, step, "npc_pick", f"{actor_id} picked {object_id}")
            return True

        if kind == "place":
            object_id = str(action.get("object") or "")
            target = str(action.get("target") or "")
            relation = str(action.get("relation") or "on")
            if state.get("parent_of", {}).get(object_id) == target and self._current_relation(state, object_id) == relation:
                return True
            move_item(state, object_id, target, relation)
            log_event(state, step, "npc_place", f"{actor_id} placed {object_id} {relation} {target}")
            return True

        if kind == "press":
            target = str(action.get("target") or "")
            desired = action.get("is_on")
            node = state.get("nodes", {}).get(target) or {}
            states = node.get("states") or {}
            if desired is not None and bool(states.get("is_on", False)) == bool(desired):
                return True
            updates = {"is_pressed": True}
            if desired is not None:
                updates["is_on"] = bool(desired)
            set_node_state(state, target, **updates)
            log_event(state, step, "npc_press", f"{actor_id} pressed {target}")
            return True

        if kind == "wash_up":
            self._apply_state_disturbance(state, actor_id, activity, step)
            log_event(state, step, "npc_wash_up", f"{actor_id} used sink during {activity}")
            return True

        if kind == "eat_meal":
            self._apply_eating_effect(state, step)
            log_event(state, step, "npc_eat", f"{actor_id} ate during {activity}")
            return True

        if kind == "night_laundry":
            self._apply_night_laundry_effect(state, step)
            return True

        if kind == "take_out_trash":
            self._take_out_trash(state, step)
            return True

        if kind == "restock_supplies":
            self._restock_home_supplies(state, step)
            return True

        if kind == "leave_scene":
            move_actor(state, actor_id, "outside_home", "outside_home", activity)
            log_event(state, step, "npc_move", f"{actor_id} left the scene")
            return True

        if kind == "remove_worn":
            object_id = str(action.get("object") or "")
            target = str(action.get("target") or "")
            relation = str(action.get("relation") or "in")
            move_item(state, object_id, target, relation)
            if canonical_semantic_type(state["nodes"].get(object_id) or {}) == "shoes":
                set_node_state(state, object_id, scattered=(target != "shoe_rack_entrance"))
            log_event(state, step, "npc_remove", f"{actor_id} removed {object_id} to {target}")
            return True

        return True

    def step(self, state: dict, actor_id: str, step: int, minute: int) -> None:
        day = int((state.get("world_state") or {}).get("day") or 1)
        _, _, scheduled_activity = self.scheduled_activity(minute, day)
        actor = state.get("nodes", {}).get(actor_id) or {}
        actor_states = actor.setdefault("states", {})
        world = state.get("world_state") or {}
        actor_states["weekday_name"] = str(world.get("weekday_name") or "")
        actor_states["season_name"] = str(world.get("season_name") or "")
        actor_states["is_workday"] = bool(world.get("is_workday", False))
        queue = actor_states.get("_phase_queue") or []
        backlog = actor_states.get("_phase_backlog") or []
        current_phase = str(actor_states.get("_phase_name") or "")
        last_scheduled = str(actor_states.get("_scheduled_phase") or "")

        if scheduled_activity != last_scheduled:
            actor_states["_scheduled_phase"] = scheduled_activity
            if scheduled_activity != current_phase and scheduled_activity not in backlog:
                backlog.append(scheduled_activity)

        if not queue:
            while backlog:
                next_phase = backlog.pop(0)
                next_queue = self._action_queue_for_phase(state, actor_id, next_phase, step)
                actor_states["_phase_name"] = next_phase
                actor_states["_phase_queue"] = next_queue
                queue = next_queue
                current_phase = next_phase
                if queue:
                    break
            else:
                actor_states["_phase_name"] = scheduled_activity
                actor_states["_phase_queue"] = []

        actor_states["_phase_backlog"] = backlog
        active_phase = str(actor_states.get("_phase_name") or scheduled_activity)
        actor_states["current_activity"] = active_phase

        if queue:
            current_action = queue[0]
            consumed = self._execute_action(state, actor_id, current_action, active_phase, step)
            if consumed:
                queue.pop(0)
            actor_states["_phase_queue"] = queue
        elif current_phase != scheduled_activity:
            actor_states["current_activity"] = scheduled_activity


POLICY_REGISTRY: dict[str, NpcPolicy] = {
    "resident": ResidentPolicy("resident"),
    "patient": HospitalPatientPolicy("patient"),
    "worker": ScheduledNpcPolicy("worker"),
    "receptionist": HospitalStaffPolicy("receptionist"),
    "doctor": HospitalStaffPolicy("doctor", uniform_id="doctor_coat_staff_room"),
    "nurse": HospitalStaffPolicy("nurse", uniform_id="nurse_uniform_staff_room"),
    "pharmacist": HospitalStaffPolicy("pharmacist"),
}


def get_npc_policy(role: str) -> NpcPolicy:
    return POLICY_REGISTRY.get(role, POLICY_REGISTRY[DEFAULT_ROLE])


def apply_npc_routines(state: dict, step: int) -> None:
    ensure_default_npcs(state)
    current_minute = minute_of_day(state.get("world_state") or {}, step)
    for spec in _npc_specs_for_state(state):
        actor_id = spec["id"]
        actor = state.get("nodes", {}).get(actor_id) or {}
        role = _schedule_role(actor)
        policy = get_npc_policy(role)
        policy.step(state, actor_id, step, current_minute)


__all__ = [
    "NpcPolicy",
    "apply_npc_routines",
    "ensure_default_npcs",
    "get_npc_policy",
    "minute_of_day",
]
