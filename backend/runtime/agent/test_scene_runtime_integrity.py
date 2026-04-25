from __future__ import annotations

import json
import unittest
from collections import defaultdict
from pathlib import Path

from backend.runtime.agent.robot_memory import RobotMemory, summarize_memory
from backend.runtime.schema.home_schema import normalize_home_scene


SCENE_DIR = Path(__file__).resolve().parents[2] / "data" / "sg_output" / "simple_graph"


def _raw_scene(scene_name: str) -> dict:
    return json.loads((SCENE_DIR / f"{scene_name}.json").read_text(encoding="utf-8"))


def _normalized_scene(scene_name: str) -> dict:
    return normalize_home_scene(_raw_scene(scene_name))


class SceneRuntimeIntegrityTests(unittest.TestCase):
    def test_home_and_hospital_nodes_with_existing_children_support_place(self) -> None:
        for scene_name in ("simple_home_1f", "simple_hospital_1f"):
            raw = _raw_scene(scene_name)
            normalized = _normalized_scene(scene_name)
            nodes_by_id = {str(node.get("id") or ""): node for node in normalized.get("nodes", [])}
            child_map: dict[str, list[str]] = defaultdict(list)
            for edge in raw.get("edges", []):
                if str(edge.get("relation") or "").lower() not in {"in", "on"}:
                    continue
                source_id = str(edge.get("source_id") or "")
                target_id = str(edge.get("target_id") or "")
                if source_id and target_id:
                    child_map[source_id].append(target_id)

            failures = []
            for source_id, children in child_map.items():
                node = nodes_by_id.get(source_id) or {}
                actions = set(node.get("interactive_actions") or [])
                if "place" not in actions:
                    failures.append((scene_name, source_id, node.get("semantic_type"), sorted(actions), children))
            self.assertFalse(failures, msg=f"nodes with in/on children must support place: {failures}")

    def test_known_problematic_scene_nodes_have_expected_affordances(self) -> None:
        home = {node["id"]: node for node in _normalized_scene("simple_home_1f").get("nodes", [])}
        hospital = {node["id"]: node for node in _normalized_scene("simple_hospital_1f").get("nodes", [])}

        self.assertIn("place", home["shoe_rack_entrance"]["interactive_actions"])
        self.assertIn("place", hospital["shelf_pharmacy"]["interactive_actions"])
        self.assertIn("place", hospital["medicine_fridge_pharmacy"]["interactive_actions"])
        self.assertNotIn("outpatient_clinic_2", hospital)

    def test_summarize_memory_prefers_robot_action_history_over_other_agents(self) -> None:
        memory = RobotMemory(
            stable_node={
                "human_resident": {
                    "id": "human_resident",
                    "node_type": "agent",
                    "semantic_type": "human",
                    "memory_recent_actions": [{"action": {"action": "sleep"}, "step": 3}],
                },
                "robot_01": {
                    "id": "robot_01",
                    "node_type": "agent",
                    "semantic_type": "robot",
                    "memory_recent_actions": [{"action": {"action": "pick", "target": "shoes_entrance_1"}, "step": 7}],
                },
            },
            working_memory={"recent_actions": []},
        )

        summary = summarize_memory(memory)

        self.assertEqual(len(summary["recent_actions"]), 1)
        self.assertEqual(summary["recent_actions"][0]["action"]["action"], "pick")
        self.assertEqual(summary["recent_actions"][0]["action"]["target"], "shoes_entrance_1")


if __name__ == "__main__":
    unittest.main()
