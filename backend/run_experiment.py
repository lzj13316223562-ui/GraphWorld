from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.core.assets.npc_library import get_default_npcs
from backend.experiments.io import (
    append_csv_row,
    append_jsonl,
    convert_jsonl_to_json_array,
    load_json,
    write_csv_rows,
    write_json_atomic,
    write_jsonl_rows,
)
from backend.experiments.paths import (
    EXPERIMENT_DIR,
    SCENE_DIR,
    TENSORBOARD_DIR,
    _slug,
    canonical_experiment_group,
    canonical_run_group,
    clean_old_outputs,
    utc_run_id,
)
from backend.experiments.tensorboard import TensorBoardWriter
from backend.runtime.agent import (
    candidate_actions,
    fallback_choose_action,
    held_object,
    llm_choose_action,
    llm_choose_reactive_action,
    llm_review_goal,
    perceive,
    reflect,
    remember,
)
from backend.runtime.agent.goal_lifecycle import (
    active_goal_claims,
    candidate_goal_options,
    goal_conflicts_with_claims,
    refresh_active_goal_snapshot,
    update_active_goal,
)
from backend.runtime.agent.maintenance_goals import (
    global_restore_goal,
    visible_dispose_food_goal,
    visible_empty_cup_goal,
    visible_laundry_goal,
    visible_restore_goal,
)
from backend.runtime.agent.rule_baselines import RULE_AGENT_MODES, choose_rule_action
from backend.runtime.blocking import finalize_blocking_case_outcomes, update_blocking_cases
from backend.runtime.engine import Orchestrator
from backend.runtime.eval import build_matrix_snapshot, matrix_score
from backend.runtime.scene_utils import node, room_of, scene_type
from backend.runtime.schedule import expected_events, planned_event_for_step, planned_events_for_step
from backend.tools.agent import resolved_agent_config

SCORE_KEYS = ("final_score", "state_score", "spatial_score", "human_event_score")
INSTANT_SCORE_KEYS = ("instant_final_score", "instant_state_score", "instant_spatial_score")
AVG_SCORE_KEYS = ("avg_final_score", "avg_state_score", "avg_spatial_score")
LLM_AGENT_MODES = ("reactive", "single_round", "goal_review")
AGENT_MODES = (*LLM_AGENT_MODES, *RULE_AGENT_MODES)
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



def actor_specs_for_scene(scene: dict[str, Any], human_count: int) -> list[dict[str, str]]:
    if scene_type(scene) == "hospital":
        defaults = get_default_npcs("hospital")
        return defaults[: max(0, int(human_count))]
    if scene_type(scene) == "supermarket":
        defaults = get_default_npcs("supermarket")
        return defaults[: max(0, int(human_count))]
    if scene_type(scene) == "office":
        defaults = get_default_npcs("office")
        return defaults[: max(0, int(human_count))]
    if scene_type(scene) == "factory":
        defaults = get_default_npcs("factory")
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
    if scene_type(scene) in {"home", "supermarket", "office", "factory"}:
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
                    "current_activity": spec.get("activity", ""),
                    "states": {},
                    "parent": parent_id,
                    "child": [],
                    "interactive_actions": [],
                },
            )
            ensure_edge(scene, parent_id, human_id, "at")
    for robot_id in robot_ids(robot_count):
        if scene_type(scene) == "hospital":
            robot_parent = "lobby"
        elif scene_type(scene) == "supermarket":
            robot_parent = "entrance"
        elif scene_type(scene) in {"office", "factory"}:
            robot_parent = "entrance"
        else:
            robot_parent = "living_room"
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


def checkpoint_payload(
    *,
    scene_id: str,
    run_id: str,
    experiment_name: str,
    step: int,
    steps: int,
    robot_count: int,
    human_count: int,
    agent_model: str,
    agent_mode: str,
    use_llm: bool,
    schedule_mode: str,
    schedule_seed: int,
    current_scene: dict[str, Any],
    baseline_scene: dict[str, Any],
    memories: dict[str, dict[str, Any] | None],
    active_goals: dict[str, dict[str, Any] | None],
    recent_histories: dict[str, list[dict[str, Any]]],
    recent_score_records: list[dict[str, Any]],
    last_record: dict[str, Any],
    cumulative_state_score: float,
    cumulative_spatial_score: float,
    blocking_cases: list[dict[str, Any]],
    human_blocking_total: int,
    human_blocking_recovered: int,
    matrix_paths: list[str],
    metrics_csv: Path,
    replay_jsonl: Path,
) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "scene_id": scene_id,
        "run_id": run_id,
        "experiment": experiment_name,
        "next_step": int(step) + 1,
        "requested_steps": int(steps),
        "robot_count": int(robot_count),
        "human_count": int(human_count),
        "agent_model": agent_model,
        "agent_mode": agent_mode,
        "use_llm": bool(use_llm),
        "schedule_mode": schedule_mode,
        "schedule_seed": int(schedule_seed),
        "current_scene": current_scene,
        "baseline_scene": baseline_scene,
        "memories": memories,
        "active_goals": active_goals,
        "recent_histories": recent_histories,
        "recent_score_records": recent_score_records,
        "last_record": last_record,
        "cumulative_state_score": cumulative_state_score,
        "cumulative_spatial_score": cumulative_spatial_score,
        "blocking_cases": blocking_cases,
        "human_blocking_total": int(human_blocking_total),
        "human_blocking_recovered": int(human_blocking_recovered),
        "matrix_paths": matrix_paths,
        "metrics_csv": str(metrics_csv),
        "replay_jsonl": str(replay_jsonl),
        "updated_at": time.time(),
    }


def find_resume_candidates() -> list[Path]:
    candidates: list[Path] = []
    if not EXPERIMENT_DIR.exists():
        return candidates
    for checkpoint in EXPERIMENT_DIR.glob("*/*/*/*/checkpoint.json"):
        run_dir = checkpoint.parent.parent
        if (run_dir / "summary.json").exists():
            continue
        candidates.append(run_dir)
    return sorted(set(candidates), key=lambda path: path.stat().st_mtime, reverse=True)


def resolve_resume_run(value: str) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise RuntimeError("--resume-run requires a run directory or run_id")
    path = Path(raw).expanduser()
    if path.exists():
        path = path.resolve()
        if (path / "summary.json").exists():
            raise RuntimeError(f"run is already complete: {path}")
        if list(path.glob("*/checkpoint.json")):
            return path
        raise RuntimeError(f"no checkpoint.json found under run directory: {path}")
    matches = [candidate for candidate in find_resume_candidates() if candidate.name == raw]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RuntimeError(f"no resumable run found for: {raw}")
    raise RuntimeError(f"ambiguous run_id {raw}: " + ", ".join(str(path) for path in matches))


def print_resume_candidates() -> None:
    candidates = find_resume_candidates()
    if not candidates:
        print("No resumable runs found.")
        return
    print("Resumable runs:")
    for index, run_dir in enumerate(candidates, start=1):
        checkpoints = []
        for checkpoint in sorted(run_dir.glob("*/checkpoint.json")):
            payload = load_json(checkpoint)
            checkpoints.append(
                f"{checkpoint.parent.name}: next_step={payload.get('next_step')}/{payload.get('requested_steps')}"
            )
        print(f"{index}. {run_dir}")
        print(f"   run_id={run_dir.name}")
        print(f"   checkpoints={'; '.join(checkpoints)}")
    print("\nUse --resume --resume-run <run_id-or-run_dir> to continue one of them.")


def load_run_checkpoints(run_dir: Path) -> dict[str, dict[str, Any]]:
    checkpoints: dict[str, dict[str, Any]] = {}
    for checkpoint in sorted(run_dir.glob("*/checkpoint.json")):
        checkpoints[checkpoint.parent.name] = load_json(checkpoint)
    if not checkpoints:
        raise RuntimeError(f"no checkpoint.json found under run directory: {run_dir}")
    return checkpoints


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
    agent_mode: str,
    expected: tuple[str, ...],
    output_dir: Path,
    matrix_viz: bool,
    replay_scene_interval: int = 1,
    metric_log_interval: int = 1,
    schedule_mode: str = "fixed",
    schedule_seed: int = 0,
    resume: bool = False,
) -> dict[str, Any]:
    scene = prepare_scene(raw_scene, robot_count=robot_count, human_count=human_count)
    scene.setdefault("world_state", {})["schedule_mode"] = schedule_mode
    scene.setdefault("world_state", {})["schedule_seed"] = int(schedule_seed)
    baseline = copy.deepcopy(scene)
    room_index_map = build_room_index(scene)
    orchestrator = Orchestrator(scene)
    memories: dict[str, dict[str, Any] | None] = {robot_id: None for robot_id in robot_ids(robot_count)}
    active_goals: dict[str, dict[str, Any] | None] = {robot_id: None for robot_id in robot_ids(robot_count)}
    recent_histories: dict[str, list[dict[str, Any]]] = {robot_id: [] for robot_id in robot_ids(robot_count)}
    recent_score_records: list[dict[str, Any]] = []
    last_record: dict[str, Any] = {}
    cumulative_state_score = 0.0
    cumulative_spatial_score = 0.0
    blocking_cases: list[dict[str, Any]] = []
    human_blocking_total = 0
    human_blocking_recovered = 0
    experiment_name = "with_robot" if robot_count else "no_robot"
    experiment_output_dir = output_dir / experiment_name
    experiment_output_dir.mkdir(parents=True, exist_ok=True)
    matrix_output_dir = experiment_output_dir / "matrices"
    planning_label = agent_mode
    model_name = (
        f"{agent_model}__{planning_label}"
        if robot_count and use_llm
        else (f"rule__{planning_label}" if robot_count and agent_mode in RULE_AGENT_MODES else ("heuristic" if robot_count else "npc_only_baseline"))
    )
    tb_dir = TENSORBOARD_DIR / _slug(scene_id) / canonical_run_group(
        scene_id,
        experiment_name,
        model_name,
        steps,
        robot_count,
        human_count,
        schedule_mode,
        schedule_seed,
    ) / run_id
    tb_dir.mkdir(parents=True, exist_ok=True)
    writer = TensorBoardWriter(tb_dir)
    replay_path = experiment_output_dir / "replay.json"
    replay_jsonl_path = experiment_output_dir / "replay.jsonl"
    csv_path = experiment_output_dir / "metrics.csv"
    checkpoint_path = experiment_output_dir / "checkpoint.json"
    model_ok = bool(robot_count and use_llm)
    model_status = require_llm_agent(agent_model) if model_ok else "not_used"
    previous_snapshot = build_matrix_snapshot(orchestrator.graph.to_scene(), expected)
    baseline_snapshot = build_matrix_snapshot(baseline, expected)
    matrix_paths: list[str] = []
    replay_scene_interval = max(0, int(replay_scene_interval))
    metric_log_interval = max(1, int(metric_log_interval))
    start_step = 0
    if resume and checkpoint_path.exists():
        checkpoint = load_json(checkpoint_path)
        checkpoint_experiment = str(checkpoint.get("experiment") or "")
        if checkpoint_experiment != experiment_name:
            raise RuntimeError(f"checkpoint experiment mismatch: {checkpoint_experiment} != {experiment_name}")
        start_step = int(checkpoint.get("next_step") or 0)
        if start_step > int(steps):
            raise RuntimeError(f"checkpoint next_step={start_step} exceeds requested steps={steps}")
        baseline = copy.deepcopy(checkpoint.get("baseline_scene") or baseline)
        scene = copy.deepcopy(checkpoint.get("current_scene") or scene)
        orchestrator = Orchestrator(scene)
        room_index_map = build_room_index(baseline)
        memories = copy.deepcopy(checkpoint.get("memories") or memories)
        active_goals = copy.deepcopy(checkpoint.get("active_goals") or active_goals)
        recent_histories = copy.deepcopy(checkpoint.get("recent_histories") or recent_histories)
        legacy_records = copy.deepcopy(checkpoint.get("records") or [])
        legacy_replay_steps = copy.deepcopy(checkpoint.get("replay_steps") or [])
        if legacy_records and not csv_path.exists():
            write_csv_rows(csv_path, legacy_records)
        if legacy_replay_steps and not replay_jsonl_path.exists():
            write_jsonl_rows(replay_jsonl_path, legacy_replay_steps)
        recent_score_records = copy.deepcopy(checkpoint.get("recent_score_records") or legacy_records[-10:])
        last_record = copy.deepcopy(checkpoint.get("last_record") or (legacy_records[-1] if legacy_records else {}))
        cumulative_state_score = float(checkpoint.get("cumulative_state_score") or 0.0)
        cumulative_spatial_score = float(checkpoint.get("cumulative_spatial_score") or 0.0)
        blocking_cases = copy.deepcopy(checkpoint.get("blocking_cases") or blocking_cases)
        human_blocking_total = int(
            checkpoint.get(
                "human_blocking_total",
                (last_record or {}).get("human_blocking_total", human_blocking_total),
            )
            or 0
        )
        human_blocking_recovered = int(
            checkpoint.get(
                "human_blocking_recovered",
                (last_record or {}).get("human_blocking_recovered", human_blocking_recovered),
            )
            or 0
        )
        matrix_paths = list(checkpoint.get("matrix_paths") or [])
        previous_snapshot = build_matrix_snapshot(orchestrator.graph.to_scene(), expected)
        baseline_snapshot = build_matrix_snapshot(baseline, expected)
        tqdm.write(f"{experiment_name}: resuming {run_id} from step {start_step}/{steps}")
    elif resume:
        tqdm.write(f"{experiment_name}: no checkpoint found, starting from step 0")
    for step in tqdm(range(start_step, steps), desc=experiment_name, unit="step", dynamic_ncols=True):
        schedule_scene = orchestrator.graph.to_scene()
        event_id = planned_event_for_step(schedule_scene, step)
        human_events = planned_events_for_step(schedule_scene, step)
        actions: list[dict[str, Any]] = []
        candidates_by_robot: dict[str, list[dict[str, Any]]] = {}
        llm_answers: dict[str, str] = {}
        goal_review_answers: dict[str, str] = {}
        observations: dict[str, dict[str, Any]] = {}
        claimed_goal_nodes: set[str] = set()
        for robot_id in robot_ids(robot_count):
            claimed_goal_nodes.update(
                claim
                for other_robot_id, goal in active_goals.items()
                if other_robot_id != robot_id
                for claim in active_goal_claims(goal)
            )
            if agent_mode != "reactive" and active_goals.get(robot_id) is None:
                proposed_goal = global_restore_goal(orchestrator.graph.to_scene(), baseline, robot_id, step)
                if proposed_goal and not goal_conflicts_with_claims(proposed_goal, claimed_goal_nodes):
                    active_goals[robot_id] = refresh_active_goal_snapshot(proposed_goal, orchestrator.graph.to_scene(), robot_id)
            observation = perceive(orchestrator, robot_id)
            observations[robot_id] = observation
            memories[robot_id] = remember(memories.get(robot_id), observation)
            if agent_mode != "reactive" and active_goals.get(robot_id) is None:
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
            if use_llm and agent_mode == "goal_review":
                goal_options = candidate_goal_options(
                    orchestrator.graph.to_scene(),
                    baseline,
                    observation,
                    robot_id,
                    step,
                    claimed_goal_nodes,
                )
                high_level_options = ["maintain_order"]
                active_task = str((active_goals.get(robot_id) or {}).get("task") or "")
                if active_task:
                    high_level_options.append(active_task)
                high_level_options.extend(task for task in goal_options if task not in high_level_options)
                review, review_answer = llm_review_goal(
                    observation,
                    agent_model,
                    initial_scene=baseline,
                    active_goal=active_goals.get(robot_id),
                    high_level_options=high_level_options,
                    recent_history=recent_histories.get(robot_id, []),
                    agent_id=robot_id,
                )
                goal_review_answers[robot_id] = review_answer
                decision = str(review.get("decision") or "")
                reviewed_task = str(review.get("high_level_task") or "")
                if decision in {"finish", "drop"} or reviewed_task == "maintain_order":
                    active_goals[robot_id] = None
                elif decision == "switch":
                    active_goals[robot_id] = goal_options.get(reviewed_task)
                elif active_goals.get(robot_id):
                    active_goals[robot_id] = refresh_active_goal_snapshot(
                        active_goals[robot_id],
                        orchestrator.graph.to_scene(),
                        robot_id,
                    )
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
                if agent_mode == "reactive":
                    recent_scores = [
                        {
                            "step": int(record.get("step") or 0),
                            "final_score": record.get("final_score"),
                            "state_score": record.get("state_score"),
                            "spatial_score": record.get("spatial_score"),
                            "human_event_score": record.get("human_event_score"),
                        }
                        for record in recent_score_records[-10:]
                    ]
                    action, llm_answer = llm_choose_reactive_action(
                        candidates,
                        observation,
                        agent_model,
                        recent_scores=recent_scores,
                        agent_id=robot_id,
                    )
                else:
                    action, llm_answer = llm_choose_action(
                        candidates,
                        observation,
                        agent_model,
                        baseline,
                        active_goal=active_goals.get(robot_id),
                        agent_id=robot_id,
                    )
                llm_answers[robot_id] = llm_answer
            elif agent_mode in RULE_AGENT_MODES:
                action = choose_rule_action(
                    agent_mode=agent_mode,
                    candidates=candidates,
                    observation=observation,
                    scene=orchestrator.graph.to_scene(),
                    baseline=baseline,
                    active_goal=active_goals.get(robot_id),
                    blocking_cases=blocking_cases,
                    robot_id=robot_id,
                )
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
        new_blocking_cases: list[dict[str, Any]] = []
        for event_result in result.get("human_events") or []:
            for case in event_result.get("blocking_cases") or []:
                new_blocking_cases.append(copy.deepcopy(case))
        if new_blocking_cases:
            blocking_cases.extend(new_blocking_cases)
            human_blocking_total += sum(1 for case in new_blocking_cases if bool(case.get("recoverable", False)))
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
        instant_metrics = matrix_score(current_snapshot, baseline_snapshot, previous_snapshot, robot_snapshot)
        instant_metrics.pop("robot_score", None)
        instant_state_score = float(instant_metrics["state_score"])
        instant_spatial_score = float(instant_metrics["spatial_score"])
        human_event_score = float(instant_metrics["human_event_score"])
        instant_final_score = round(
            instant_state_score * 0.45 + instant_spatial_score * 0.35 + human_event_score * 0.20,
            4,
        )
        cumulative_state_score += instant_state_score
        cumulative_spatial_score += instant_spatial_score
        avg_state_score = round(cumulative_state_score / (step + 1), 4)
        avg_spatial_score = round(cumulative_spatial_score / (step + 1), 4)
        avg_final_score = round(
            avg_state_score * 0.45
            + avg_spatial_score * 0.35
            + human_event_score * 0.20,
            4,
        )
        metrics = {
            "final_score": avg_final_score,
            "state_score": avg_state_score,
            "spatial_score": avg_spatial_score,
            "human_event_score": round(human_event_score, 4),
            "instant_final_score": instant_final_score,
            "instant_state_score": round(instant_state_score, 4),
            "instant_spatial_score": round(instant_spatial_score, 4),
            "avg_final_score": avg_final_score,
            "avg_state_score": avg_state_score,
            "avg_spatial_score": avg_spatial_score,
            "robot_state_improvements": instant_metrics.get("robot_state_improvements", 0),
            "robot_spatial_improvements": instant_metrics.get("robot_spatial_improvements", 0),
            "human_blocking_total": human_blocking_total,
            "human_blocking_recovered": human_blocking_recovered,
            "human_blocking_recovery_rate": round(
                human_blocking_recovered / human_blocking_total, 4
            )
            if human_blocking_total
            else 0.0,
        }
        previous_snapshot = current_snapshot
        primary_action = actions[0] if actions else {}
        action_name = str(primary_action.get("action") or "")
        before_resolved = sum(1 for case in blocking_cases if str(case.get("status") or "") in {"resolved", "closed_success"})
        update_blocking_cases(blocking_cases, current, actions, step)
        finalize_blocking_case_outcomes(blocking_cases, result.get("human_events") or [])
        after_resolved = sum(1 for case in blocking_cases if str(case.get("status") or "") in {"resolved", "closed_success"})
        human_blocking_recovered += max(0, after_resolved - before_resolved)
        metrics["human_blocking_total"] = human_blocking_total
        metrics["human_blocking_recovered"] = human_blocking_recovered
        metrics["human_blocking_recovery_rate"] = (
            round(human_blocking_recovered / human_blocking_total, 4) if human_blocking_total else 0.0
        )
        for robot_id in robot_ids(robot_count):
            action_for_robot = actions_by_robot.get(robot_id, {})
            history = recent_histories.setdefault(robot_id, [])
            history.append(
                {
                    "step": step,
                    "room": room_of(current, robot_id),
                    "holding": held_object(orchestrator, robot_id),
                    "active_goal": str((active_goals.get(robot_id) or {}).get("task") or ""),
                    "action": action_for_robot.get("action", ""),
                    "target": action_for_robot.get("target", ""),
                    "object": action_for_robot.get("object", ""),
                    "final_score": float(metrics["final_score"]),
                    "state_score": float(metrics["state_score"]),
                    "spatial_score": float(metrics["spatial_score"]),
                    "human_event_score": float(metrics["human_event_score"]),
                }
            )
            del history[:-10]
        if step % metric_log_interval == 0 or step + 1 == steps:
            for key in SCORE_KEYS:
                writer.add_scalar(f"scores/{key}", float(metrics[key]), step)
            for key in INSTANT_SCORE_KEYS:
                writer.add_scalar(f"scores/{key}", float(metrics[key]), step)
            for key in AVG_SCORE_KEYS:
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
            "goal_review": json.dumps(goal_review_answers, ensure_ascii=False),
            "active_goal": json.dumps(active_goals, ensure_ascii=False),
            **metrics,
        }
        append_csv_row(csv_path, row)
        recent_score_records.append(row)
        del recent_score_records[:-10]
        last_record = row
        primary_robot = robot_ids(robot_count)[0] if robot_count else ""
        robot_room = room_of(current, primary_robot) if primary_robot else ""
        if primary_robot and robot_room:
            writer.add_scalar("trajectory/room_index", room_index_map.get(robot_room, -1), step)
        include_scene = replay_scene_interval > 0 and (step % replay_scene_interval == 0 or step + 1 == steps)
        replay_row = {
            "episode_step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reasoning": json.dumps(llm_answers, ensure_ascii=False) if robot_count else "npc_only_baseline",
            "goal_review": json.dumps(goal_review_answers, ensure_ascii=False) if robot_count else "",
            "planner": {
                "mode": "llm" if robot_count and use_llm and model_ok else ("rule" if robot_count and agent_mode in RULE_AGENT_MODES else ("heuristic" if robot_count else "npc_only_baseline")),
                "event": event_id,
            },
            "action": copy.deepcopy(primary_action),
            "robot_actions": copy.deepcopy(actions),
            "ok": all(bool(action.get("legal", True)) for action in actions) if actions else True,
            "failed_preconds": {
                str(action.get("agent") or ""): copy.deepcopy(action.get("validation_failures") or [])
                for action in actions
            },
            "blocking_cases": copy.deepcopy(blocking_cases),
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
        append_jsonl(replay_jsonl_path, replay_row)
        write_json_atomic(
            checkpoint_path,
            checkpoint_payload(
                scene_id=scene_id,
                run_id=run_id,
                experiment_name=experiment_name,
                step=step,
                steps=steps,
                robot_count=robot_count,
                human_count=human_count,
                agent_model=agent_model,
                agent_mode=agent_mode,
                use_llm=use_llm,
                schedule_mode=schedule_mode,
                schedule_seed=schedule_seed,
                current_scene=current,
                baseline_scene=baseline,
                memories=memories,
                active_goals=active_goals,
                recent_histories=recent_histories,
                recent_score_records=recent_score_records,
                last_record=last_record,
                cumulative_state_score=cumulative_state_score,
                cumulative_spatial_score=cumulative_spatial_score,
                blocking_cases=blocking_cases,
                human_blocking_total=human_blocking_total,
                human_blocking_recovered=human_blocking_recovered,
                matrix_paths=matrix_paths,
                metrics_csv=csv_path,
                replay_jsonl=replay_jsonl_path,
            ),
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
    replay_count = convert_jsonl_to_json_array(replay_jsonl_path, replay_path, desc=f"{experiment_name} replay")
    return {
        "experiment": experiment_name,
        "records": [last_record] if last_record else [],
        "tensorboard_log_dir": str(tb_dir),
        "replay_path": str(replay_path),
        "metrics_csv": str(csv_path),
        "matrix_dir": str(matrix_output_dir) if matrix_viz else "",
        "matrix_count": len(matrix_paths),
        "replay_count": replay_count,
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
    parser.add_argument("--goal-review", choices=("on", "off"), default="on")
    parser.add_argument("--agent-mode", choices=AGENT_MODES, default="")
    parser.add_argument("--only", choices=("both", "no_robot", "with_robot"), default="both")
    parser.add_argument("--matrix-viz", action="store_true")
    parser.add_argument("--replay-scene-interval", type=int, default=1)
    parser.add_argument("--metric-log-interval", type=int, default=1)
    parser.add_argument("--schedule-mode", choices=("fixed", "calendar", "stochastic"), default="fixed")
    parser.add_argument("--schedule-seed", type=int, default=0)
    parser.add_argument("--resume", action="store_true", help="List resumable interrupted runs, or resume --resume-run.")
    parser.add_argument("--resume-run", default="", help="Run id or run directory to continue when --resume is set.")
    args = parser.parse_args()
    if args.resume and not str(args.resume_run or "").strip():
        print_resume_candidates()
        return
    agent_mode = str(args.agent_mode or "").strip() or ("goal_review" if args.goal_review == "on" else "single_round")
    agent_model = str(args.agent_model)
    requested_use_llm = not args.no_llm and agent_mode not in RULE_AGENT_MODES
    scene_id = str(args.scene or "simple_home_1f").removesuffix(".json")
    steps = int(args.steps)
    robots = max(0, int(args.robots))
    humans = max(0, int(args.humans))
    schedule_mode = str(args.schedule_mode or "fixed")
    schedule_seed = int(args.schedule_seed)
    group_robots = 0 if args.only == "no_robot" else robots
    resume_checkpoints: dict[str, dict[str, Any]] = {}
    if args.resume:
        output_dir = resolve_resume_run(str(args.resume_run))
        resume_checkpoints = load_run_checkpoints(output_dir)
        first_checkpoint = next(iter(resume_checkpoints.values()))
        run_id = output_dir.name
        experiment_group = output_dir.parent.name
        scene_id = str(first_checkpoint.get("scene_id") or scene_id)
        steps = int(first_checkpoint.get("requested_steps") or steps)
        robots = int(first_checkpoint.get("robot_count") or robots)
        humans = int(first_checkpoint.get("human_count") or humans)
        agent_model = str(first_checkpoint.get("agent_model") or agent_model)
        agent_mode = str(first_checkpoint.get("agent_mode") or agent_mode)
        schedule_mode = str(first_checkpoint.get("schedule_mode") or schedule_mode)
        schedule_seed = int(first_checkpoint.get("schedule_seed") or schedule_seed)
        if "with_robot" in resume_checkpoints:
            robots = int(resume_checkpoints["with_robot"].get("robot_count") or robots)
            group_robots = robots
        else:
            group_robots = 0
    else:
        if not args.no_clean:
            clean_old_outputs()
        experiment_model = (
            "npc_only_baseline"
            if group_robots == 0
            else (f"rule__{agent_mode}" if agent_mode in RULE_AGENT_MODES else ("heuristic" if args.no_llm else f"{agent_model}__{agent_mode}"))
        )
        experiment_group = canonical_experiment_group(
            scene_id,
            steps,
            group_robots,
            humans,
            experiment_model,
            schedule_mode,
            schedule_seed,
        )
        run_id = utc_run_id()
        output_dir = EXPERIMENT_DIR / _slug(scene_id) / experiment_group / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_path = SCENE_DIR / f"{scene_id}.json"
    raw_scene = json.loads(scene_path.read_text(encoding="utf-8"))
    expected_scene = prepare_scene(raw_scene, robot_count=robots, human_count=humans)
    expected_scene.setdefault("world_state", {})["schedule_mode"] = schedule_mode
    expected_scene.setdefault("world_state", {})["schedule_seed"] = int(schedule_seed)
    expected = expected_events(expected_scene, steps)
    results = []
    should_run_no_robot = args.only in {"both", "no_robot"}
    should_run_with_robot = args.only in {"both", "with_robot"}
    if args.resume:
        checkpoint_experiments = set(resume_checkpoints)
        if args.only == "both":
            should_run_no_robot = "no_robot" in checkpoint_experiments
            should_run_with_robot = "with_robot" in checkpoint_experiments
        else:
            requested_experiment = "no_robot" if args.only == "no_robot" else "with_robot"
            if requested_experiment not in checkpoint_experiments:
                raise RuntimeError(
                    f"requested --only {args.only}, but checkpoint has {sorted(checkpoint_experiments)}"
                )
    if should_run_no_robot:
        results.append(
            run_episode(
                raw_scene,
                scene_id=scene_id,
                steps=steps,
                robot_count=0,
                human_count=humans,
                run_id=run_id,
                agent_model=agent_model,
                use_llm=False,
                agent_mode="no_robot",
                expected=expected,
                output_dir=output_dir,
                matrix_viz=args.matrix_viz,
                replay_scene_interval=args.replay_scene_interval,
                metric_log_interval=args.metric_log_interval,
                schedule_mode=schedule_mode,
                schedule_seed=schedule_seed,
                resume=args.resume,
            )
        )
    if should_run_with_robot:
        results.append(
            run_episode(
                raw_scene,
                scene_id=scene_id,
                steps=steps,
                robot_count=robots,
                human_count=humans,
                run_id=run_id,
                agent_model=agent_model,
                use_llm=bool(resume_checkpoints.get("with_robot", {}).get("use_llm", requested_use_llm)) if args.resume else requested_use_llm,
                agent_mode=agent_mode,
                expected=expected,
                output_dir=output_dir,
                matrix_viz=args.matrix_viz,
                replay_scene_interval=args.replay_scene_interval,
                metric_log_interval=args.metric_log_interval,
                schedule_mode=schedule_mode,
                schedule_seed=schedule_seed,
                resume=args.resume,
            )
        )
    summary = {
        "run_id": run_id,
        "scene": scene_id,
        "experiment_group": experiment_group,
        "steps": steps,
        "agent_model": agent_model,
        "agent_mode": agent_mode,
        "goal_review": args.goal_review,
        "schedule_mode": schedule_mode,
        "schedule_seed": schedule_seed,
        "robots": group_robots,
        "humans": humans,
        "expected_events": expected,
        "created_at": time.time(),
        "runs": [
            {key: value for key, value in result.items() if key != "records"}
            | {
                "final_metrics": {score_key: result["records"][-1][score_key] for score_key in SCORE_KEYS},
                "final_instant_metrics": {
                    score_key: result["records"][-1][score_key]
                    for score_key in INSTANT_SCORE_KEYS
                    if score_key in result["records"][-1]
                },
                "final_avg_metrics": {
                    score_key: result["records"][-1][score_key]
                    for score_key in AVG_SCORE_KEYS
                    if score_key in result["records"][-1]
                },
                "final_blocking_metrics": {
                    "human_blocking_total": result["records"][-1].get("human_blocking_total", 0),
                    "human_blocking_recovered": result["records"][-1].get("human_blocking_recovered", 0),
                    "human_blocking_recovery_rate": result["records"][-1].get("human_blocking_recovery_rate", 0.0),
                },
            }
            for result in results
        ],
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
