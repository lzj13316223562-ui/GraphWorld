from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import io
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tensorboard.compat.proto import event_pb2, summary_pb2, tensor_pb2, tensor_shape_pb2, types_pb2
from tensorboard.summary.writer.event_file_writer import EventFileWriter
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.assets.npc_library import get_default_npcs, get_event_spec, planned_activity
from backend.runtime.agent import candidate_actions, fallback_choose_action, held_object, llm_choose_action, perceive, reflect, remember
from backend.runtime.engine import Orchestrator
from backend.runtime.eval import build_matrix_snapshot, matrix_score
from backend.tools.agent import resolved_agent_config


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SCENE_DIR = DATA_DIR / "sg_output" / "simple_graph"
SCENE_PATH = SCENE_DIR / "simple_home_1f.json"
LEGACY_REPLAY_DIR = DATA_DIR / "replay_logs"
TENSORBOARD_DIR = DATA_DIR / "tensorboard"
EXPERIMENT_DIR = DATA_DIR / "experiments"

SCORE_KEYS = ("final_score", "state_score", "spatial_score", "human_event_score")
CLOTH_SEMANTICS = {"clothes", "towel", "blanket"}
HOSPITAL_RETURN_SKILLS = {
    "replenish_prescription_sheet",
    "replenish_medicine_box",
    "return_refrigerated_medicine",
    "clean_medical_waste",
    "collect_dirty_linen",
    "restock_clean_sheet",
    "return_wheelchair",
}
HOSPITAL_CLEAN_SKILLS = {"clean_waiting_area", "clean_exam_bed"}
HOSPITAL_SKILL_BY_SEMANTIC = {
    "prescription_sheet": "replenish_prescription_sheet",
    "medicine_box": "replenish_medicine_box",
    "refrigerated_medicine": "return_refrigerated_medicine",
    "medical_waste": "clean_medical_waste",
    "wheelchair": "return_wheelchair",
}
HOSPITAL_SKILL_PRIORITY = {
    "replenish_prescription_sheet": 0,
    "return_refrigerated_medicine": 1,
    "replenish_medicine_box": 2,
    "restock_clean_sheet": 3,
    "clean_medical_waste": 4,
    "collect_dirty_linen": 5,
    "return_wheelchair": 6,
    "clean_waiting_area": 7,
    "clean_exam_bed": 8,
}
ACTION_CODES = {
    "move": 1,
    "pick": 2,
    "place": 3,
    "open": 4,
    "close": 5,
    "press": 6,
    "brush": 7,
    "fold": 8,
    "dump": 9,
}


class TensorBoardWriter:
    def __init__(self, log_dir: Path | str) -> None:
        self._writer = EventFileWriter(str(log_dir))

    def add_scalar(self, tag: str, value: float, step: int) -> None:
        summary = summary_pb2.Summary(
            value=[summary_pb2.Summary.Value(tag=tag, simple_value=float(value))]
        )
        self._writer.add_event(event_pb2.Event(wall_time=time.time(), step=int(step), summary=summary))

    def add_text(self, tag: str, text: str, step: int = 0) -> None:
        metadata = summary_pb2.SummaryMetadata(
            plugin_data=summary_pb2.SummaryMetadata.PluginData(plugin_name="text")
        )
        tensor = tensor_pb2.TensorProto(
            dtype=types_pb2.DT_STRING,
            string_val=[text.encode("utf-8")],
            tensor_shape=tensor_shape_pb2.TensorShapeProto(dim=[tensor_shape_pb2.TensorShapeProto.Dim(size=1)]),
        )
        summary = summary_pb2.Summary(
            value=[summary_pb2.Summary.Value(tag=tag, metadata=metadata, tensor=tensor)]
        )
        self._writer.add_event(event_pb2.Event(wall_time=time.time(), step=int(step), summary=summary))

    def add_figure(self, tag: str, fig: plt.Figure, step: int = 0) -> None:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=140)
        image = summary_pb2.Summary.Image(
            encoded_image_string=buffer.getvalue(),
            height=int(fig.bbox.bounds[3]),
            width=int(fig.bbox.bounds[2]),
            colorspace=4,
        )
        summary = summary_pb2.Summary(value=[summary_pb2.Summary.Value(tag=tag, image=image)])
        self._writer.add_event(event_pb2.Event(wall_time=time.time(), step=int(step), summary=summary))

    def flush(self) -> None:
        self._writer.flush()

    def close(self) -> None:
        self._writer.close()


def _slug(value: str | None) -> str:
    text = str(value or "").strip().lower()
    cleaned: list[str] = []
    for ch in text:
        cleaned.append(ch if ch.isalnum() else "_")
    slug = "".join(cleaned).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "unknown"


def canonical_model_label(agent_model: str | None) -> str:
    model = str(agent_model or "").strip()
    if not model:
        return "unknown_model"
    if model == "npc_only_baseline":
        return "npc_only_baseline"
    return _slug(model.replace(":", "-").replace(".", "_"))


def canonical_run_group(
    scene_id: str,
    experiment_type: str,
    agent_model: str | None,
    steps: int,
    robots: int,
    humans: int,
) -> str:
    return "__".join(
        (
            f"exp_{_slug(experiment_type)}",
            f"steps_{int(steps)}",
            f"robots_{int(robots)}",
            f"humans_{int(humans)}",
            f"model_{canonical_model_label(agent_model)}",
        )
    )


def canonical_experiment_group(scene_id: str, steps: int, robots: int, humans: int, agent_model: str | None) -> str:
    return "__".join(
        (
            f"steps_{int(steps)}",
            f"robots_{int(robots)}",
            f"humans_{int(humans)}",
            f"model_{canonical_model_label(agent_model)}",
        )
    )


def utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]


def clean_old_outputs() -> None:
    for folder in (TENSORBOARD_DIR, EXPERIMENT_DIR):
        folder.mkdir(parents=True, exist_ok=True)
        for item in folder.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
    if LEGACY_REPLAY_DIR.exists():
        for item in LEGACY_REPLAY_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        with contextlib.suppress(OSError):
            LEGACY_REPLAY_DIR.rmdir()


def node(scene: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for item in scene.get("nodes") or []:
        if item.get("id") == node_id:
            return item
    return None


def add_child(scene: dict[str, Any], parent_id: str, child_id: str) -> None:
    parent = node(scene, parent_id)
    if not parent:
        return
    children = parent.setdefault("child", [])
    if child_id not in children:
        children.append(child_id)


def ensure_node(scene: dict[str, Any], item: dict[str, Any]) -> None:
    existing = node(scene, str(item["id"]))
    if existing:
        existing.update({key: value for key, value in item.items() if key not in {"child"}})
        if item.get("child") is not None:
            existing["child"] = item["child"]
    else:
        scene.setdefault("nodes", []).append(item)
    parent_id = str(item.get("parent") or "")
    if parent_id:
        add_child(scene, parent_id, str(item["id"]))


def ensure_edge(scene: dict[str, Any], source_id: str, target_id: str, relation: str) -> None:
    for edge in scene.setdefault("edges", []):
        if edge.get("source_id") == source_id and edge.get("target_id") == target_id and edge.get("relation") == relation:
            return
    scene["edges"].append(
        {
            "source_id": source_id,
            "target_id": target_id,
            "edge_type": "runtime_seed_edge",
            "relation": relation,
            "category": "runtime_seed",
            "properties": {},
        }
    )


def robot_ids(robot_count: int) -> tuple[str, ...]:
    return tuple(f"robot_{index:02d}" for index in range(1, max(0, int(robot_count)) + 1))


def human_ids(human_count: int) -> tuple[str, ...]:
    count = max(0, int(human_count))
    return tuple("human_resident" if index == 1 else f"human_resident_{index:02d}" for index in range(1, count + 1))


def scene_type(scene: dict[str, Any]) -> str:
    name = str(scene.get("scene_name") or "")
    if "hospital" in name:
        return "hospital"
    return "home"


def actor_specs_for_scene(scene: dict[str, Any], human_count: int) -> list[dict[str, str]]:
    if scene_type(scene) == "hospital":
        defaults = get_default_npcs("hospital")
        return defaults[: max(0, int(human_count))]
    return [
        {
            "id": human_id,
            "name": "resident",
            "name_cn": "resident",
            "role": "resident",
            "parent": "bed_bedroom",
            "room": "bedroom",
            "activity": "sleeping",
            "persona": "weekday_office_worker",
        }
        for human_id in human_ids(human_count)
    ]


def prepare_scene(raw_scene: dict[str, Any], robot_count: int, human_count: int) -> dict[str, Any]:
    scene = copy.deepcopy(raw_scene)
    scene.setdefault("world_state", {}).setdefault("step", 0)
    scene["world_state"].setdefault("time_min", 360)
    scene["world_state"].setdefault("minutes_per_step", 10)
    scene["world_state"].setdefault("day", 1)
    if scene_type(scene) == "home":
        for spec in actor_specs_for_scene(scene, human_count):
            human_id = str(spec["id"])
            parent_id = str(spec.get("parent") or "outside_home")
            ensure_node(
                scene,
                {
                    "id": human_id,
                    "name": spec.get("name", "human"),
                    "name_cn": spec.get("name_cn", spec.get("name", "human")),
                    "node_type": "human",
                    "semantic_type": "human",
                    "role": spec.get("role", "resident"),
                    "persona": spec.get("persona", ""),
                    "states": {"current_activity": spec.get("activity", "")},
                    "parent": parent_id,
                    "child": [],
                    "interactive_actions": [],
                },
            )
            ensure_edge(scene, parent_id, human_id, "at")
    for robot_id in robot_ids(robot_count):
        robot_parent = "lobby" if scene_type(scene) == "hospital" else "living_room"
        ensure_node(
            scene,
            {
                "id": robot_id,
                "name": "robot",
                "name_cn": "robot",
                "node_type": "robot",
                "semantic_type": "robot",
                "states": {},
                "parent": robot_parent,
                "child": [],
                "interactive_actions": [],
            },
        )
        ensure_edge(scene, robot_parent, robot_id, "at")
    support_nodes = []
    if scene_type(scene) == "home":
        support_nodes.extend([
        {
            "id": "garbage_station_outside_home",
            "name": "garbage station",
            "name_cn": "垃圾处理站",
            "node_type": "fixed_object",
            "semantic_type": "garbage_station",
            "states": {},
            "parent": "outside_home",
            "child": [],
            "interactive_actions": ["move", "dump"],
        },
        {
            "id": "trash_bin_living_room",
            "name": "trash bin",
            "name_cn": "trash bin",
            "node_type": "movable_object",
            "semantic_type": "trash_bin",
            "states": {"is_dirty": False},
            "parent": "living_room",
            "child": [],
            "interactive_actions": ["pick", "place"],
            "max_capacity": 3,
        },
        {
            "id": "food_living_room",
            "name": "food",
            "name_cn": "food",
            "node_type": "movable_object",
            "semantic_type": "food",
            "states": {"is_cooked": True, "is_rotten": False},
            "parent": "fridge_kitchen",
            "child": [],
            "interactive_actions": ["pick", "place"],
        },
        {
            "id": "plate_living_room",
            "name": "plate",
            "name_cn": "plate",
            "node_type": "movable_object",
            "semantic_type": "plate",
            "states": {"is_dirty": False},
            "parent": "dishwasher_kitchen",
            "child": [],
            "interactive_actions": ["pick", "place", "brush"],
        },
        {
            "id": "cup_living_room",
            "name": "cup",
            "name_cn": "cup",
            "node_type": "movable_object",
            "semantic_type": "cup",
            "states": {"is_dirty": False, "is_wet": False},
            "parent": "dishwasher_kitchen",
            "child": [],
            "interactive_actions": ["pick", "place", "brush"],
        },
        ])
    for item in support_nodes:
        ensure_node(scene, item)
        ensure_edge(scene, str(item["parent"]), str(item["id"]), "in")
    for item in scene.get("nodes") or []:
        if str(item.get("semantic_type") or "") == "sink":
            actions = item.setdefault("interactive_actions", [])
            if "dump" not in actions:
                actions.append("dump")
    return scene


def prepare_home_scene(raw_scene: dict[str, Any], robot_count: int, human_count: int) -> dict[str, Any]:
    return prepare_scene(raw_scene, robot_count=robot_count, human_count=human_count)


def planned_event_for_actor(scene: dict[str, Any], actor: dict[str, Any], step: int) -> str:
    world = scene.get("world_state") or {}
    minute = int(world.get("time_min") or 0) + step * int(world.get("minutes_per_step") or 10)
    day = int(world.get("day") or 1)
    role = str(actor.get("role") or (actor.get("states") or {}).get("role") or "resident")
    _, _, activity = planned_activity(role, minute, day)
    return activity


def planned_event_for_step(scene: dict[str, Any], step: int) -> str:
    actors = [node for node in scene.get("nodes") or [] if str(node.get("node_type") or "") == "human"]
    if not actors:
        return ""
    return planned_event_for_actor(scene, actors[0], step)


def planned_events_for_step(scene: dict[str, Any], step: int) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for actor in scene.get("nodes") or []:
        if str(actor.get("node_type") or "") != "human":
            continue
        actor_id = str(actor.get("id") or "")
        if not actor_id:
            continue
        event_id = planned_event_for_actor(scene, actor, step)
        previous_id = planned_event_for_actor(scene, actor, step - 1) if step > 0 else ""
        next_id = planned_event_for_actor(scene, actor, step + 1)
        events.append(
            {
                "event": event_id,
                "actor": actor_id,
                "period_start": step == 0 or previous_id != event_id,
                "period_end": next_id != event_id,
            }
        )
    return events


def expected_events(scene: dict[str, Any], steps: int) -> tuple[str, ...]:
    if not any(str(node.get("node_type") or "") == "human" for node in scene.get("nodes") or []):
        return ()
    events = []
    for step in range(steps):
        for event in planned_events_for_step(scene, step):
            event_id = str(event.get("event") or "")
            if event_id and event_id not in events:
                events.append(event_id)
    return tuple(events)


def score_scene(
    scene: dict[str, Any],
    baseline: dict[str, Any],
    previous: dict[str, Any],
    expected: tuple[str, ...],
    robot_scene: dict[str, Any],
) -> dict[str, float]:
    return matrix_score(
        build_matrix_snapshot(scene, expected),
        build_matrix_snapshot(baseline, expected),
        build_matrix_snapshot(previous, expected),
        build_matrix_snapshot(robot_scene, expected),
    )


def write_json_array(path: Path, rows: list[dict[str, Any]], *, desc: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("[\n")
        for index, row in enumerate(tqdm(rows, desc=desc, unit="row", dynamic_ncols=True)):
            if index:
                handle.write(",\n")
            handle.write(json.dumps(row, ensure_ascii=False))
        handle.write("\n]\n")


def room_of(scene: dict[str, Any], node_id: str) -> str:
    current_id = str(node_id or "")
    visited: set[str] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        item = node(scene, current_id)
        if not item:
            return ""
        node_type = str(item.get("node_type") or "")
        if node_type == "room":
            return current_id
        current_id = str(item.get("parent") or "")
    return ""


def visible_restore_goal(observation: dict[str, Any], baseline: dict[str, Any], step: int) -> dict[str, Any] | None:
    baseline_nodes = {str(item.get("id") or ""): item for item in baseline.get("nodes") or [] if item.get("id")}
    current_nodes = {str(item.get("id") or ""): item for item in observation.get("nodes") or [] if item.get("id")}
    for node_id, current in sorted(current_nodes.items()):
        initial = baseline_nodes.get(node_id) or {}
        if str(initial.get("node_type") or "") != "movable_object":
            continue
        current_parent = str(current.get("parent") or "")
        initial_parent = str(initial.get("parent") or "")
        if not current_parent or not initial_parent or current_parent == initial_parent:
            continue
        current_parent_node = current_nodes.get(current_parent) or {}
        if str(current_parent_node.get("node_type") or "") == "human":
            parent_states = current_parent_node.get("states") or {}
            if parent_states.get("checked_out") is not True:
                continue
        hospital_skill = hospital_skill_for_return_issue(node_id, current, initial)
        if hospital_skill:
            goal = make_hospital_return_goal(
                node_id,
                hospital_return_target(observation, baseline, node_id, hospital_skill) or initial_parent,
                hospital_skill,
                step,
                source="visible_hospital_supply_issue",
            )
            if goal:
                return goal
        return make_restore_goal(node_id, initial_parent, step, source="visible_spatial_issue")
    return None


def make_restore_goal(object_id: str, target_id: str, step: int, *, source: str) -> dict[str, Any]:
    task = f"restore_initial_position {object_id} -> {target_id}"
    return {
        "type": "restore_initial_position",
        "task": task,
        "object": object_id,
        "target": target_id,
        "started_step": step,
        "last_progress_step": step,
        "steps_without_progress": 0,
        "source": source,
    }


def first_node_by_semantic(scene: dict[str, Any], semantics: set[str], *, room: str = "") -> str:
    for item in scene.get("nodes") or []:
        if str(item.get("semantic_type") or "") not in semantics:
            continue
        if room and room_of(scene, str(item.get("id") or "")) != room:
            continue
        return str(item.get("id") or "")
    return ""


def first_node_by_semantic_near(scene: dict[str, Any], semantics: set[str], *, preferred_room: str = "") -> str:
    if preferred_room:
        near = first_node_by_semantic(scene, semantics, room=preferred_room)
        if near:
            return near
    return first_node_by_semantic(scene, semantics)


def dispose_food_phase(
    scene: dict[str, Any],
    object_id: str,
    trash_bin_id: str = "",
    robot_id: str = "robot_01",
    trash_bin_home: str = "",
) -> str:
    item = node(scene, object_id) or {}
    states = item.get("states") or {}
    if not (states.get("is_rotten") is True or states.get("is_burnt") is True):
        if trash_bin_id and trash_bin_home and str((node(scene, trash_bin_id) or {}).get("parent") or "") != trash_bin_home:
            return "return_bin"
        return "done"
    if trash_bin_id and str(item.get("parent") or "") == trash_bin_id:
        return "dump_bin" if str((node(scene, trash_bin_id) or {}).get("parent") or "") == robot_id else "take_bin"
    if trash_bin_id and str((node(scene, trash_bin_id) or {}).get("parent") or "") == robot_id:
        return "dump_bin"
    return "collect_food"


def make_dispose_food_goal(
    object_id: str,
    step: int,
    *,
    source: str,
    scene: dict[str, Any],
    robot_id: str = "robot_01",
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    object_room = room_of(scene, object_id)
    trash_bin = first_node_by_semantic_near(scene, {"trash_bin"}, preferred_room=object_room)
    garbage_station = first_node_by_semantic(scene, {"garbage_station"})
    if not trash_bin or not garbage_station:
        return None
    baseline_bin = node(baseline or {}, trash_bin) or {}
    baseline_food = node(baseline or {}, object_id) or {}
    trash_bin_home = str(baseline_bin.get("parent") or (node(scene, trash_bin) or {}).get("parent") or "")
    food_home = str(baseline_food.get("parent") or first_node_by_semantic(scene, {"refrigerator", "fridge"}))
    phase = dispose_food_phase(scene, object_id, trash_bin, robot_id, trash_bin_home)
    if phase == "done":
        return None
    return {
        "type": "skill",
        "skill": "dispose_food",
        "task": f"dispose_food {object_id} -> {garbage_station}",
        "object": object_id,
        "target": garbage_station,
        "food_home": food_home,
        "trash_bin": trash_bin,
        "trash_bin_home": trash_bin_home,
        "garbage_station": garbage_station,
        "phase": phase,
        "started_step": step,
        "last_progress_step": step,
        "steps_without_progress": 0,
        "source": source,
    }


def visible_dispose_food_goal(
    observation: dict[str, Any],
    scene: dict[str, Any],
    step: int,
    robot_id: str = "robot_01",
    baseline: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    for item in sorted(observation.get("nodes") or [], key=lambda node_item: str(node_item.get("id") or "")):
        if str(item.get("semantic_type") or "") != "food":
            continue
        states = item.get("states") or {}
        if states.get("is_rotten") is True or states.get("is_burnt") is True:
            return make_dispose_food_goal(
                str(item.get("id") or ""),
                step,
                source="visible_bad_food",
                scene=scene,
                robot_id=robot_id,
                baseline=baseline,
            )
    return None


def empty_cup_phase(scene: dict[str, Any], object_id: str) -> str:
    item = node(scene, object_id) or {}
    states = item.get("states") or {}
    if float(states.get("fill_level") or 0.0) <= 0.0 and states.get("is_full") is not True:
        return "done"
    return "dump_cup"


def make_empty_cup_goal(object_id: str, step: int, *, source: str, scene: dict[str, Any]) -> dict[str, Any] | None:
    object_room = room_of(scene, object_id)
    sink = first_node_by_semantic_near(scene, {"sink"}, preferred_room=object_room)
    if not sink:
        return None
    phase = empty_cup_phase(scene, object_id)
    if phase == "done":
        return None
    return {
        "type": "skill",
        "skill": "empty_cup",
        "task": f"empty_cup {object_id} -> {sink}",
        "object": object_id,
        "target": sink,
        "sink": sink,
        "phase": phase,
        "started_step": step,
        "last_progress_step": step,
        "steps_without_progress": 0,
        "source": source,
    }


def visible_empty_cup_goal(observation: dict[str, Any], scene: dict[str, Any], step: int) -> dict[str, Any] | None:
    for item in sorted(observation.get("nodes") or [], key=lambda node_item: str(node_item.get("id") or "")):
        if str(item.get("semantic_type") or "") != "cup":
            continue
        states = item.get("states") or {}
        if float(states.get("fill_level") or 0.0) > 0.0 or states.get("is_full") is True:
            return make_empty_cup_goal(str(item.get("id") or ""), step, source="visible_full_cup", scene=scene)
    return None


def laundry_phase(scene: dict[str, Any], object_id: str, washer_id: str = "", wardrobe_id: str = "") -> str:
    item = node(scene, object_id) or {}
    states = item.get("states") or {}
    parent = str(item.get("parent") or "")
    if states.get("is_dirty") is True:
        if washer_id and parent == washer_id:
            washer = node(scene, washer_id) or {}
            return "washing_wait" if bool((washer.get("states") or {}).get("is_on", False)) else "start_washer"
        return "wash_load"
    if states.get("is_wet") is True:
        return "dry"
    if states.get("folded") is False:
        return "fold"
    if wardrobe_id and parent != wardrobe_id:
        return "store"
    return "done"


def make_laundry_goal(object_id: str, step: int, *, source: str, scene: dict[str, Any]) -> dict[str, Any] | None:
    washer = first_node_by_semantic(scene, {"washer", "washing_machine"})
    drying_rack = first_node_by_semantic(scene, {"drying_rack"})
    wardrobe = first_node_by_semantic(scene, {"cabinet"}, room="bedroom") or first_node_by_semantic(scene, {"wardrobe"}, room="bedroom")
    if not washer or not drying_rack or not wardrobe:
        return None
    phase = laundry_phase(scene, object_id, washer, wardrobe)
    if phase == "done":
        return None
    return {
        "type": "skill",
        "skill": "laundry_clothes",
        "task": f"laundry_clothes {object_id} -> {wardrobe}",
        "object": object_id,
        "target": wardrobe,
        "washer": washer,
        "washer_button": f"{washer}_button",
        "drying_rack": drying_rack,
        "wardrobe": wardrobe,
        "phase": phase,
        "started_step": step,
        "last_progress_step": step,
        "steps_without_progress": 0,
        "source": source,
    }


def visible_laundry_goal(observation: dict[str, Any], scene: dict[str, Any], step: int) -> dict[str, Any] | None:
    for item in sorted(observation.get("nodes") or [], key=lambda node_item: str(node_item.get("id") or "")):
        if str(item.get("semantic_type") or "") not in CLOTH_SEMANTICS:
            continue
        states = item.get("states") or {}
        if states.get("is_dirty") is True or states.get("is_wet") is True or states.get("folded") is False:
            return make_laundry_goal(str(item.get("id") or ""), step, source="visible_laundry_issue", scene=scene)
    return None


def hospital_skill_for_return_issue(node_id: str, current: dict[str, Any], initial: dict[str, Any]) -> str:
    semantic = str(current.get("semantic_type") or initial.get("semantic_type") or "")
    if semantic == "bed_sheet":
        states = current.get("states") or {}
        if states.get("is_dirty") is True:
            return "collect_dirty_linen"
        if node_id == "clean_sheet_storage" or states.get("is_clean") is True:
            return "restock_clean_sheet"
        return ""
    return HOSPITAL_SKILL_BY_SEMANTIC.get(semantic, "")


def hospital_return_target(scene: dict[str, Any], baseline: dict[str, Any], object_id: str, skill: str) -> str:
    initial = node(baseline, object_id) or {}
    if skill == "clean_medical_waste":
        return first_node_by_semantic(scene, {"medical_waste_bin"}) or str(initial.get("parent") or "")
    if skill == "collect_dirty_linen":
        return first_node_by_semantic(scene, {"dirty_linen_bin", "linen_bin"}) or str(initial.get("parent") or "")
    if skill == "restock_clean_sheet":
        return first_node_by_semantic(scene, {"supply_cabinet"}) or str(initial.get("parent") or "")
    return str(initial.get("parent") or "")


def make_hospital_return_goal(
    object_id: str,
    target_id: str,
    skill: str,
    step: int,
    *,
    source: str,
) -> dict[str, Any] | None:
    if not object_id or not target_id or skill not in HOSPITAL_RETURN_SKILLS:
        return None
    return {
        "type": "skill",
        "skill": skill,
        "task": f"{skill} {object_id} -> {target_id}",
        "object": object_id,
        "target": target_id,
        "phase": "return_item",
        "started_step": step,
        "last_progress_step": step,
        "steps_without_progress": 0,
        "source": source,
    }


def make_hospital_clean_goal(target_id: str, skill: str, step: int, *, source: str) -> dict[str, Any] | None:
    if not target_id or skill not in HOSPITAL_CLEAN_SKILLS:
        return None
    return {
        "type": "skill",
        "skill": skill,
        "task": f"{skill} {target_id}",
        "object": target_id,
        "target": target_id,
        "phase": "clean_surface",
        "started_step": step,
        "last_progress_step": step,
        "steps_without_progress": 0,
        "source": source,
    }


def hospital_issue_goal(scene: dict[str, Any], baseline: dict[str, Any], robot_id: str, step: int) -> dict[str, Any] | None:
    if scene_type(scene) != "hospital":
        return None
    baseline_nodes = {str(item.get("id") or ""): item for item in baseline.get("nodes") or [] if item.get("id")}
    current_nodes = {str(item.get("id") or ""): item for item in scene.get("nodes") or [] if item.get("id")}
    robot_room = room_of(scene, robot_id)
    candidates: list[tuple[int, int, str, dict[str, Any]]] = []
    for node_id, current in sorted(current_nodes.items()):
        states = current.get("states") or {}
        semantic = str(current.get("semantic_type") or "")
        if node_id == "seats_waiting_area" and states.get("is_dirty") is True:
            priority = 5 if room_of(scene, node_id) == robot_room else 25
            goal = make_hospital_clean_goal(node_id, "clean_waiting_area", step, source="global_hospital_dirty_surface")
            if goal:
                candidates.append((priority, HOSPITAL_SKILL_PRIORITY["clean_waiting_area"], node_id, goal))
        if semantic == "bed" and (states.get("is_dirty") is True or states.get("needs_cleaning") is True):
            priority = 5 if room_of(scene, node_id) == robot_room else 25
            goal = make_hospital_clean_goal(node_id, "clean_exam_bed", step, source="global_hospital_dirty_bed")
            if goal:
                candidates.append((priority, HOSPITAL_SKILL_PRIORITY["clean_exam_bed"], node_id, goal))
        initial = baseline_nodes.get(node_id) or {}
        skill = hospital_skill_for_return_issue(node_id, current, initial)
        if not skill:
            continue
        current_parent = str(current.get("parent") or "")
        initial_parent = str(initial.get("parent") or "")
        target_id = hospital_return_target(scene, baseline, node_id, skill) or initial_parent
        if not current_parent or not target_id or current_parent == target_id:
            continue
        current_parent_node = node(scene, current_parent) or {}
        if str(current_parent_node.get("node_type") or "") == "human":
            parent_states = current_parent_node.get("states") or {}
            if parent_states.get("checked_out") is not True:
                continue
        current_room = room_of(scene, current_parent)
        initial_room = room_of(scene, target_id) or room_of(baseline, initial_parent)
        priority = 40
        if current_parent == robot_id:
            priority = 0
        elif current_room == robot_room:
            priority = 10
        elif initial_room == robot_room:
            priority = 20
        elif current_room:
            priority = 30
        goal = make_hospital_return_goal(node_id, target_id, skill, step, source="global_hospital_supply_issue")
        if goal:
            candidates.append((priority, HOSPITAL_SKILL_PRIORITY.get(skill, 99), node_id, goal))
    if not candidates:
        return None
    _, _, _, goal = min(candidates, key=lambda item: (item[0], item[1], item[2]))
    return goal


def global_restore_goal(scene: dict[str, Any], baseline: dict[str, Any], robot_id: str, step: int) -> dict[str, Any] | None:
    baseline_nodes = {str(item.get("id") or ""): item for item in baseline.get("nodes") or [] if item.get("id")}
    current_nodes = {str(item.get("id") or ""): item for item in scene.get("nodes") or [] if item.get("id")}
    robot_room = room_of(scene, robot_id)
    hospital_goal = hospital_issue_goal(scene, baseline, robot_id, step)
    if hospital_goal:
        return hospital_goal
    dispose_candidates: list[tuple[int, str]] = []
    for node_id, current in sorted(current_nodes.items()):
        if str(current.get("semantic_type") or "") != "food":
            continue
        states = current.get("states") or {}
        if not (states.get("is_rotten") is True or states.get("is_burnt") is True):
            continue
        current_parent = str(current.get("parent") or "")
        current_parent_node = node(scene, current_parent) or {}
        if str(current_parent_node.get("node_type") or "") == "human":
            continue
        current_room = room_of(scene, current_parent)
        priority = 10 if current_room == robot_room else 30
        if current_parent == robot_id:
            priority = 0
        dispose_candidates.append((priority, node_id))
    if dispose_candidates:
        _, object_id = min(dispose_candidates)
        goal = make_dispose_food_goal(object_id, step, source="global_bad_food", scene=scene, robot_id=robot_id, baseline=baseline)
        if goal:
            return goal
    cup_candidates: list[tuple[int, str]] = []
    for node_id, current in sorted(current_nodes.items()):
        if str(current.get("semantic_type") or "") != "cup":
            continue
        states = current.get("states") or {}
        if not (float(states.get("fill_level") or 0.0) > 0.0 or states.get("is_full") is True):
            continue
        current_parent = str(current.get("parent") or "")
        current_room = room_of(scene, current_parent)
        priority = 10 if current_room == robot_room else 30
        if current_parent == robot_id:
            priority = 0
        cup_candidates.append((priority, node_id))
    if cup_candidates:
        _, object_id = min(cup_candidates)
        goal = make_empty_cup_goal(object_id, step, source="global_full_cup", scene=scene)
        if goal:
            return goal
    laundry_candidates: list[tuple[int, str]] = []
    for node_id, current in sorted(current_nodes.items()):
        if str(current.get("semantic_type") or "") not in CLOTH_SEMANTICS:
            continue
        states = current.get("states") or {}
        if not (states.get("is_dirty") is True or states.get("is_wet") is True or states.get("folded") is False):
            continue
        current_parent = str(current.get("parent") or "")
        current_parent_node = node(scene, current_parent) or {}
        if str(current_parent_node.get("node_type") or "") == "human":
            continue
        current_room = room_of(scene, current_parent)
        priority = 10 if current_room == robot_room else 30
        if current_parent == robot_id:
            priority = 0
        laundry_candidates.append((priority, node_id))
    if laundry_candidates:
        _, object_id = min(laundry_candidates)
        goal = make_laundry_goal(object_id, step, source="global_laundry_issue", scene=scene)
        if goal:
            return goal
    candidates: list[tuple[int, str, str]] = []
    for node_id, current in sorted(current_nodes.items()):
        initial = baseline_nodes.get(node_id) or {}
        if str(initial.get("node_type") or "") != "movable_object":
            continue
        current_parent = str(current.get("parent") or "")
        initial_parent = str(initial.get("parent") or "")
        if not current_parent or not initial_parent or current_parent == initial_parent:
            continue
        current_parent_node = node(scene, current_parent) or {}
        if str(current_parent_node.get("node_type") or "") == "human":
            continue
        current_room = room_of(scene, current_parent)
        initial_room = room_of(baseline, initial_parent)
        priority = 50
        if current_parent == robot_id:
            priority = 0
        elif current_room == robot_room:
            priority = 10
        elif initial_room == robot_room:
            priority = 20
        elif current_room:
            priority = 30
        candidates.append((priority, node_id, initial_parent))
    if not candidates:
        return None
    _, object_id, target_id = min(candidates)
    return make_restore_goal(object_id, target_id, step, source="global_spatial_issue")


def next_room_toward(scene: dict[str, Any], start_room: str, target_room: str) -> str:
    if not start_room or not target_room or start_room == target_room:
        return ""
    graph: dict[str, set[str]] = {}
    for edge in scene.get("edges") or []:
        relation = str(edge.get("relation") or "").lower()
        if relation not in {"connected", "connected_to", "next_to", "neighbour"}:
            continue
        source = str(edge.get("source_id") or "")
        target = str(edge.get("target_id") or "")
        if source and target:
            graph.setdefault(source, set()).add(target)
            graph.setdefault(target, set()).add(source)
    queue: list[tuple[str, list[str]]] = [(start_room, [start_room])]
    seen = {start_room}
    while queue:
        room_id, path = queue.pop(0)
        for neighbor in sorted(graph.get(room_id, ())):
            if neighbor in seen:
                continue
            next_path = [*path, neighbor]
            if neighbor == target_room:
                return next_path[1] if len(next_path) > 1 else ""
            seen.add(neighbor)
            queue.append((neighbor, next_path))
    return ""


def refresh_active_goal_snapshot(goal: dict[str, Any], scene: dict[str, Any], robot_id: str) -> dict[str, Any]:
    updated = copy.deepcopy(goal)
    object_id = str(updated.get("object") or "")
    object_node = node(scene, object_id) or {}
    robot_node = node(scene, robot_id) or {}
    target_id = str(updated.get("target") or "")
    skill = str(updated.get("skill") or "")
    destination_room_override = ""
    if str(updated.get("type") or "") == "skill" and skill == "dispose_food":
        trash_bin = str(updated.get("trash_bin") or first_node_by_semantic_near(scene, {"trash_bin"}, preferred_room=room_of(scene, object_id)))
        garbage_station = str(updated.get("garbage_station") or first_node_by_semantic(scene, {"garbage_station"}))
        updated["trash_bin"] = trash_bin
        updated["garbage_station"] = garbage_station
        updated["target"] = garbage_station
        trash_bin_home = str(updated.get("trash_bin_home") or (node(scene, trash_bin) or {}).get("parent") or "")
        updated["trash_bin_home"] = trash_bin_home
        updated["phase"] = dispose_food_phase(scene, object_id, trash_bin, robot_id, trash_bin_home)
        phase = str(updated.get("phase") or "")
        target_by_phase = {
            "collect_food": trash_bin,
            "take_bin": trash_bin,
            "dump_bin": garbage_station,
            "return_bin": trash_bin_home,
        }
        target_id = target_by_phase.get(phase, garbage_station)
        if phase == "collect_food":
            destination_room_override = room_of(scene, trash_bin) if str(object_node.get("parent") or "") == robot_id else room_of(scene, object_id)
        elif phase == "take_bin":
            destination_room_override = room_of(scene, trash_bin)
        elif phase == "dump_bin":
            destination_room_override = room_of(scene, garbage_station)
        elif phase == "return_bin":
            destination_room_override = room_of(scene, trash_bin_home)
    if str(updated.get("type") or "") == "skill" and skill == "empty_cup":
        sink = str(updated.get("sink") or first_node_by_semantic_near(scene, {"sink"}, preferred_room=room_of(scene, object_id)))
        updated["sink"] = sink
        updated["target"] = sink
        updated["phase"] = empty_cup_phase(scene, object_id)
        target_id = sink
        if str(object_node.get("parent") or "") == robot_id:
            destination_room_override = room_of(scene, sink)
    if str(updated.get("type") or "") == "skill" and skill == "laundry_clothes":
        washer = str(updated.get("washer") or first_node_by_semantic(scene, {"washer", "washing_machine"}))
        drying_rack = str(updated.get("drying_rack") or first_node_by_semantic(scene, {"drying_rack"}))
        wardrobe = str(updated.get("wardrobe") or first_node_by_semantic(scene, {"cabinet"}, room="bedroom") or first_node_by_semantic(scene, {"wardrobe"}, room="bedroom"))
        updated["washer"] = washer
        updated["washer_button"] = str(updated.get("washer_button") or f"{washer}_button")
        updated["drying_rack"] = drying_rack
        updated["wardrobe"] = wardrobe
        updated["target"] = wardrobe
        updated["phase"] = laundry_phase(scene, object_id, washer, wardrobe)
        target_by_phase = {
            "wash_load": washer,
            "start_washer": washer,
            "washing_wait": washer,
            "dry": drying_rack,
            "fold": object_id,
            "store": wardrobe,
        }
        target_id = target_by_phase.get(str(updated.get("phase") or ""), wardrobe)
    if str(updated.get("type") or "") == "skill" and skill in HOSPITAL_RETURN_SKILLS:
        target_id = str(updated.get("target") or "")
        updated["phase"] = "done" if object_node and str(object_node.get("parent") or "") == target_id else "return_item"
        if str(object_node.get("parent") or "") == robot_id:
            destination_room_override = room_of(scene, target_id)
    if str(updated.get("type") or "") == "skill" and skill in HOSPITAL_CLEAN_SKILLS:
        target_id = str(updated.get("target") or object_id)
        target_node = node(scene, target_id) or {}
        target_states = target_node.get("states") or {}
        updated["phase"] = (
            "clean_surface"
            if target_states.get("is_dirty") is True or target_states.get("needs_cleaning") is True
            else "done"
        )
        destination_room_override = room_of(scene, target_id)
    updated["object_parent"] = str(object_node.get("parent") or "")
    updated["object_room"] = room_of(scene, object_id)
    updated["target_room"] = room_of(scene, target_id)
    updated["robot_parent"] = str(robot_node.get("parent") or "")
    updated["robot_room"] = room_of(scene, robot_id)
    destination_room = destination_room_override or (updated["target_room"] if updated["object_parent"] == robot_id else updated["object_room"])
    updated["next_room"] = next_room_toward(scene, updated["robot_room"], destination_room)
    return updated


def active_goal_ids_valid(goal: dict[str, Any] | None, scene: dict[str, Any]) -> bool:
    if not goal:
        return False
    node_ids = {str(item.get("id") or "") for item in scene.get("nodes") or [] if item.get("id")}
    fields = ("object", "target", "food_home", "trash_bin", "trash_bin_home", "garbage_station", "sink", "washer", "drying_rack", "wardrobe")
    return all(str(goal.get(field) or "") in node_ids for field in fields if goal.get(field))


def active_goal_completed(goal: dict[str, Any] | None, scene: dict[str, Any]) -> bool:
    if not goal:
        return False
    if not active_goal_ids_valid(goal, scene):
        return True
    object_node = node(scene, str(goal.get("object") or "")) or {}
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") == "laundry_clothes":
        states = object_node.get("states") or {}
        return bool(
            object_node
            and str(object_node.get("parent") or "") == str(goal.get("wardrobe") or goal.get("target") or "")
            and states.get("is_dirty") is False
            and states.get("is_wet") is False
            and states.get("folded") is True
        )
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") == "dispose_food":
        states = object_node.get("states") or {}
        trash_bin_node = node(scene, str(goal.get("trash_bin") or "")) or {}
        return bool(
            object_node
            and str(object_node.get("parent") or "") == str(goal.get("food_home") or "")
            and str(trash_bin_node.get("parent") or "") == str(goal.get("trash_bin_home") or "")
            and states.get("is_rotten") is False
            and states.get("is_burnt") is False
        )
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") == "empty_cup":
        states = object_node.get("states") or {}
        return bool(object_node and float(states.get("fill_level") or 0.0) <= 0.0 and states.get("is_full") is not True)
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") in HOSPITAL_RETURN_SKILLS:
        return bool(object_node and str(object_node.get("parent") or "") == str(goal.get("target") or ""))
    if str(goal.get("type") or "") == "skill" and str(goal.get("skill") or "") in HOSPITAL_CLEAN_SKILLS:
        target_node = node(scene, str(goal.get("target") or goal.get("object") or "")) or {}
        states = target_node.get("states") or {}
        return bool(target_node and states.get("is_dirty") is not True and states.get("needs_cleaning") is not True)
    return bool(object_node and str(object_node.get("parent") or "") == str(goal.get("target") or ""))


def active_goal_claims(goal: dict[str, Any] | None) -> set[str]:
    if not goal:
        return set()
    claims = {str(goal.get("object") or "")}
    skill = str(goal.get("skill") or "")
    if skill == "dispose_food":
        claims.add(str(goal.get("trash_bin") or ""))
    if skill == "empty_cup":
        claims.add(str(goal.get("sink") or goal.get("target") or ""))
    if skill == "laundry_clothes":
        claims.add(str(goal.get("washer") or ""))
        claims.add(str(goal.get("drying_rack") or ""))
        claims.add(str(goal.get("wardrobe") or goal.get("target") or ""))
    if skill in HOSPITAL_RETURN_SKILLS | HOSPITAL_CLEAN_SKILLS:
        claims.add(str(goal.get("target") or ""))
    if str(goal.get("type") or "") == "restore_initial_position":
        claims.add(str(goal.get("target") or ""))
    return {claim for claim in claims if claim}


def goal_conflicts_with_claims(goal: dict[str, Any] | None, claimed: set[str]) -> bool:
    if not goal:
        return False
    return bool(active_goal_claims(goal) & claimed)


def action_conflict_key(action: dict[str, Any]) -> tuple[str, str]:
    action_name = str(action.get("action") or "")
    target_id = str(action.get("target") or "")
    object_id = str(action.get("object") or "")
    if action_name == "pick" and object_id:
        return ("object", object_id)
    if action_name == "place" and object_id:
        return ("object", object_id)
    if action_name in {"brush", "fold", "dump", "open", "close", "press"} and target_id:
        return ("target", target_id)
    return ("", "")


def choose_non_conflicting_action(candidates: list[dict[str, Any]], blocked_keys: set[tuple[str, str]]) -> dict[str, Any] | None:
    for preferred_action in ("move", "open", "close"):
        for candidate in candidates:
            if str(candidate.get("action") or "") != preferred_action:
                continue
            key = action_conflict_key(candidate)
            if not key[0] or key not in blocked_keys:
                replacement = copy.deepcopy(candidate)
                replacement["reason"] = f"conflict fallback: choose non-conflicting {preferred_action}"
                return replacement
    for candidate in candidates:
        key = action_conflict_key(candidate)
        if not key[0] or key not in blocked_keys:
            replacement = copy.deepcopy(candidate)
            replacement["reason"] = "conflict fallback: choose non-conflicting action"
            return replacement
    return None


def resolve_robot_action_conflicts(
    actions: list[dict[str, Any]],
    candidates_by_robot: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    used_keys: set[tuple[str, str]] = set()
    resolved: list[dict[str, Any]] = []
    for action in actions:
        robot_id = str(action.get("agent") or "")
        key = action_conflict_key(action)
        if key[0] and key in used_keys:
            replacement = choose_non_conflicting_action(candidates_by_robot.get(robot_id) or [], used_keys)
            if replacement:
                action = replacement
                key = action_conflict_key(action)
        resolved.append(action)
        if key[0]:
            used_keys.add(key)
    return resolved


def update_active_goal(
    goal: dict[str, Any] | None,
    scene: dict[str, Any],
    robot_id: str,
    action: dict[str, Any],
    action_result: dict[str, Any],
    step: int,
    *,
    max_stale_steps: int = 12,
) -> dict[str, Any] | None:
    if not goal:
        return None
    if active_goal_completed(goal, scene):
        return None
    before_object_parent = str(goal.get("object_parent") or "")
    before_robot_parent = str(goal.get("robot_parent") or "")
    before_robot_room = str(goal.get("robot_room") or "")
    updated = refresh_active_goal_snapshot(goal, scene, robot_id)
    if not active_goal_ids_valid(updated, scene):
        return None
    meaningful_action = str(action.get("action") or "") in {"pick", "place", "brush", "dump", "fold", "press"}
    action_ok = bool(action_result.get("ok", action.get("legal", True)))
    progressed = (
        str(updated.get("object_parent") or "") != before_object_parent
        or str(updated.get("robot_parent") or "") != before_robot_parent
        or str(updated.get("robot_room") or "") != before_robot_room
        or (action_ok and meaningful_action)
    )
    if progressed:
        updated["last_progress_step"] = step
        updated["steps_without_progress"] = 0
    else:
        updated["steps_without_progress"] = int(updated.get("steps_without_progress") or 0) + 1
    if int(updated.get("steps_without_progress") or 0) >= max_stale_steps:
        return None
    return updated


def matrix_figure(scene: dict[str, Any], expected: tuple[str, ...], *, kind: str) -> plt.Figure:
    snapshot = build_matrix_snapshot(scene, expected)
    if kind == "state":
        data = []
        for row in snapshot.state_matrix:
            encoded = []
            for value in row:
                if value is None:
                    encoded.append(-1)
                elif isinstance(value, str):
                    encoded.append(0.5)
                else:
                    encoded.append(int(value))
            data = [*data, encoded]
        fig_width = max(7, len(snapshot.state_columns) * 0.55)
        fig_height = max(5, len(snapshot.node_ids) * 0.18)
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        image = ax.imshow(data, aspect="auto", vmin=-1, vmax=1, cmap="viridis")
        ax.set_xticks(range(len(snapshot.state_columns)))
        ax.set_xticklabels(snapshot.state_columns, rotation=90, fontsize=6)
        ax.set_yticks(range(len(snapshot.node_ids)))
        ax.set_yticklabels(snapshot.node_ids, fontsize=5)
        ax.set_title("state_matrix")
        fig.colorbar(image, ax=ax, fraction=0.018, pad=0.01)
    else:
        data = snapshot.node_relation_matrix
        size = len(snapshot.node_ids)
        fig_size = max(6, min(18, size * 0.22))
        fig, ax = plt.subplots(figsize=(fig_size, fig_size))
        ax.imshow(data, aspect="equal", vmin=0, vmax=1, cmap="Greys")
        ax.set_xticks(range(size))
        ax.set_xticklabels(snapshot.node_ids, rotation=90, fontsize=4)
        ax.set_yticks(range(size))
        ax.set_yticklabels(snapshot.node_ids, fontsize=4)
        ax.set_title("spatial_matrix")
    fig.tight_layout()
    return fig


def save_step_matrices(
    snapshot: Any,
    *,
    step: int,
    output_dir: Path,
) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"step_{step:04d}.json"
    payload = {
        "step": step,
        "node_ids": list(snapshot.node_ids),
        "movable_node_ids": list(snapshot.movable_node_ids),
        "state_columns": list(snapshot.state_columns),
        "state_matrix": [list(row) for row in snapshot.state_matrix],
        "node_relation_matrix": [list(row) for row in snapshot.node_relation_matrix],
        "human_events": list(snapshot.human_events),
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(out_path)


def check_llm_agent(agent_model: str, timeout: float = 30.0) -> tuple[bool, str]:
    try:
        cfg = resolved_agent_config(agent_model)
    except Exception:
        return False, f"unsupported agent: {agent_model}"
    served_name = str(cfg.get("model") or agent_model)
    if cfg.get("type") != "openai":
        return True, served_name
    base_url = str(cfg.get("base_url") or "").rstrip("/")
    if not base_url:
        return False, f"missing base_url for agent: {agent_model}"
    try:
        health_url = base_url.rsplit("/v1", 1)[0] + "/health"
        request = urllib.request.Request(health_url)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:
            response.read()
        return True, served_name
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def require_llm_agent(agent_model: str) -> str:
    model_ok, model_status = check_llm_agent(agent_model)
    if not model_ok:
        raise RuntimeError(f"LLM agent is required but unavailable: {model_status}")
    return model_status


def build_room_index(scene: dict[str, Any]) -> dict[str, int]:
    rooms = sorted(
        str(item.get("id") or "")
        for item in scene.get("nodes") or []
        if str(item.get("node_type") or "") == "room" and str(item.get("id") or "")
    )
    return {room_id: index for index, room_id in enumerate(rooms)}


def build_trajectory_figure(
    replay_steps: list[dict[str, Any]],
    room_index_map: dict[str, int],
    *,
    kind: str,
) -> plt.Figure:
    xs = [int(step.get("episode_step") or index) for index, step in enumerate(replay_steps)]
    fig, ax = plt.subplots(figsize=(12, 4.5))
    if kind == "action":
        ys = [
            ACTION_CODES.get(str((step.get("action") or {}).get("action") or ""), -1)
            for step in replay_steps
        ]
        ax.plot(xs, ys, marker="o", markersize=3, linewidth=1.2, color="#1565c0")
        ax.set_yticks(list(ACTION_CODES.values()))
        ax.set_yticklabels(list(ACTION_CODES.keys()))
        ax.set_ylabel("action")
        ax.set_title("action_timeline")
    else:
        ys = [
            room_index_map.get(str((step.get("robot_state") or {}).get("room_id") or ""), -1)
            for step in replay_steps
        ]
        ax.plot(xs, ys, marker="o", markersize=3, linewidth=1.2, color="#2e7d32")
        ordered_rooms = sorted(room_index_map.items(), key=lambda item: item[1])
        ax.set_yticks([index for _, index in ordered_rooms])
        ax.set_yticklabels([room_id for room_id, _ in ordered_rooms])
        ax.set_ylabel("room")
        ax.set_title("room_timeline")
    ax.set_xlabel("step")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def run_episode(
    raw_scene: dict[str, Any],
    *,
    scene_id: str,
    steps: int,
    robot_count: int,
    human_count: int,
    run_id: str,
    agent_model: str,
    use_llm: bool,
    expected: tuple[str, ...],
    output_dir: Path,
    matrix_viz: bool,
    replay_scene_interval: int = 1,
    metric_log_interval: int = 1,
) -> dict[str, Any]:
    scene = prepare_scene(raw_scene, robot_count=robot_count, human_count=human_count)
    baseline = copy.deepcopy(scene)
    room_index_map = build_room_index(scene)
    orchestrator = Orchestrator(scene)
    memories: dict[str, dict[str, Any] | None] = {robot_id: None for robot_id in robot_ids(robot_count)}
    active_goals: dict[str, dict[str, Any] | None] = {robot_id: None for robot_id in robot_ids(robot_count)}
    records: list[dict[str, Any]] = []
    replay_steps: list[dict[str, Any]] = []
    cumulative_state_score = 0.0
    cumulative_spatial_score = 0.0
    experiment_name = "with_robot" if robot_count else "no_robot"
    experiment_output_dir = output_dir / experiment_name
    experiment_output_dir.mkdir(parents=True, exist_ok=True)
    matrix_output_dir = experiment_output_dir / "matrices"
    model_name = agent_model if robot_count else "npc_only_baseline"
    tb_dir = TENSORBOARD_DIR / _slug(scene_id) / canonical_run_group(
        scene_id,
        experiment_name,
        model_name,
        steps,
        robot_count,
        human_count,
    ) / run_id
    tb_dir.mkdir(parents=True, exist_ok=True)
    writer = TensorBoardWriter(tb_dir)
    replay_path = experiment_output_dir / "replay.json"
    model_ok = bool(robot_count and use_llm)
    model_status = require_llm_agent(agent_model) if model_ok else "not_used"
    previous_snapshot = build_matrix_snapshot(orchestrator.graph.to_scene(), expected)
    baseline_snapshot = build_matrix_snapshot(baseline, expected)
    matrix_paths: list[str] = []
    replay_scene_interval = max(0, int(replay_scene_interval))
    metric_log_interval = max(1, int(metric_log_interval))
    for step in tqdm(range(steps), desc=experiment_name, unit="step", dynamic_ncols=True):
        schedule_scene = orchestrator.graph.to_scene()
        event_id = planned_event_for_step(schedule_scene, step)
        human_events = planned_events_for_step(schedule_scene, step)
        actions: list[dict[str, Any]] = []
        candidates_by_robot: dict[str, list[dict[str, Any]]] = {}
        llm_answers: dict[str, str] = {}
        observations: dict[str, dict[str, Any]] = {}
        claimed_goal_nodes: set[str] = set()
        for robot_id in robot_ids(robot_count):
            claimed_goal_nodes.update(
                claim
                for other_robot_id, goal in active_goals.items()
                if other_robot_id != robot_id
                for claim in active_goal_claims(goal)
            )
            if active_goals.get(robot_id) is None:
                proposed_goal = global_restore_goal(orchestrator.graph.to_scene(), baseline, robot_id, step)
                if proposed_goal and not goal_conflicts_with_claims(proposed_goal, claimed_goal_nodes):
                    active_goals[robot_id] = refresh_active_goal_snapshot(proposed_goal, orchestrator.graph.to_scene(), robot_id)
            observation = perceive(orchestrator, robot_id)
            observations[robot_id] = observation
            memories[robot_id] = remember(memories.get(robot_id), observation)
            if active_goals.get(robot_id) is None:
                proposed_goal = visible_dispose_food_goal(observation, orchestrator.graph.to_scene(), step, robot_id, baseline)
                if proposed_goal and goal_conflicts_with_claims(proposed_goal, claimed_goal_nodes):
                    proposed_goal = None
                if not proposed_goal:
                    proposed_goal = visible_empty_cup_goal(observation, orchestrator.graph.to_scene(), step)
                    if proposed_goal and goal_conflicts_with_claims(proposed_goal, claimed_goal_nodes):
                        proposed_goal = None
                if not proposed_goal:
                    proposed_goal = visible_laundry_goal(observation, orchestrator.graph.to_scene(), step)
                    if proposed_goal and goal_conflicts_with_claims(proposed_goal, claimed_goal_nodes):
                        proposed_goal = None
                if not proposed_goal:
                    proposed_goal = visible_restore_goal(observation, baseline, step)
                    if proposed_goal and goal_conflicts_with_claims(proposed_goal, claimed_goal_nodes):
                        proposed_goal = None
                if proposed_goal:
                    active_goals[robot_id] = refresh_active_goal_snapshot(proposed_goal, orchestrator.graph.to_scene(), robot_id)
            claimed_goal_nodes.update(active_goal_claims(active_goals.get(robot_id)))
            candidates = candidate_actions(orchestrator, observation, robot_id)
            if not candidates:
                raise RuntimeError(
                    f"no legal candidates for {robot_id} at step {step}; "
                    f"room={orchestrator.graph.room_of.get(robot_id)}; "
                    f"parent={orchestrator.graph.parent_of.get(robot_id)}; "
                    f"visible={len(observation.get('nodes') or [])}"
                )
            candidates_by_robot[robot_id] = candidates
            if use_llm:
                action, llm_answer = llm_choose_action(
                    candidates,
                    observation,
                    agent_model,
                    baseline,
                    active_goal=active_goals.get(robot_id),
                    agent_id=robot_id,
                )
                llm_answers[robot_id] = llm_answer
            else:
                action = fallback_choose_action(candidates)
            actions.append(action)
        actions = resolve_robot_action_conflicts(actions, candidates_by_robot)
        result = orchestrator.step(
            robot_actions=actions,
            human_events=human_events,
            capture_robot_scene=bool(robot_count),
            capture_scene=False,
        )
        for robot_id in robot_ids(robot_count):
            memories[robot_id] = reflect(memories.get(robot_id), result)
        current = orchestrator.graph.to_scene()
        action_results = {
            robot_id: copy.deepcopy(action_result)
            for robot_id, action_result in zip(robot_ids(robot_count), result.get("robot_actions") or [])
        }
        actions_by_robot = {str(action.get("agent") or ""): action for action in actions}
        for robot_id in robot_ids(robot_count):
            active_goals[robot_id] = update_active_goal(
                active_goals.get(robot_id),
                current,
                robot_id,
                actions_by_robot.get(robot_id, {}),
                action_results.get(robot_id, {}),
                step,
            )
        current_snapshot = build_matrix_snapshot(current, expected)
        robot_snapshot = build_matrix_snapshot(result["robot_scene"], expected) if robot_count else current_snapshot
        metrics = matrix_score(current_snapshot, baseline_snapshot, previous_snapshot, robot_snapshot)
        metrics.pop("robot_score", None)
        cumulative_state_score += float(metrics["state_score"])
        cumulative_spatial_score += float(metrics["spatial_score"])
        metrics["state_score"] = round(cumulative_state_score / (step + 1), 4)
        metrics["spatial_score"] = round(cumulative_spatial_score / (step + 1), 4)
        metrics["final_score"] = round(
            float(metrics["state_score"]) * 0.45
            + float(metrics["spatial_score"]) * 0.35
            + float(metrics["human_event_score"]) * 0.20,
            4,
        )
        previous_snapshot = current_snapshot
        primary_action = actions[0] if actions else {}
        action_name = str(primary_action.get("action") or "")
        if step % metric_log_interval == 0 or step + 1 == steps:
            for key in SCORE_KEYS:
                writer.add_scalar(f"scores/{key}", float(metrics[key]), step)
            writer.add_scalar("actions/action_code", ACTION_CODES.get(action_name, -1), step)
        if matrix_viz:
            matrix_paths.append(
                save_step_matrices(
                    current_snapshot,
                    step=step,
                    output_dir=matrix_output_dir,
                )
            )
        row = {
            "step": step,
            "experiment": experiment_name,
            "event": event_id,
            "action": action_name,
            "target": primary_action.get("target", ""),
            "action_reason": primary_action.get("reason", ""),
            "action_legal": all(bool(action.get("legal", True)) for action in actions) if actions else True,
            "validation_failures": json.dumps(
                {str(action.get("agent") or ""): action.get("validation_failures", []) for action in actions},
                ensure_ascii=False,
            ),
            "llm_answer": json.dumps(llm_answers, ensure_ascii=False),
            "active_goal": json.dumps(active_goals, ensure_ascii=False),
            **metrics,
        }
        records.append(row)
        primary_robot = robot_ids(robot_count)[0] if robot_count else ""
        robot_room = room_of(current, primary_robot) if primary_robot else ""
        if primary_robot and robot_room:
            writer.add_scalar("trajectory/room_index", room_index_map.get(robot_room, -1), step)
        include_scene = replay_scene_interval > 0 and (step % replay_scene_interval == 0 or step + 1 == steps)
        replay_steps.append(
            {
                "episode_step": step,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reasoning": json.dumps(llm_answers, ensure_ascii=False) if robot_count else "npc_only_baseline",
                "planner": {
                    "mode": "llm" if robot_count and use_llm and model_ok else ("heuristic" if robot_count else "npc_only_baseline"),
                    "event": event_id,
                },
                "action": copy.deepcopy(primary_action),
                "robot_actions": copy.deepcopy(actions),
                "ok": all(bool(action.get("legal", True)) for action in actions) if actions else True,
                "failed_preconds": {
                    str(action.get("agent") or ""): copy.deepcopy(action.get("validation_failures") or [])
                    for action in actions
                },
                "observation": copy.deepcopy(observations),
                "memory_before": {},
                "memory_after": copy.deepcopy(memories),
                "active_goals": copy.deepcopy(active_goals),
                "event_log": copy.deepcopy(human_events),
                "scene_metrics": {
                    "world_metrics": {
                        "world_score": float(metrics["final_score"]),
                        "human_score": float(metrics["human_event_score"]),
                    },
                    "top_issues": [],
                },
                "world_score": float(metrics["final_score"]),
                "scene": copy.deepcopy(current) if include_scene else {},
                "robot_state": {
                    "room_id": robot_room,
                    "holding": held_object(orchestrator, primary_robot) if primary_robot else "",
                },
                "robot_states": {
                    robot_id: {
                        "room_id": room_of(current, robot_id),
                        "holding": held_object(orchestrator, robot_id),
                    }
                    for robot_id in robot_ids(robot_count)
                },
            }
        )
    writer.add_text(
        "trajectory/room_index_map",
        "\n".join(f"{index}: {room_id}" for room_id, index in sorted(room_index_map.items(), key=lambda item: item[1])),
        0,
    )
    tqdm.write(f"{experiment_name}: flushing tensorboard")
    writer.flush()
    writer.close()
    tqdm.write(f"{experiment_name}: writing replay to {replay_path}")
    write_json_array(replay_path, replay_steps, desc=f"{experiment_name} replay")
    csv_path = experiment_output_dir / "metrics.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer_csv = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer_csv.writeheader()
        writer_csv.writerows(records)
    return {
        "experiment": experiment_name,
        "records": records,
        "tensorboard_log_dir": str(tb_dir),
        "replay_path": str(replay_path),
        "metrics_csv": str(csv_path),
        "matrix_dir": str(matrix_output_dir) if matrix_viz else "",
        "matrix_count": len(matrix_paths),
        "model_ok": model_ok,
        "model_status": model_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="simple_home_1f")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--agent-model", default="vllm-qwen3.5-4b")
    parser.add_argument("--robots", type=int, default=1)
    parser.add_argument("--humans", type=int, default=1)
    parser.add_argument("--no-clean", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--only", choices=("both", "no_robot", "with_robot"), default="both")
    parser.add_argument("--matrix-viz", action="store_true")
    parser.add_argument("--replay-scene-interval", type=int, default=1)
    parser.add_argument("--metric-log-interval", type=int, default=1)
    args = parser.parse_args()
    robots = max(0, int(args.robots))
    humans = max(0, int(args.humans))
    group_robots = 0 if args.only == "no_robot" else robots
    if not args.no_clean:
        clean_old_outputs()
    run_id = utc_run_id()
    scene_id = str(args.scene or "simple_home_1f").removesuffix(".json")
    experiment_model = (
        "npc_only_baseline"
        if group_robots == 0
        else ("heuristic" if args.no_llm else args.agent_model)
    )
    experiment_group = canonical_experiment_group(scene_id, args.steps, group_robots, humans, experiment_model)
    output_dir = EXPERIMENT_DIR / _slug(scene_id) / experiment_group / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_path = SCENE_DIR / f"{scene_id}.json"
    raw_scene = json.loads(scene_path.read_text(encoding="utf-8"))
    expected = expected_events(prepare_scene(raw_scene, robot_count=robots, human_count=humans), args.steps)
    results = []
    if args.only in {"both", "no_robot"}:
        results.append(
            run_episode(
                raw_scene,
                scene_id=scene_id,
                steps=args.steps,
                robot_count=0,
                human_count=humans,
                run_id=run_id,
                agent_model=args.agent_model,
                use_llm=False,
                expected=expected,
                output_dir=output_dir,
                matrix_viz=args.matrix_viz,
                replay_scene_interval=args.replay_scene_interval,
                metric_log_interval=args.metric_log_interval,
            )
        )
    if args.only in {"both", "with_robot"}:
        results.append(
            run_episode(
                raw_scene,
                scene_id=scene_id,
                steps=args.steps,
                robot_count=robots,
                human_count=humans,
                run_id=run_id,
                agent_model=args.agent_model,
                use_llm=not args.no_llm,
                expected=expected,
                output_dir=output_dir,
                matrix_viz=args.matrix_viz,
                replay_scene_interval=args.replay_scene_interval,
                metric_log_interval=args.metric_log_interval,
            )
        )
    summary = {
        "run_id": run_id,
        "scene": scene_id,
        "experiment_group": experiment_group,
        "steps": args.steps,
        "agent_model": args.agent_model,
        "robots": group_robots,
        "humans": humans,
        "expected_events": expected,
        "created_at": time.time(),
        "runs": [
            {key: value for key, value in result.items() if key != "records"}
            | {"final_metrics": {score_key: result["records"][-1][score_key] for score_key in SCORE_KEYS}}
            for result in results
        ],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
