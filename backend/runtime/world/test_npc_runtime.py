from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.runtime.engine.state import build_runtime_state
from backend.runtime.schema.home_schema import normalize_home_scene
from backend.runtime.world.npc_runtime import ResidentPolicy, ensure_default_npcs


SCENE_PATH = Path(__file__).resolve().parents[2] / "data" / "sg_output" / "simple_graph" / "simple_home_1f.json"


def _state() -> dict:
    scene = normalize_home_scene(json.loads(SCENE_PATH.read_text(encoding="utf-8")))
    state = build_runtime_state(scene)
    ensure_default_npcs(state)
    return state


class ResidentPolicyRecoveryTests(unittest.TestCase):
    def test_take_out_trash_empties_bin(self) -> None:
        state = _state()
        trash = state["nodes"]["trash_bin_living_room"].setdefault("states", {})
        trash["fill_level"] = 0.9
        trash["is_full"] = True

        policy = ResidentPolicy("resident")
        ok = policy._execute_action(state, "human_resident", {"kind": "take_out_trash"}, "leaving_home", 1)

        self.assertTrue(ok)
        self.assertEqual(state["nodes"]["trash_bin_living_room"]["states"]["fill_level"], 0.0)
        self.assertFalse(state["nodes"]["trash_bin_living_room"]["states"]["is_full"])

    def test_restock_supplies_refreshes_missing_and_rotten_food(self) -> None:
        state = _state()
        state["nodes"]["milk_fridge_kitchen"]["states"]["freshness"] = 0.0
        state["nodes"]["milk_fridge_kitchen"]["states"]["is_rotten"] = True
        state["parent_of"]["milk_fridge_kitchen"] = ""
        state["room_of"]["milk_fridge_kitchen"] = ""
        state["nodes"]["milk_fridge_kitchen"]["parent"] = ""

        policy = ResidentPolicy("resident")
        ok = policy._execute_action(state, "human_resident", {"kind": "restock_supplies"}, "returning_home", 1)

        self.assertTrue(ok)
        self.assertEqual(state["parent_of"]["milk_fridge_kitchen"], "fridge_kitchen")
        self.assertEqual(state["room_of"]["milk_fridge_kitchen"], "kitchen")
        self.assertEqual(state["nodes"]["milk_fridge_kitchen"]["states"]["freshness"], 1.0)
        self.assertFalse(state["nodes"]["milk_fridge_kitchen"]["states"]["is_rotten"])
        self.assertEqual(state["nodes"]["milk_fridge_kitchen"]["states"]["temperature"], "cold")

    def test_take_out_trash_refreshes_staple_food_from_trash(self) -> None:
        state = _state()
        state["nodes"]["milk_fridge_kitchen"]["states"]["freshness"] = 0.0
        state["nodes"]["milk_fridge_kitchen"]["states"]["is_rotten"] = True
        state["parent_of"]["milk_fridge_kitchen"] = "trash_bin_living_room"
        state["room_of"]["milk_fridge_kitchen"] = "living_room"
        state["nodes"]["milk_fridge_kitchen"]["parent"] = "trash_bin_living_room"
        state["nodes"]["trash_bin_living_room"]["states"]["fill_level"] = 0.3
        state["nodes"]["trash_bin_living_room"]["states"]["is_full"] = False

        policy = ResidentPolicy("resident")
        ok = policy._execute_action(state, "human_resident", {"kind": "take_out_trash"}, "leaving_home", 1)

        self.assertTrue(ok)
        self.assertEqual(state["parent_of"]["milk_fridge_kitchen"], "fridge_kitchen")
        self.assertEqual(state["room_of"]["milk_fridge_kitchen"], "kitchen")
        self.assertEqual(state["nodes"]["milk_fridge_kitchen"]["states"]["freshness"], 1.0)
        self.assertFalse(state["nodes"]["milk_fridge_kitchen"]["states"]["is_rotten"])


if __name__ == "__main__":
    unittest.main()
