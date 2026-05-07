from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


HOME_NPC_LIBRARY: List[Dict[str, str]] = [
    {
        "id": "human_resident",
        "name": "white_collar_worker",
        "name_cn": "普通白领",
        "role": "resident",
        "parent": "bed_bedroom",
        "room": "bedroom",
        "activity": "sleeping",
        "persona": "weekday_office_worker",
    }
]


HOSPITAL_NPC_LIBRARY: List[Dict[str, str]] = [
    {
        "id": "receptionist_1",
        "name": "receptionist",
        "name_cn": "前台",
        "role": "receptionist",
        "parent": "outside_home",
        "room": "outside_home",
        "activity": "off_shift",
        "persona": "hospital_receptionist",
    },
    {
        "id": "doctor_1",
        "name": "doctor",
        "name_cn": "医生",
        "role": "doctor",
        "parent": "outside_home",
        "room": "outside_home",
        "activity": "off_shift",
        "persona": "hospital_doctor",
    },
    {
        "id": "nurse_1",
        "name": "nurse",
        "name_cn": "护士",
        "role": "nurse",
        "parent": "outside_home",
        "room": "outside_home",
        "activity": "off_shift",
        "persona": "hospital_nurse",
    },
    {
        "id": "patient_1",
        "name": "patient",
        "name_cn": "病人",
        "role": "patient",
        "parent": "outside_home",
        "room": "outside_home",
        "activity": "away",
        "persona": "hospital_patient",
    },
    {
        "id": "pharmacist_1",
        "name": "pharmacist",
        "name_cn": "药师",
        "role": "pharmacist",
        "parent": "outside_home",
        "room": "outside_home",
        "activity": "off_shift",
        "persona": "hospital_pharmacist",
    },
]


@dataclass(frozen=True)
class ScheduleEntry:
    start_min: int
    end_min: int
    target_parent: str
    target_room: str
    activity: str


@dataclass(frozen=True)
class EventPrecondition:
    kind: str
    target: str = ""
    semantic_type: str = ""
    semantic_types: tuple[str, ...] = ()
    state: str = ""
    value: object = True
    states: dict[str, object] = field(default_factory=dict)
    match_states: dict[str, object] = field(default_factory=dict)
    relation: str = ""
    relation_not: str = ""
    parent: str = ""
    room: str = ""
    description: str = ""


@dataclass(frozen=True)
class EventEffect:
    kind: str
    target: str = ""
    semantic_type: str = ""
    state: str = ""
    value: object = True
    states: dict[str, object] = field(default_factory=dict)
    match_states: dict[str, object] = field(default_factory=dict)
    parent: str = ""
    parent_options: tuple[str, ...] = ()
    parent_index_offset: int = 0
    parent_index_mode: str = "step"
    relation: str = ""
    relation_options: tuple[str, ...] = ()
    relation_not: str = ""
    room: str = ""
    states_by_parent: dict[str, dict[str, object]] = field(default_factory=dict)
    transient_states_by_index: dict[int, dict[str, object | None]] = field(default_factory=dict)
    amount: float = 0.0
    min_value: float | None = None
    max_value: float | None = None
    threshold_state: str = ""
    threshold_op: str = ""
    threshold_value: float = 0.0
    description: str = ""


@dataclass(frozen=True)
class EventSpec:
    event_id: str
    duration: int = 1
    preconditions: tuple[EventPrecondition, ...] = field(default_factory=tuple)
    effects_on_success: tuple[EventEffect, ...] = field(default_factory=tuple)
    effects_on_failure: tuple[EventEffect, ...] = field(default_factory=tuple)


NPC_EVENT_LIBRARY: dict[str, EventSpec] = {
    "sleeping": EventSpec(
        event_id="sleeping",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="bed_bedroom", relation="at"),
        ),
    ),
    "waking_up": EventSpec(
        event_id="waking_up",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="bed_bedroom", relation="at"),
        ),
    ),
    "getting_dressed": EventSpec(
        event_id="getting_dressed",
        duration=1,
        preconditions=(
            EventPrecondition(
                "has_node",
                semantic_type="clothes",
                room="bedroom",
                states={"is_dirty": False, "is_wet": False, "folded": True},
                relation_not="worn_by",
                description="No clean clothes available.",
            ),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="wardrobe_bedroom", relation="near"),
            EventEffect(
                "move_matching_node",
                semantic_type="clothes",
                room="bedroom",
                match_states={"is_dirty": False, "is_wet": False, "folded": True},
                relation_not="worn_by",
                parent="human",
                relation="worn_by",
            ),
        ),
    ),
    "washing_up_morning": EventSpec(
        event_id="washing_up_morning",
        duration=1,
        preconditions=(
            EventPrecondition(
                "has_semantics",
                semantic_types=("toothbrush", "toothpaste", "cup"),
                room="bathroom",
                description="Bathroom supplies are unavailable.",
            ),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="sink_bathroom", relation="near"),
            EventEffect(
                "move_matching_node",
                target="toothbrush_bathroom",
                parent_options=("sink_bathroom", "faucet_bathroom", "sink_bathroom", "toilet_bathroom"),
                parent_index_offset=1,
                relation="on",
                transient_states_by_index={2: {"misplaced_near": "counter_bathroom"}},
            ),
            EventEffect(
                "move_matching_node",
                target="cup_bathroom",
                parent_options=("sink_bathroom", "faucet_bathroom", "sink_bathroom"),
                parent_index_offset=3,
                relation="on",
                transient_states_by_index={2: {"misplaced_near": "counter_bathroom"}},
            ),
            EventEffect("set_state", target="sink_bathroom", states={"is_full": True}),
            EventEffect("increment_state", target="toilet_bathroom", state="cleanliness", amount=-0.18, min_value=0.0, threshold_state="is_dirty", threshold_op="<=", threshold_value=0.45),
            EventEffect("set_state", target="human", state="is_dirty", value=False),
        ),
    ),
    "washing_up_night": EventSpec(
        event_id="washing_up_night",
        duration=1,
        preconditions=(
            EventPrecondition(
                "has_semantics",
                semantic_types=("toothbrush", "toothpaste", "cup"),
                room="bathroom",
                description="Bathroom supplies are unavailable.",
            ),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="sink_bathroom", relation="near"),
            EventEffect(
                "move_matching_node",
                target="toothbrush_bathroom",
                parent_options=("sink_bathroom", "faucet_bathroom", "sink_bathroom", "toilet_bathroom"),
                parent_index_offset=1,
                relation="on",
                transient_states_by_index={2: {"misplaced_near": "counter_bathroom"}},
            ),
            EventEffect(
                "move_matching_node",
                target="cup_bathroom",
                parent_options=("sink_bathroom", "faucet_bathroom", "sink_bathroom"),
                parent_index_offset=3,
                relation="on",
                transient_states_by_index={2: {"misplaced_near": "counter_bathroom"}},
            ),
            EventEffect("set_state", target="sink_bathroom", states={"is_full": True}),
            EventEffect("increment_state", target="toilet_bathroom", state="cleanliness", amount=-0.18, min_value=0.0, threshold_state="is_dirty", threshold_op="<=", threshold_value=0.45),
            EventEffect("move_worn_node", semantic_type="clothes", parent="bathroom", relation="in", states={"is_dirty": True, "folded": False}),
        ),
    ),
    "breakfast": EventSpec(
        event_id="breakfast",
        duration=1,
        preconditions=(
            EventPrecondition("has_node", semantic_type="food", description="No food available."),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="coffee_table_living_room", relation="near"),
            EventEffect("move_matching_node", target="bowls_dishwasher_kitchen", parent="coffee_table_living_room", relation="on", states={"is_clean": False, "is_dirty": True}),
            EventEffect("set_state", target="plate_living_room", states={"is_dirty": True}),
            EventEffect("set_state", target="cup_living_room", states={"is_dirty": True}),
            EventEffect("increment_state", target="trash_bin_living_room", state="fill_level", amount=0.22, max_value=1.0, threshold_state="is_full", threshold_op=">=", threshold_value=0.75),
        ),
    ),
    "leaving_home": EventSpec(
        event_id="leaving_home",
        duration=1,
        preconditions=(
            EventPrecondition(
                "has_node",
                semantic_type="shoes",
                room="entrance",
                states={"is_dirty": False, "is_wet": False},
                relation_not="worn_by",
                description="No shoes available to leave home.",
            ),
        ),
        effects_on_success=(
            EventEffect("move_matching_node", semantic_type="shoes", room="entrance", match_states={"is_dirty": False, "is_wet": False}, relation_not="worn_by", parent="human", relation="worn_by", states={"scattered": False}),
            EventEffect("set_state", target="door_entrance", states={"is_open": True}),
            EventEffect("move_actor", parent="outside_home", relation="at"),
        ),
    ),
    "eating": EventSpec(
        event_id="eating",
        duration=1,
        preconditions=(
            EventPrecondition("has_node", semantic_type="food", description="No food available."),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="coffee_table_living_room", relation="near"),
            EventEffect("move_matching_node", target="bowls_dishwasher_kitchen", parent="coffee_table_living_room", relation="on", states={"is_clean": False, "is_dirty": True}),
            EventEffect("set_state", target="plate_living_room", states={"is_dirty": True}),
            EventEffect("set_state", target="cup_living_room", states={"is_dirty": True}),
            EventEffect("increment_state", target="trash_bin_living_room", state="fill_level", amount=0.22, max_value=1.0, threshold_state="is_full", threshold_op=">=", threshold_value=0.75),
        ),
    ),
    "returning_home": EventSpec(
        event_id="returning_home",
        duration=1,
        effects_on_success=(
            EventEffect("set_state", target="door_entrance", states={"is_open": True}),
            EventEffect("move_actor", parent="shoe_rack_entrance", relation="near"),
            EventEffect(
                "move_worn_node",
                semantic_type="shoes",
                parent_options=("shoe_rack_entrance", "living_room"),
                parent_index_mode="day",
                relation_options=("on", "in"),
                states={"is_dirty": True},
                states_by_parent={
                    "shoe_rack_entrance": {"scattered": False},
                    "living_room": {"scattered": True},
                },
            ),
            EventEffect("move_actor", parent="sofa_living_room", relation="near"),
        ),
    ),
    "waiting_for_dinner": EventSpec(
        event_id="waiting_for_dinner",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="sofa_living_room", relation="near"),
        ),
    ),
    "resting_home": EventSpec(
        event_id="resting_home",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="sofa_living_room", relation="near"),
        ),
    ),
    "away_at_work": EventSpec(
        event_id="away_at_work",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="outside_home", relation="at"),
        ),
    ),
}


ROLE_SCHEDULES: dict[str, list[ScheduleEntry]] = {
    "resident_workday": [
        ScheduleEntry(0, 6 * 60, "bed_bedroom", "bedroom", "sleeping"),
        ScheduleEntry(6 * 60, 6 * 60 + 30, "bed_bedroom", "bedroom", "waking_up"),
        ScheduleEntry(6 * 60 + 30, 7 * 60, "wardrobe_bedroom", "bedroom", "getting_dressed"),
        ScheduleEntry(7 * 60, 7 * 60 + 30, "sink_bathroom", "bathroom", "washing_up_morning"),
        ScheduleEntry(7 * 60 + 30, 8 * 60, "coffee_table_living_room", "living_room", "breakfast"),
        ScheduleEntry(8 * 60, 8 * 60 + 30, "entrance", "entrance", "leaving_home"),
        ScheduleEntry(8 * 60 + 30, 18 * 60, "outside_home", "outside_home", "away_at_work"),
        ScheduleEntry(18 * 60, 18 * 60 + 30, "living_room", "living_room", "returning_home"),
        ScheduleEntry(18 * 60 + 30, 20 * 60, "sofa_living_room", "living_room", "waiting_for_dinner"),
        ScheduleEntry(20 * 60, 21 * 60, "coffee_table_living_room", "living_room", "eating"),
        ScheduleEntry(21 * 60, 22 * 60, "sink_bathroom", "bathroom", "washing_up_night"),
        ScheduleEntry(22 * 60, 24 * 60, "bed_bedroom", "bedroom", "sleeping"),
    ],
    "resident_weekend": [
        ScheduleEntry(0, 7 * 60 + 30, "bed_bedroom", "bedroom", "sleeping"),
        ScheduleEntry(7 * 60 + 30, 8 * 60, "bed_bedroom", "bedroom", "waking_up"),
        ScheduleEntry(8 * 60, 8 * 60 + 30, "wardrobe_bedroom", "bedroom", "getting_dressed"),
        ScheduleEntry(8 * 60 + 30, 9 * 60, "sink_bathroom", "bathroom", "washing_up_morning"),
        ScheduleEntry(9 * 60, 10 * 60, "coffee_table_living_room", "living_room", "breakfast"),
        ScheduleEntry(10 * 60, 12 * 60 + 30, "sofa_living_room", "living_room", "resting_home"),
        ScheduleEntry(12 * 60 + 30, 13 * 60 + 30, "coffee_table_living_room", "living_room", "eating"),
        ScheduleEntry(13 * 60 + 30, 19 * 60, "sofa_living_room", "living_room", "resting_home"),
        ScheduleEntry(19 * 60, 20 * 60, "coffee_table_living_room", "living_room", "eating"),
        ScheduleEntry(20 * 60, 21 * 60, "sink_bathroom", "bathroom", "washing_up_night"),
        ScheduleEntry(21 * 60, 24 * 60, "bed_bedroom", "bedroom", "sleeping"),
    ],
    "patient": [
        ScheduleEntry(0, 8 * 60, "outside_home", "outside_home", "away"),
        ScheduleEntry(8 * 60, 8 * 60 + 20, "entrance", "entrance", "arriving"),
        ScheduleEntry(8 * 60 + 20, 16 * 60, "registration", "registration", "care_pathway"),
        ScheduleEntry(16 * 60, 17 * 60, "outside_home", "outside_home", "departing"),
        ScheduleEntry(17 * 60, 24 * 60, "outside_home", "outside_home", "departed"),
    ],
    "worker": [
        ScheduleEntry(0, 5 * 60 + 30, "bed_bedroom", "bedroom", "sleeping"),
        ScheduleEntry(5 * 60 + 30, 6 * 60, "wardrobe_bedroom", "bedroom", "getting_ready"),
        ScheduleEntry(6 * 60, 6 * 60 + 30, "sink_bathroom", "bathroom", "washing_up_morning"),
        ScheduleEntry(6 * 60 + 30, 7 * 60, "entrance", "entrance", "departing"),
        ScheduleEntry(7 * 60, 18 * 60, "outside_home", "outside_home", "working_shift"),
        ScheduleEntry(18 * 60, 18 * 60 + 30, "living_room", "living_room", "returning_home"),
        ScheduleEntry(18 * 60 + 30, 22 * 60, "sofa_living_room", "living_room", "resting"),
        ScheduleEntry(22 * 60, 24 * 60, "bed_bedroom", "bedroom", "sleeping"),
    ],
    "receptionist": [
        ScheduleEntry(0, 7 * 60 + 20, "outside_home", "outside_home", "off_shift"),
        ScheduleEntry(7 * 60 + 20, 8 * 60, "registration", "registration", "walking_to_registration"),
        ScheduleEntry(8 * 60, 12 * 60, "registration", "registration", "registration_desk"),
        ScheduleEntry(12 * 60, 13 * 60, "staff_room", "staff_room", "break"),
        ScheduleEntry(13 * 60, 17 * 60 + 30, "registration", "registration", "registration_desk"),
        ScheduleEntry(17 * 60 + 30, 18 * 60, "outside_home", "outside_home", "departing"),
        ScheduleEntry(18 * 60, 24 * 60, "outside_home", "outside_home", "off_shift"),
    ],
    "doctor": [
        ScheduleEntry(0, 6 * 60 + 30, "outside_home", "outside_home", "off_shift"),
        ScheduleEntry(6 * 60 + 30, 8 * 60, "staff_room", "staff_room", "walking_to_staff_room"),
        ScheduleEntry(8 * 60, 8 * 60 + 20, "staff_room", "staff_room", "preparing"),
        ScheduleEntry(8 * 60 + 20, 8 * 60 + 50, "outpatient_clinic_1", "outpatient_clinic_1", "walking_to_clinic"),
        ScheduleEntry(8 * 60 + 50, 12 * 60 + 30, "outpatient_clinic_1", "outpatient_clinic_1", "clinic_station"),
        ScheduleEntry(12 * 60 + 30, 13 * 60, "staff_room", "staff_room", "break"),
        ScheduleEntry(13 * 60, 13 * 60 + 30, "outpatient_clinic_1", "outpatient_clinic_1", "walking_to_clinic"),
        ScheduleEntry(13 * 60 + 30, 16 * 60 + 40, "outpatient_clinic_1", "outpatient_clinic_1", "clinic_station"),
        ScheduleEntry(16 * 60 + 40, 18 * 60, "outside_home", "outside_home", "departing"),
        ScheduleEntry(18 * 60, 24 * 60, "outside_home", "outside_home", "off_shift"),
    ],
    "nurse": [
        ScheduleEntry(0, 6 * 60 + 30, "outside_home", "outside_home", "off_shift"),
        ScheduleEntry(6 * 60 + 30, 8 * 60, "staff_room", "staff_room", "walking_to_staff_room"),
        ScheduleEntry(8 * 60, 8 * 60 + 20, "staff_room", "staff_room", "preparing"),
        ScheduleEntry(8 * 60 + 20, 9 * 60, "triage", "triage", "walking_to_triage"),
        ScheduleEntry(9 * 60, 12 * 60 + 30, "triage", "triage", "triage_station"),
        ScheduleEntry(12 * 60 + 30, 13 * 60, "staff_room", "staff_room", "break"),
        ScheduleEntry(13 * 60, 13 * 60 + 30, "treatment_room", "treatment_room", "walking_to_treatment"),
        ScheduleEntry(13 * 60 + 30, 16 * 60 + 30, "treatment_room", "treatment_room", "treatment_station"),
        ScheduleEntry(16 * 60 + 30, 18 * 60, "outside_home", "outside_home", "departing"),
        ScheduleEntry(18 * 60, 24 * 60, "outside_home", "outside_home", "off_shift"),
    ],
    "pharmacist": [
        ScheduleEntry(0, 7 * 60 + 30, "outside_home", "outside_home", "off_shift"),
        ScheduleEntry(7 * 60 + 30, 8 * 60, "pharmacy", "pharmacy", "walking_to_pharmacy"),
        ScheduleEntry(8 * 60, 17 * 60 + 30, "pharmacy", "pharmacy", "pharmacy_station"),
        ScheduleEntry(17 * 60 + 30, 18 * 60, "outside_home", "outside_home", "departing"),
        ScheduleEntry(18 * 60, 24 * 60, "outside_home", "outside_home", "off_shift"),
    ],
}

DEFAULT_ROLE = "resident"


def get_default_npcs(scene_type: str) -> List[Dict[str, str]]:
    if scene_type == "hospital":
        return HOSPITAL_NPC_LIBRARY
    return HOME_NPC_LIBRARY


def _is_workday(day: int) -> bool:
    return ((max(1, int(day)) - 1) % 7) < 5


def schedule_for_role(role: str, day: int = 1) -> list[ScheduleEntry]:
    if role == "resident":
        resolved = "resident_workday" if _is_workday(day) else "resident_weekend"
        return ROLE_SCHEDULES[resolved]
    return ROLE_SCHEDULES.get(role, ROLE_SCHEDULES["resident_workday"])


def planned_activity(role: str, minute: int, day: int = 1) -> tuple[str, str, str]:
    normalized = minute % (24 * 60)
    for entry in schedule_for_role(role, day):
        if entry.start_min <= normalized < entry.end_min:
            return (entry.target_parent, entry.target_room, entry.activity)
    fallback = schedule_for_role(role, day)[-1]
    return (fallback.target_parent, fallback.target_room, fallback.activity)


def get_event_spec(event_id: str) -> EventSpec | None:
    return NPC_EVENT_LIBRARY.get(str(event_id or ""))
