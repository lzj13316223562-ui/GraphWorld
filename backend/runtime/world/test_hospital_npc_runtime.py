from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.runtime.engine.state import build_runtime_state
from backend.runtime.schema.home_schema import normalize_home_scene
from backend.runtime.world.npc_runtime import HospitalPatientPolicy, HospitalStaffPolicy, ensure_default_npcs


SCENE_PATH = Path(__file__).resolve().parents[2] / "data" / "sg_output" / "simple_graph" / "simple_hospital_1f.json"


def _state() -> dict:
    scene = normalize_home_scene(json.loads(SCENE_PATH.read_text(encoding="utf-8")))
    state = build_runtime_state(scene)
    ensure_default_npcs(state)
    return state


class HospitalNpcFlowTests(unittest.TestCase):
    def test_default_hospital_npcs_include_pharmacist(self) -> None:
        state = _state()
        self.assertIn("pharmacist_1", state["nodes"])

    def test_patient_progresses_when_registration_event_happens(self) -> None:
        state = _state()
        state["room_of"]["patient_1"] = "registration"
        state["parent_of"]["patient_1"] = "registration"
        state["nodes"]["patient_1"]["parent"] = "registration"
        state["nodes"]["patient_1"]["states"]["current_activity"] = "waiting_registration"
        state["room_of"]["receptionist_1"] = "registration"
        state["parent_of"]["receptionist_1"] = "registration"
        state["nodes"]["receptionist_1"]["parent"] = "registration"

        policy = HospitalStaffPolicy("receptionist")
        policy._apply_service_event(state, "receptionist_1", "registration_desk", "registration", 10)

        patient_states = state["nodes"]["patient_1"]["states"]
        self.assertTrue(patient_states["registration_done"])
        self.assertEqual(patient_states["current_activity"], "registration_complete")

    def test_patient_progresses_when_triage_consultation_and_dispensing_happen(self) -> None:
        state = _state()
        patient_states = state["nodes"]["patient_1"]["states"]
        patient_states["registration_done"] = True

        state["room_of"]["patient_1"] = "triage"
        state["parent_of"]["patient_1"] = "triage"
        state["nodes"]["patient_1"]["parent"] = "triage"
        patient_states["current_activity"] = "waiting_triage"
        state["room_of"]["nurse_1"] = "triage"
        state["parent_of"]["nurse_1"] = "triage"
        state["nodes"]["nurse_1"]["parent"] = "triage"
        HospitalStaffPolicy("nurse")._apply_service_event(state, "nurse_1", "triage_station", "triage", 20)
        self.assertTrue(patient_states["triage_done"])

        state["room_of"]["patient_1"] = "outpatient_clinic_1"
        state["parent_of"]["patient_1"] = "outpatient_clinic_1"
        state["nodes"]["patient_1"]["parent"] = "outpatient_clinic_1"
        patient_states["current_activity"] = "waiting_consultation"
        state["room_of"]["doctor_1"] = "outpatient_clinic_1"
        state["parent_of"]["doctor_1"] = "outpatient_clinic_1"
        state["nodes"]["doctor_1"]["parent"] = "outpatient_clinic_1"
        HospitalStaffPolicy("doctor")._apply_service_event(state, "doctor_1", "clinic_station", "outpatient_clinic_1", 30)
        self.assertTrue(patient_states["consultation_done"])

        state["room_of"]["patient_1"] = "pharmacy"
        state["parent_of"]["patient_1"] = "pharmacy"
        state["nodes"]["patient_1"]["parent"] = "pharmacy"
        patient_states["current_activity"] = "waiting_pharmacy"
        state["room_of"]["pharmacist_1"] = "pharmacy"
        state["parent_of"]["pharmacist_1"] = "pharmacy"
        state["nodes"]["pharmacist_1"]["parent"] = "pharmacy"
        HospitalStaffPolicy("pharmacist")._apply_service_event(state, "pharmacist_1", "pharmacy_station", "pharmacy", 40)
        self.assertTrue(patient_states["dispensing_done"])

    def test_patient_policy_uses_service_completion_flags(self) -> None:
        state = _state()
        patient = state["nodes"]["patient_1"]["states"]
        patient["registration_done"] = True
        patient["triage_done"] = True
        patient["consultation_done"] = False
        patient["treatment_done"] = False
        patient["payment_done"] = False
        patient["dispensing_done"] = False
        state["room_of"]["patient_1"] = "waiting_area"
        state["parent_of"]["patient_1"] = "waiting_area"
        state["nodes"]["patient_1"]["parent"] = "waiting_area"

        policy = HospitalPatientPolicy("patient")
        policy.step(state, "patient_1", 50, 12 * 60)

        self.assertEqual(state["nodes"]["patient_1"]["states"]["current_activity"], "waiting_consultation")


if __name__ == "__main__":
    unittest.main()
