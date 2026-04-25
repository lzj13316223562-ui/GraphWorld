from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.runtime.agent.robot_executor import execute_robot_action
from backend.runtime.agent.robot_observation import ensure_scene_robot_stub
from backend.runtime.schema.home_schema import normalize_home_scene


SCENE_PATH = Path(__file__).resolve().parents[2] / "data" / "sg_output" / "simple_graph" / "simple_home_1f.json"


def _scene() -> dict:
    scene = json.loads(SCENE_PATH.read_text(encoding="utf-8"))
    scene = normalize_home_scene(scene)
    ensure_scene_robot_stub(scene, "robot_01")
    return scene


class RobotExecutorTests(unittest.TestCase):
    def _run_ok(self, scene: dict, action: dict, runtime_state: dict | None = None) -> dict:
        result = execute_robot_action(scene, action, runtime_state=runtime_state)
        self.assertTrue(result["ok"], msg=f"action failed: {action}, errors={result.get('failed_preconds')}")
        return result

    def test_executor_can_operate_on_raw_scene_without_preseeded_agent_stub(self) -> None:
        raw_scene = json.loads(SCENE_PATH.read_text(encoding="utf-8"))
        result = execute_robot_action(raw_scene, {"agent": "robot_01", "action": "scan", "target": "button_entrance"})

        self.assertTrue(result["ok"])

    def test_move_to_adjacent_room_succeeds_and_updates_map(self) -> None:
        result = self._run_ok(_scene(), {"agent": "robot_01", "action": "move", "target": "door_entrance"})
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "open", "target": "door_entrance"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "living_room"},
            runtime_state=result["runtime_state"],
        )
        self.assertEqual(result["scene"]["agent"]["current_room"], "living_room")
        self.assertEqual(result["runtime_state"]["parent_of"]["robot_01"], "living_room")
        self.assertEqual(result["runtime_state"]["room_of"]["robot_01"], "living_room")

    def test_move_to_non_adjacent_room_fails(self) -> None:
        result = execute_robot_action(_scene(), {"agent": "robot_01", "action": "move", "target": "bathroom"})

        self.assertFalse(result["ok"])
        self.assertIn("room not reachable from current room: bathroom", result["failed_preconds"])

    def test_press_requires_press_affordance(self) -> None:
        result = execute_robot_action(_scene(), {"agent": "robot_01", "action": "press", "target": "shoe_rack_entrance"})

        self.assertFalse(result["ok"])
        self.assertIn("target does not support press: shoe_rack_entrance", result["failed_preconds"])

    def test_brush_requires_brush_affordance(self) -> None:
        result = execute_robot_action(_scene(), {"agent": "robot_01", "action": "brush", "target": "button_entrance"})

        self.assertFalse(result["ok"])
        self.assertIn("target does not support brush: button_entrance", result["failed_preconds"])

    def test_brush_requires_cleaning_tool_in_hand(self) -> None:
        result = execute_robot_action(_scene(), {"agent": "robot_01", "action": "brush", "target": "toilet_bathroom"})

        self.assertFalse(result["ok"])
        self.assertIn("brush requires holding a cleaning tool for target: toilet_bathroom", result["failed_preconds"])

    def test_brush_toilet_with_toilet_brush_succeeds(self) -> None:
        scene = _scene()
        move_result = self._run_ok(scene, {"agent": "robot_01", "action": "move", "target": "door_entrance"})
        move_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "open", "target": "door_entrance"},
            runtime_state=move_result["runtime_state"],
        )
        move_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "move", "target": "living_room"},
            runtime_state=move_result["runtime_state"],
        )
        move_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "move", "target": "door_bedroom"},
            runtime_state=move_result["runtime_state"],
        )
        move_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "open", "target": "door_bedroom"},
            runtime_state=move_result["runtime_state"],
        )
        move_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "move", "target": "bedroom"},
            runtime_state=move_result["runtime_state"],
        )
        move_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "move", "target": "door_bathroom"},
            runtime_state=move_result["runtime_state"],
        )
        move_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "open", "target": "door_bathroom"},
            runtime_state=move_result["runtime_state"],
        )
        move_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "move", "target": "bathroom"},
            runtime_state=move_result["runtime_state"],
        )
        pick_result = self._run_ok(
            move_result["scene"],
            {"agent": "robot_01", "action": "pick", "object": "toilet_brush_bathroom"},
            runtime_state=move_result["runtime_state"],
        )
        brush_result = self._run_ok(
            pick_result["scene"],
            {"agent": "robot_01", "action": "move", "target": "toilet_bathroom"},
            runtime_state=pick_result["runtime_state"],
        )
        brush_result = self._run_ok(
            brush_result["scene"],
            {"agent": "robot_01", "action": "brush", "target": "toilet_bathroom"},
            runtime_state=brush_result["runtime_state"],
        )

    def test_open_requires_open_affordance(self) -> None:
        moved = self._run_ok(_scene(), {"agent": "robot_01", "action": "move", "target": "bench_entrance"})
        result = execute_robot_action(
            moved["scene"],
            {"agent": "robot_01", "action": "open", "target": "bench_entrance"},
            runtime_state=moved["runtime_state"],
        )

        self.assertFalse(result["ok"])
        self.assertIn("target does not support open: bench_entrance", result["failed_preconds"])

    def test_pick_requires_pick_affordance(self) -> None:
        result = execute_robot_action(_scene(), {"agent": "robot_01", "action": "pick", "object": "button_entrance"})

        self.assertFalse(result["ok"])
        self.assertIn("target does not support pick: button_entrance", result["failed_preconds"])

    def test_pick_and_place_update_inventory_and_parent(self) -> None:
        scene = _scene()
        pick_result = self._run_ok(scene, {"agent": "robot_01", "action": "move", "target": "shoe_rack_entrance"})
        pick_result = self._run_ok(
            pick_result["scene"],
            {"agent": "robot_01", "action": "pick", "object": "shoes_entrance_1"},
            runtime_state=pick_result["runtime_state"],
        )
        self.assertEqual(pick_result["scene"]["agent"]["inventory"], ["shoes_entrance_1"])
        self.assertEqual(pick_result["runtime_state"]["parent_of"]["shoes_entrance_1"], "robot_01")

        place_result = self._run_ok(
            pick_result["scene"],
            {"agent": "robot_01", "action": "move", "target": "bench_entrance"},
            runtime_state=pick_result["runtime_state"],
        )
        place_result = self._run_ok(
            place_result["scene"],
            {"agent": "robot_01", "action": "place", "object": "shoes_entrance_1", "target": "bench_entrance"},
            runtime_state=place_result["runtime_state"],
        )

        self.assertEqual(place_result["scene"]["agent"]["inventory"], [])
        self.assertEqual(place_result["runtime_state"]["parent_of"]["shoes_entrance_1"], "bench_entrance")

    def test_place_on_shoe_rack_is_legal(self) -> None:
        scene = _scene()
        pick_result = self._run_ok(scene, {"agent": "robot_01", "action": "move", "target": "shoe_rack_entrance"})
        pick_result = self._run_ok(
            pick_result["scene"],
            {"agent": "robot_01", "action": "pick", "object": "shoes_entrance_1"},
            runtime_state=pick_result["runtime_state"],
        )

        place_result = self._run_ok(
            pick_result["scene"],
            {"agent": "robot_01", "action": "place", "object": "shoes_entrance_1", "target": "shoe_rack_entrance"},
            runtime_state=pick_result["runtime_state"],
        )

        self.assertEqual(place_result["runtime_state"]["parent_of"]["shoes_entrance_1"], "shoe_rack_entrance")

    def test_can_dispose_food_into_trash_bin_without_opening_it(self) -> None:
        scene = _scene()
        result = self._run_ok(scene, {"agent": "robot_01", "action": "move", "target": "door_entrance"})
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "open", "target": "door_entrance"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "living_room"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "door_living_room"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "open", "target": "door_living_room"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "kitchen"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "door_fridge_kitchen"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "open", "target": "door_fridge_kitchen"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "fridge_kitchen"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "pick", "object": "milk_fridge_kitchen"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "door_living_room"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "living_room"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "move", "target": "trash_bin_living_room"},
            runtime_state=result["runtime_state"],
        )
        result = self._run_ok(
            result["scene"],
            {"agent": "robot_01", "action": "place", "object": "milk_fridge_kitchen", "target": "trash_bin_living_room"},
            runtime_state=result["runtime_state"],
        )

        self.assertEqual(result["runtime_state"]["parent_of"]["milk_fridge_kitchen"], "trash_bin_living_room")

    def test_place_requires_place_affordance(self) -> None:
        scene = _scene()
        pick_result = execute_robot_action(scene, {"agent": "robot_01", "action": "pick", "object": "shoes_entrance_1"})
        result = execute_robot_action(
            pick_result["scene"],
            {"agent": "robot_01", "action": "place", "object": "shoes_entrance_1", "target": "button_entrance"},
            runtime_state=pick_result["runtime_state"],
        )

        self.assertFalse(result["ok"])
        self.assertIn("target does not support place: button_entrance", result["failed_preconds"])

    def test_invalid_action_returns_feedback(self) -> None:
        result = execute_robot_action(_scene(), {"agent": "robot_01", "action": "dance", "target": "entrance"})

        self.assertFalse(result["ok"])
        self.assertIn("unsupported action: dance", result["failed_preconds"])


if __name__ == "__main__":
    unittest.main()
