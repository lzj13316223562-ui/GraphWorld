from __future__ import annotations

import argparse
import contextlib
import copy
import csv
import io
import json
import re
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

from backend.core.actions import ActionType
from backend.core.assets.npc_library import get_event_spec, planned_activity
from backend.runtime.agent import perceive, reflect, remember
from backend.runtime.engine import Orchestrator
from backend.runtime.eval import build_matrix_snapshot, matrix_score
from backend.tools.agent import llm_query, resolved_agent_config


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SCENE_PATH = DATA_DIR / "sg_output" / "simple_graph" / "simple_home_1f.json"
LEGACY_REPLAY_DIR = DATA_DIR / "replay_logs"
TENSORBOARD_DIR = DATA_DIR / "tensorboard"
EXPERIMENT_DIR = DATA_DIR / "experiments"

SCORE_KEYS = ("final_score", "state_score", "spatial_score", "human_event_score")
ROBOT_ACTIONS = tuple(action.value for action in ActionType)
ACTION_CODES = {
    "move": 1,
    "pick": 2,
    "place": 3,
    "open": 4,
    "close": 5,
    "press": 6,
    "brush": 7,
    "fold": 8,
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
            f"scene_{_slug(scene_id)}",
            f"exp_{_slug(experiment_type)}",
            f"steps_{int(steps)}",
            f"robots_{int(robots)}",
            f"humans_{int(humans)}",
            f"model_{canonical_model_label(agent_model)}",
        )
    )


def canonical_experiment_group(scene_id: str, steps: int, robots: int, humans: int) -> str:
    return "__".join(
        (
            f"scene_{_slug(scene_id)}",
            "exp_home_matrix",
            f"steps_{int(steps)}",
            f"robots_{int(robots)}",
            f"humans_{int(humans)}",
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


def prepare_home_scene(raw_scene: dict[str, Any], robot_count: int, human_count: int) -> dict[str, Any]:
    scene = copy.deepcopy(raw_scene)
    scene.setdefault("world_state", {}).setdefault("step", 0)
    scene["world_state"].setdefault("time_min", 360)
    scene["world_state"].setdefault("minutes_per_step", 10)
    scene["world_state"].setdefault("day", 1)
    for human_id in human_ids(human_count):
        ensure_node(
            scene,
            {
                "id": human_id,
                "name": "resident",
                "name_cn": "resident",
                "node_type": "human",
                "semantic_type": "human",
                "states": {"current_activity": "sleeping"},
                "parent": "bed_bedroom",
                "child": [],
                "interactive_actions": [],
            },
        )
        ensure_edge(scene, "bed_bedroom", human_id, "at")
    for robot_id in robot_ids(robot_count):
        ensure_node(
            scene,
            {
                "id": robot_id,
                "name": "robot",
                "name_cn": "robot",
                "node_type": "robot",
                "semantic_type": "robot",
                "states": {},
                "parent": "living_room",
                "child": [],
                "interactive_actions": [],
            },
        )
        ensure_edge(scene, "living_room", robot_id, "at")
    support_nodes = [
        {
            "id": "food_living_room",
            "name": "food",
            "name_cn": "food",
            "node_type": "movable_object",
            "semantic_type": "food",
            "states": {"is_cooked": True, "is_rotten": False},
            "parent": "coffee_table_living_room",
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
            "parent": "coffee_table_living_room",
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
            "parent": "coffee_table_living_room",
            "child": [],
            "interactive_actions": ["pick", "place", "brush"],
        },
    ]
    for item in support_nodes:
        ensure_node(scene, item)
        ensure_edge(scene, str(item["parent"]), str(item["id"]), "on")
    return scene


def planned_event_for_step(scene: dict[str, Any], step: int) -> str:
    world = scene.get("world_state") or {}
    minute = int(world.get("time_min") or 0) + step * int(world.get("minutes_per_step") or 10)
    day = int(world.get("day") or 1)
    _, _, activity = planned_activity("resident", minute, day)
    return activity


def expected_events(scene: dict[str, Any], steps: int) -> tuple[str, ...]:
    if not any(str(node.get("node_type") or "") == "human" for node in scene.get("nodes") or []):
        return ()
    events = []
    for step in range(steps):
        event_id = planned_event_for_step(scene, step)
        if event_id not in events:
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


def is_same_room(orchestrator: Orchestrator, a: str, b: str) -> bool:
    graph = orchestrator.graph
    return bool(graph.room_of.get(a) and graph.room_of.get(a) == graph.room_of.get(b))


def held_object(orchestrator: Orchestrator, agent_id: str = "robot_01") -> str:
    return orchestrator.graph.held_by(agent_id)


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


def candidate_payload(
    orchestrator: Orchestrator,
    action: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    validation = orchestrator.robot_actions.validate(action)
    return {
        **action,
        "reason": reason,
        "legal": validation.ok,
        "validation_failures": list(validation.failures),
    }


def candidate_actions(orchestrator: Orchestrator, observation: dict[str, Any], agent_id: str = "robot_01") -> list[dict[str, Any]]:
    graph = orchestrator.graph
    candidates: list[dict[str, Any]] = []
    visible_nodes = [graph.nodes.get(str(item.get("id") or "")) or {} for item in observation.get("nodes") or []]
    visible_ids = {str(node.get("id") or "") for node in visible_nodes if node.get("id")}
    holding = held_object(orchestrator, agent_id)
    for room_id in sorted((observation.get("world_state") or {}).get("visible_rooms") or []):
        if room_id and room_id != graph.room_of.get(agent_id):
            candidate = candidate_payload(
                orchestrator,
                {"agent": agent_id, "action": "move", "target": room_id},
                reason="move to visible room",
            )
            if candidate["legal"]:
                candidates.append(candidate)
    for node_id in sorted(visible_ids):
        item = graph.nodes.get(node_id) or {}
        if not item or node_id == agent_id:
            continue
        states = item.get("states") or {}
        actions = {str(action).lower() for action in item.get("interactive_actions") or []}
        if str(item.get("node_type") or "") in {"fixed_object", "control_object"}:
            candidate = candidate_payload(
                orchestrator,
                {"agent": agent_id, "action": "move", "target": node_id},
                reason="move near visible object",
            )
            if candidate["legal"]:
                candidates.append(candidate)
        for action_name in ROBOT_ACTIONS:
            if action_name == "move":
                continue
            if action_name == "place":
                if not holding:
                    continue
                action = {"agent": agent_id, "action": "place", "target": node_id, "object": holding}
            elif action_name == "pick":
                action = {"agent": agent_id, "action": "pick", "target": node_id, "object": node_id}
            else:
                action = {"agent": agent_id, "action": action_name, "target": node_id}
            reason = f"{action_name} visible object"
            if action_name in actions or action_name in {"move", "place"}:
                if states.get("is_dirty") is True and action_name == "brush":
                    reason = "restore dirty object"
                elif states.get("is_open") is True and action_name == "close":
                    reason = "close open object"
                candidate = candidate_payload(orchestrator, action, reason=reason)
                if candidate["legal"]:
                    candidates.append(candidate)
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = (
            str(candidate.get("action") or ""),
            str(candidate.get("target") or ""),
            str(candidate.get("object") or ""),
        )
        deduped[key] = candidate
    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            not bool(item.get("legal")),
            list(ACTION_CODES).index(str(item.get("action") or "")) if str(item.get("action") or "") in ACTION_CODES else 99,
            str(item.get("target") or ""),
        ),
    )
    return ordered


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


def parse_action_index(text: str, fallback: int = 0) -> int:
    try:
        payload = json.loads(text)
        return int(payload.get("action_index", fallback))
    except Exception:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            try:
                payload = json.loads(match.group(0))
                return int(payload.get("action_index", fallback))
            except Exception:
                pass
    return fallback


def llm_choose_action(candidates: list[dict[str, Any]], observation: dict[str, Any], agent_model: str) -> tuple[dict[str, Any], str]:
    if not candidates:
        raise ValueError("no legal action candidates")
    if len(candidates) <= 1:
        return candidates[0], "single_candidate"
    compact_nodes = []
    for item in observation.get("nodes") or []:
        states = item.get("states") or {}
        if states.get("is_dirty") is True or states.get("is_open") is True or item.get("id") == "robot_01":
            compact_nodes.append(
                {
                    "id": item.get("id"),
                    "semantic_type": item.get("semantic_type"),
                    "node_type": item.get("node_type"),
                    "states": states,
                    "parent": item.get("parent"),
                }
            )
    prompt = {
        "task": "Maintain order in the home. Choose one legal action.",
        "visible_nodes": compact_nodes,
        "candidates": [{"action_index": idx, **candidate} for idx, candidate in enumerate(candidates)],
        "response_format": {"action_index": 0},
    }
    answer = llm_query(
        system_prompt=(
            "Return only compact JSON with exactly one field: "
            '{"action_index": <integer>}. '
            "Do not include markdown, explanations, or thinking."
        ),
        user_query=json.dumps(prompt, ensure_ascii=True),
        agent=agent_model,
        timeout=180,
    )
    index = parse_action_index(answer, 0)
    if index < 0 or index >= len(candidates):
        index = 0
    return candidates[index], answer

def fallback_choose_action(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    for action_name in ("brush", "close"):
        for candidate in candidates:
            if candidate.get("action") == action_name:
                return candidate
    return candidates[0]


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
    scene = prepare_home_scene(raw_scene, robot_count=robot_count, human_count=human_count)
    baseline = copy.deepcopy(scene)
    room_index_map = build_room_index(scene)
    orchestrator = Orchestrator(scene)
    memories: dict[str, dict[str, Any] | None] = {robot_id: None for robot_id in robot_ids(robot_count)}
    records: list[dict[str, Any]] = []
    replay_steps: list[dict[str, Any]] = []
    cumulative_state_score = 0.0
    cumulative_spatial_score = 0.0
    experiment_name = "with_robot" if robot_count else "no_robot"
    experiment_output_dir = output_dir / experiment_name
    experiment_output_dir.mkdir(parents=True, exist_ok=True)
    matrix_output_dir = experiment_output_dir / "matrices"
    model_name = agent_model if robot_count else "npc_only_baseline"
    tb_dir = TENSORBOARD_DIR / canonical_run_group(
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
        schedule_scene = {"world_state": orchestrator.graph.world_state}
        event_id = planned_event_for_step(schedule_scene, step)
        event_period_end = step + 1 >= steps or planned_event_for_step(schedule_scene, step + 1) != event_id
        human_events = [
            {"event": event_id, "actor": human_id, "period_end": event_period_end}
            for human_id in human_ids(human_count)
        ]
        actions: list[dict[str, Any]] = []
        llm_answers: dict[str, str] = {}
        observations: dict[str, dict[str, Any]] = {}
        for robot_id in robot_ids(robot_count):
            observation = perceive(orchestrator, robot_id)
            observations[robot_id] = observation
            memories[robot_id] = remember(memories.get(robot_id), observation)
            candidates = candidate_actions(orchestrator, observation, robot_id)
            if not candidates:
                continue
            if use_llm:
                action, llm_answer = llm_choose_action(candidates, observation, agent_model)
                llm_answers[robot_id] = llm_answer
            else:
                action = fallback_choose_action(candidates)
            actions.append(action)
        result = orchestrator.step(
            robot_actions=actions,
            human_events=human_events,
            capture_robot_scene=bool(robot_count),
            capture_scene=False,
        )
        for robot_id in robot_ids(robot_count):
            memories[robot_id] = reflect(memories.get(robot_id), result)
        current = orchestrator.graph.to_scene()
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
    if not args.no_clean:
        clean_old_outputs()
    run_id = utc_run_id()
    scene_id = "simple_home_1f"
    output_dir = EXPERIMENT_DIR / canonical_experiment_group(scene_id, args.steps, robots, humans) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_scene = json.loads(SCENE_PATH.read_text(encoding="utf-8"))
    expected = expected_events(prepare_home_scene(raw_scene, robot_count=robots, human_count=humans), args.steps)
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
        "experiment_group": canonical_experiment_group(scene_id, args.steps, robots, humans),
        "steps": args.steps,
        "agent_model": args.agent_model,
        "robots": robots,
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
