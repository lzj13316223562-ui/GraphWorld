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
        "id": "doctor_1",
        "name": "doctor",
        "name_cn": "医生",
        "role": "doctor",
        "parent": "outside_home",
        "room": "outside_home",
        "activity": "off_shift",
        "persona": "hospital_doctor",
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
    timing: str = "every_step"
    target: str = ""
    semantic_type: str = ""
    state: str = ""
    value: object = True
    states: dict[str, object] = field(default_factory=dict)
    match_states: dict[str, object] = field(default_factory=dict)
    match_parent: str = ""
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
                timing="period_start",
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
            EventEffect("move_worn_node", timing="period_start", semantic_type="clothes", parent="bathroom", relation="in", states={"is_dirty": True, "folded": False}),
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
            EventEffect("move_matching_node", timing="period_start", target="bowls_dishwasher_kitchen", parent="coffee_table_living_room", relation="on", states={"is_clean": False, "is_dirty": True}),
            EventEffect("move_matching_node", timing="period_start", target="food_living_room", parent="coffee_table_living_room", relation="on", states={"is_rotten": True}),
            EventEffect("move_matching_node", timing="period_start", target="plate_living_room", parent="coffee_table_living_room", relation="on", states={"is_dirty": True}),
            EventEffect("move_matching_node", timing="period_start", target="cup_living_room", parent="coffee_table_living_room", relation="on", states={"is_dirty": True}),
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
            EventEffect("move_matching_node", timing="period_start", semantic_type="shoes", room="entrance", match_states={"is_dirty": False, "is_wet": False}, relation_not="worn_by", parent="human", relation="worn_by", states={"scattered": False}),
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
            EventEffect("move_matching_node", timing="period_start", target="bowls_dishwasher_kitchen", parent="coffee_table_living_room", relation="on", states={"is_clean": False, "is_dirty": True}),
            EventEffect("move_matching_node", timing="period_start", target="food_living_room", parent="coffee_table_living_room", relation="on", states={"is_rotten": True}),
            EventEffect("move_matching_node", timing="period_start", target="plate_living_room", parent="coffee_table_living_room", relation="on", states={"is_dirty": True}),
            EventEffect("move_matching_node", timing="period_start", target="cup_living_room", parent="coffee_table_living_room", relation="on", states={"is_dirty": True}),
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
                timing="period_start",
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
    "hospital_away": EventSpec(
        event_id="hospital_away",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="outside_home", relation="at"),
        ),
    ),
    "hospital_off_shift": EventSpec(
        event_id="hospital_off_shift",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="outside_home", relation="at"),
        ),
    ),
    "patient_register": EventSpec(
        event_id="patient_register",
        duration=1,
        preconditions=(
            EventPrecondition("has_node", target="medical_form_registration", parent="counter_registration", description="No registration form available."),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="counter_registration", relation="near"),
            EventEffect(
                "set_state",
                target="human",
                states={
                    "registered": True,
                    "waiting": False,
                    "called": False,
                    "diagnosed": False,
                    "has_prescription": False,
                    "medicine_delivered": False,
                    "has_medicine": False,
                    "infusion_done": False,
                    "checked_out": False,
                },
            ),
            EventEffect("set_state", target="computer_registration", states={"is_on": True}),
            EventEffect("move_matching_node", target="medical_form_registration", parent="counter_registration", relation="on", states={"is_filled": True}),
        ),
    ),
    "patient_wait": EventSpec(
        event_id="patient_wait",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="seats_waiting_area", relation="near"),
            EventEffect("set_state", target="human", states={"waiting": True}),
            EventEffect("set_state", target="queue_screen_waiting_area", states={"is_on": True}),
            EventEffect("increment_state", timing="period_start", target="seats_waiting_area", state="cleanliness", amount=-0.12, min_value=0.0, threshold_state="is_dirty", threshold_op="<=", threshold_value=0.75),
        ),
    ),
    "patient_consult": EventSpec(
        event_id="patient_consult",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="exam_bed_clinic_1", relation="near"),
            EventEffect("set_state", target="human", states={"waiting": False, "diagnosed": True}),
            EventEffect("set_state", target="exam_bed_clinic_1", states={"is_dirty": True, "needs_cleaning": True}),
        ),
    ),
    "patient_take_medicine": EventSpec(
        event_id="patient_take_medicine",
        duration=1,
        preconditions=(
            EventPrecondition("has_node", semantic_type="prescription_sheet", parent="patient_1", description="Patient has no prescription."),
            EventPrecondition("has_node", target="medicine_box_pharmacy", parent="pharmacy", description="No medicine box available at pharmacy."),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="shelf_pharmacy", relation="near"),
            EventEffect("move_matching_node", target="medicine_box_pharmacy", parent="patient_1", relation="carried_by", states={"assigned_patient": "patient_1"}),
            EventEffect("set_state", target="human", states={"has_medicine": True, "waiting": False}),
        ),
    ),
    "patient_infusion": EventSpec(
        event_id="patient_infusion",
        duration=1,
        preconditions=(
            EventPrecondition("has_node", target="refrigerated_medicine_pharmacy", parent="patient_1", description="Infusion medicine was not delivered to patient."),
            EventPrecondition("has_node", target="patient_1", states={"medicine_delivered": True}, description="Infusion medicine is not assigned for this visit."),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="treatment_bed_treatment_room", relation="near"),
            EventEffect("set_state", target="human", states={"infusion_done": True, "waiting": False}),
            EventEffect("set_state", target="treatment_bed_treatment_room", states={"is_dirty": True, "needs_cleaning": True}),
            EventEffect("move_matching_node", target="used_syringe_treatment_room", parent="treatment_bed_treatment_room", relation="on", states={"is_medical_waste": True}),
        ),
    ),
    "patient_leave": EventSpec(
        event_id="patient_leave",
        duration=1,
        effects_on_success=(
            EventEffect("move_matching_node", target="prescription_sheet_clinic_1", match_parent="patient_1", parent="prescription_return_lobby", relation="on", states={"assigned_patient": ""}),
            EventEffect("move_matching_node", target="medicine_box_pharmacy", match_parent="patient_1", parent="supply_zone_lobby", relation="on", states={"assigned_patient": ""}),
            EventEffect("move_matching_node", target="refrigerated_medicine_pharmacy", match_parent="patient_1", parent="supply_zone_lobby", relation="on", states={"assigned_patient": "", "temperature": "cold"}),
            EventEffect("move_actor", parent="outside_home", relation="at"),
            EventEffect("set_state", target="human", states={"checked_out": True, "waiting": False}),
        ),
    ),
    "doctor_prepare": EventSpec(
        event_id="doctor_prepare",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="locker_staff_room", relation="near"),
            EventEffect("move_matching_node", target="doctor_coat_staff_room", parent="doctor_1", relation="worn_by"),
        ),
    ),
    "doctor_call_patient": EventSpec(
        event_id="doctor_call_patient",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="desk_clinic_1", relation="near"),
            EventEffect("set_state", target="queue_screen_waiting_area", states={"is_on": True, "called_patient": "patient_1"}),
            EventEffect("set_state", target="patient_1", states={"called": True}),
        ),
    ),
    "doctor_examine_patient": EventSpec(
        event_id="doctor_examine_patient",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="exam_bed_clinic_1", relation="near"),
            EventEffect("set_state", target="computer_clinic_1", states={"is_on": True}),
            EventEffect("set_state", target="patient_1", states={"diagnosed": True}),
        ),
    ),
    "doctor_prescribe": EventSpec(
        event_id="doctor_prescribe",
        duration=1,
        preconditions=(
            EventPrecondition("has_node", target="prescription_sheet_clinic_1", parent="outpatient_clinic_1", description="No blank prescription sheet available."),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="desk_clinic_1", relation="near"),
            EventEffect("move_matching_node", target="prescription_sheet_clinic_1", parent="patient_1", relation="has", states={"assigned_patient": "patient_1"}),
            EventEffect("set_state", target="patient_1", states={"has_prescription": True}),
        ),
    ),
    "nurse_prepare": EventSpec(
        event_id="nurse_prepare",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="locker_staff_room", relation="near"),
            EventEffect("move_matching_node", target="nurse_uniform_staff_room", parent="nurse_1", relation="worn_by"),
        ),
    ),
    "nurse_round": EventSpec(
        event_id="nurse_round",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="treatment_bed_treatment_room", relation="near"),
            EventEffect("set_state", target="medical_cart_treatment_room", states={"is_checked": True}),
        ),
    ),
    "nurse_deliver_medicine": EventSpec(
        event_id="nurse_deliver_medicine",
        duration=1,
        preconditions=(
            EventPrecondition("has_node", target="refrigerated_medicine_pharmacy", parent="medicine_fridge_pharmacy", description="No refrigerated medicine available."),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="medical_cart_treatment_room", relation="near"),
            EventEffect("move_matching_node", target="refrigerated_medicine_pharmacy", parent="patient_1", relation="assigned_to", states={"assigned_patient": "patient_1"}),
            EventEffect("set_state", target="patient_1", states={"medicine_delivered": True}),
        ),
    ),
    "nurse_change_bed_sheet": EventSpec(
        event_id="nurse_change_bed_sheet",
        duration=1,
        preconditions=(
            EventPrecondition("has_node", target="clean_sheet_storage", parent="supply_cabinet_treatment_room", description="No clean bed sheet available."),
        ),
        effects_on_success=(
            EventEffect("move_actor", parent="treatment_bed_treatment_room", relation="near"),
            EventEffect("move_matching_node", target="clean_sheet_storage", parent="treatment_bed_treatment_room", relation="on", states={"is_clean": True, "is_dirty": False, "folded": False}),
            EventEffect("move_matching_node", target="dirty_sheet_treatment_room", parent="dirty_linen_bin_treatment_room", relation="in", states={"is_dirty": True}),
            EventEffect("set_state", target="treatment_bed_treatment_room", states={"is_dirty": False, "needs_cleaning": False}),
        ),
    ),
    "nurse_clean_bed": EventSpec(
        event_id="nurse_clean_bed",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="treatment_bed_treatment_room", relation="near"),
            EventEffect("set_state", target="treatment_bed_treatment_room", states={"is_dirty": False, "needs_cleaning": False}),
        ),
    ),
    "nurse_restock_supplies": EventSpec(
        event_id="nurse_restock_supplies",
        duration=1,
        effects_on_success=(
            EventEffect("move_actor", parent="medical_cart_treatment_room", relation="near"),
            EventEffect("set_state", target="supply_cabinet_treatment_room", states={"is_low": False}),
            EventEffect("set_state", target="medical_cart_treatment_room", states={"is_full": True, "fill_level": 1.0}),
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
        ScheduleEntry(0, 8 * 60, "outside_home", "outside_home", "hospital_away"),
        ScheduleEntry(8 * 60, 8 * 60 + 10, "counter_registration", "registration", "patient_register"),
        ScheduleEntry(8 * 60 + 10, 8 * 60 + 50, "seats_waiting_area", "waiting_area", "patient_wait"),
        ScheduleEntry(8 * 60 + 50, 9 * 60 + 20, "exam_bed_clinic_1", "outpatient_clinic_1", "patient_consult"),
        ScheduleEntry(9 * 60 + 20, 9 * 60 + 40, "seats_waiting_area", "waiting_area", "patient_wait"),
        ScheduleEntry(9 * 60 + 40, 9 * 60 + 50, "shelf_pharmacy", "pharmacy", "patient_take_medicine"),
        ScheduleEntry(9 * 60 + 50, 10 * 60, "seats_waiting_area", "waiting_area", "patient_wait"),
        ScheduleEntry(10 * 60, 11 * 60, "treatment_bed_treatment_room", "treatment_room", "patient_infusion"),
        ScheduleEntry(11 * 60, 11 * 60 + 20, "outside_home", "outside_home", "patient_leave"),
        ScheduleEntry(11 * 60 + 20, 24 * 60, "outside_home", "outside_home", "hospital_away"),
    ],
    "doctor": [
        ScheduleEntry(0, 7 * 60 + 50, "outside_home", "outside_home", "hospital_off_shift"),
        ScheduleEntry(7 * 60 + 50, 8 * 60 + 20, "locker_staff_room", "staff_room", "doctor_prepare"),
        ScheduleEntry(8 * 60 + 20, 8 * 60 + 50, "desk_clinic_1", "outpatient_clinic_1", "doctor_call_patient"),
        ScheduleEntry(8 * 60 + 50, 9 * 60 + 20, "exam_bed_clinic_1", "outpatient_clinic_1", "doctor_examine_patient"),
        ScheduleEntry(9 * 60 + 20, 9 * 60 + 30, "desk_clinic_1", "outpatient_clinic_1", "doctor_prescribe"),
        ScheduleEntry(9 * 60 + 30, 17 * 60, "desk_clinic_1", "outpatient_clinic_1", "doctor_call_patient"),
        ScheduleEntry(17 * 60, 24 * 60, "outside_home", "outside_home", "hospital_off_shift"),
    ],
    "nurse": [
        ScheduleEntry(0, 7 * 60 + 40, "outside_home", "outside_home", "hospital_off_shift"),
        ScheduleEntry(7 * 60 + 40, 8 * 60 + 10, "locker_staff_room", "staff_room", "nurse_prepare"),
        ScheduleEntry(8 * 60 + 10, 9 * 60 + 30, "treatment_bed_treatment_room", "treatment_room", "nurse_round"),
        ScheduleEntry(9 * 60 + 30, 9 * 60 + 40, "medical_cart_treatment_room", "treatment_room", "nurse_deliver_medicine"),
        ScheduleEntry(9 * 60 + 40, 10 * 60, "treatment_bed_treatment_room", "treatment_room", "nurse_round"),
        ScheduleEntry(10 * 60, 10 * 60 + 10, "treatment_bed_treatment_room", "treatment_room", "nurse_change_bed_sheet"),
        ScheduleEntry(10 * 60 + 10, 11 * 60, "treatment_bed_treatment_room", "treatment_room", "nurse_clean_bed"),
        ScheduleEntry(11 * 60, 12 * 60, "medical_cart_treatment_room", "treatment_room", "nurse_restock_supplies"),
        ScheduleEntry(12 * 60, 17 * 60, "treatment_bed_treatment_room", "treatment_room", "nurse_round"),
        ScheduleEntry(17 * 60, 24 * 60, "outside_home", "outside_home", "hospital_off_shift"),
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
