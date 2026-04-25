from __future__ import annotations

from dataclasses import dataclass
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
