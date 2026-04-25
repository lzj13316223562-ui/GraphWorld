from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.runtime.agent.robot_memory import (
    RobotMemory,
    consolidate_experience,
    reflect_on_feedback,
    summarize_memory,
    update_memory_from_observation,
)
from backend.runtime.agent.robot_observation import build_robot_observation
from backend.runtime.agent.robot_resoning import _legal_action_space, ground_high_level_plan, planner_only_decision
from backend.runtime.engine.state import build_runtime_state


class RobotPlannerReflectionTest(unittest.TestCase):
    def _home_kitchen_scene(self, *, fridge_open: bool) -> tuple[dict, dict]:
        scene = json.loads(Path("backend/data/sg_output/simple_graph/simple_home_1f.json").read_text(encoding="utf-8"))
        scene["agent"] = {"id": "robot_01", "current_room": "kitchen", "inventory": []}
        for node in scene["nodes"]:
            if node.get("id") == "fridge_kitchen":
                node.setdefault("states", {})["is_open"] = fridge_open
            if node.get("id") == "door_fridge_kitchen":
                node.setdefault("states", {})["is_open"] = fridge_open
            if node.get("id") in {"milk_fridge_kitchen", "juice_fridge_kitchen", "vegetables_fridge_kitchen"}:
                node.setdefault("states", {})["is_rotten"] = True
                node.setdefault("states", {})["freshness"] = 0.0
        state = build_runtime_state(scene)
        state["nodes"]["fridge_kitchen"].setdefault("states", {})["is_open"] = fridge_open
        state["nodes"]["door_fridge_kitchen"].setdefault("states", {})["is_open"] = fridge_open
        for node_id in ("milk_fridge_kitchen", "juice_fridge_kitchen", "vegetables_fridge_kitchen"):
            state["nodes"][node_id].setdefault("states", {})["is_rotten"] = True
            state["nodes"][node_id].setdefault("states", {})["freshness"] = 0.0
        return scene, state

    def test_hospital_scene_normalization_restores_interactive_actions(self) -> None:
        scene = json.loads(Path("backend/data/sg_output/simple_graph/simple_hospital_1f.json").read_text(encoding="utf-8"))
        observation = build_robot_observation(scene, agent_id="robot_01")
        visible_by_id = {node["id"]: node for node in observation["visible_nodes"]}
        self.assertIn("button_entrance", visible_by_id)
        self.assertIn("press", visible_by_id["button_entrance"]["interactive_actions"])
        self.assertIn("door_entrance", visible_by_id)
        self.assertIn("open", visible_by_id["door_entrance"]["interactive_actions"])
        self.assertIn("close", visible_by_id["door_entrance"]["interactive_actions"])

    def test_grounding_prefers_intervention_actions_for_relevant_issues(self) -> None:
        observation = {
            "robot": {"current_room": "room_living", "adjacent_rooms": ["room_kitchen"]},
            "compressed_observation": {
                "world": {"world_score": 0.62},
            },
            "visible_nodes": [],
        }
        action_space = [
            {
                "action_type": "move",
                "target_id": "room_kitchen",
                "target_semantic": "room",
                "issue_tags": [],
                "action_payload": {"agent": "robot_01", "action": "move", "target": "room_kitchen"},
            },
            {
                "action_type": "pick",
                "target_id": "apple_1",
                "target_semantic": "fruit",
                "issue_tags": ["rotten"],
                "action_payload": {"agent": "robot_01", "action": "pick", "target": "apple_1", "object": "apple_1"},
            },
            {
                "action_type": "close",
                "target_id": "door_1",
                "target_semantic": "door",
                "issue_tags": ["open"],
                "action_payload": {"agent": "robot_01", "action": "close", "target": "door_1"},
            },
        ]
        memory_summary = {"recent_actions": []}
        plan = {
            "focus": "intervene",
            "intent": "remove or fix score-relevant issues in the current room",
            "preferred_action_types": ["pick", "close"],
            "avoid_action_types": ["scan"],
            "target_ids": ["apple_1", "door_1"],
        }

        decision = ground_high_level_plan(plan, action_space, observation, memory_summary)

        self.assertEqual(decision["action"], "pick")
        self.assertEqual(decision["target"], "apple_1")
        candidates = decision["grounding"]["candidates"]
        self.assertGreaterEqual(candidates[0]["grounding_score"], candidates[-1]["grounding_score"])

    def test_planner_only_fallback_uses_legal_action_space(self) -> None:
        observation = {
            "compressed_observation": {
                "world": {"world_score": 0.58},
            },
            "visible_nodes": [{"id": "sink_1", "semantic_type": "sink", "states": {"is_dirty": True}}],
        }
        action_space = [
            {
                "action_type": "move",
                "target_id": "room_kitchen",
                "target_semantic": "room",
                "issue_tags": [],
                "action_payload": {"agent": "robot_01", "action": "move", "target": "room_kitchen"},
            },
            {
                "action_type": "brush",
                "target_id": "sink_1",
                "target_semantic": "sink",
                "issue_tags": ["dirty"],
                "action_payload": {"agent": "robot_01", "action": "brush", "target": "sink_1"},
            },
        ]
        packet = {
            "compressed_observation": observation.get("compressed_observation") or {},
            "local_issue_objects": [{"id": "sink_1", "issue_tags": ["dirty"]}],
            "previous_goal_review": {},
        }
        planner, decision = planner_only_decision(observation, {"recent_actions": []}, action_space, packet)

        self.assertEqual(planner["focus"], "intervene")
        self.assertEqual(decision["action"], "brush")
        self.assertEqual(decision["target"], "sink_1")

    def test_grounding_filters_risky_repetition(self) -> None:
        observation = {
            "compressed_observation": {"world": {"world_score": 0.55}},
            "visible_nodes": [],
        }
        action_space = [
            {
                "action_type": "close",
                "target_id": "door_kitchen",
                "target_semantic": "door",
                "issue_tags": ["open"],
                "action_payload": {"agent": "robot_01", "action": "close", "target": "door_kitchen"},
            },
            {
                "action_type": "brush",
                "target_id": "sink_1",
                "target_semantic": "sink",
                "issue_tags": ["dirty"],
                "action_payload": {"agent": "robot_01", "action": "brush", "target": "sink_1"},
            },
        ]
        memory_summary = {
            "recent_actions": [
                {"action": {"action": "close", "target": "door_kitchen"}, "outcome": "risky", "world_score_before": 0.6, "world_score_after": 0.58},
                {"action": {"action": "close", "target": "door_kitchen"}, "outcome": "risky", "world_score_before": 0.58, "world_score_after": 0.56},
            ]
        }
        plan = {
            "focus": "intervene",
            "intent": "reduce risks in the room",
            "preferred_action_types": ["close", "brush"],
            "avoid_action_types": [],
            "target_ids": ["door_kitchen", "sink_1"],
        }
        decision = ground_high_level_plan(plan, action_space, observation, memory_summary)
        self.assertEqual(decision["action"], "brush")
        self.assertEqual(decision["target"], "sink_1")

    def test_legal_action_space_includes_memory_issue_targets_not_in_planning_visible_nodes(self) -> None:
        scene, state = self._home_kitchen_scene(fridge_open=True)
        full_observation = build_robot_observation(scene, runtime_state=state, agent_id="robot_01")
        memory = RobotMemory()
        update_memory_from_observation(memory, full_observation)
        memory_summary = summarize_memory(memory)

        planning_observation = dict(full_observation)
        planning_observation["visible_nodes"] = [
            node for node in full_observation["visible_nodes"] if node["id"] in {"button_kitchen", "door_fridge_kitchen", "door_kitchen"}
        ]

        action_space = _legal_action_space(scene, state, planning_observation, memory_summary, memory, "robot_01")
        action_targets = {(item["action_type"], item.get("target_id")) for item in action_space}

        # With explicit local-interaction preconditions, planner should first expose setup moves.
        self.assertIn(("move", "door_fridge_kitchen"), action_targets)
        self.assertIn(("move", "door_kitchen"), action_targets)

    def test_setup_actions_prioritize_reachable_moves_before_open_close(self) -> None:
        scene, state = self._home_kitchen_scene(fridge_open=False)
        full_observation = build_robot_observation(scene, runtime_state=state, agent_id="robot_01")
        memory = RobotMemory()
        update_memory_from_observation(memory, full_observation)
        memory_summary = summarize_memory(memory)

        planning_observation = dict(full_observation)
        planning_observation["visible_nodes"] = [
            node
            for node in full_observation["visible_nodes"]
            if node["id"] in {"button_kitchen", "dishwasher_kitchen_door", "door_fridge_kitchen", "door_kitchen"}
        ]

        action_space = _legal_action_space(scene, state, planning_observation, memory_summary, memory, "robot_01")
        action_targets = {(item["action_type"], item.get("target_id")) for item in action_space}

        self.assertNotIn(("open", "door_fridge_kitchen"), action_targets)
        self.assertNotIn(("close", "door_fridge_kitchen"), action_targets)
        self.assertIn(("move", "button_kitchen"), action_targets)

    def test_reflection_produces_high_level_experience_summary(self) -> None:
        memory = RobotMemory(
            node={
                "plate_1": {"id": "plate_1", "node_type": "object", "semantic_type": "plate"},
            },
            working_memory={"recent_reflections": [], "patterns": [], "experience_summaries": [], "experience_library": {}},
        )
        action = {"action": "brush", "target": "plate_1", "agent": "robot_01"}

        immediate = reflect_on_feedback(
            memory,
            action=action,
            reasoning="clean the dirty plate",
            ok=True,
            failed_preconds=[],
            world_score_before=0.50,
            world_score_after=0.56,
            step=12,
            phase="after_action",
        )
        world = reflect_on_feedback(
            memory,
            action=action,
            reasoning="clean the dirty plate",
            ok=True,
            failed_preconds=[],
            world_score_before=0.56,
            world_score_after=0.58,
            step=12,
            phase="after_world_step",
        )
        summary = consolidate_experience(
            memory,
            action=action,
            ok=True,
            failed_preconds=[],
            immediate_reflection=immediate,
            world_reflection=world,
            step=12,
        )

        self.assertEqual(summary["outcome"], "helpful")
        self.assertIn("reliably useful intervention", summary["summary"])
        self.assertTrue(memory.working_memory["experience_summaries"])
        library_entries = list((memory.working_memory.get("experience_library") or {}).values())
        self.assertEqual(len(library_entries), 1)
        self.assertEqual(library_entries[0]["count"], 1)


if __name__ == "__main__":
    unittest.main()
