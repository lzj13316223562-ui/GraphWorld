from __future__ import annotations

import contextlib
import copy
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from torch.utils.tensorboard import SummaryWriter

from backend.runtime.agent.robot_agent_runtime import (
    DECISION_MODE_LLM,
    DECISION_MODE_PLANNER_ONLY,
    run_robot_episode,
)
from backend.runtime.engine.npc_baseline import run_npc_baseline_episode
from backend.tools.analyze_experiments import summarize_replay, write_replay_analysis


ROOT = Path(__file__).resolve().parent
REPLAY_DIR = ROOT / "data" / "replays"
REPLAY_LOG_DIR = ROOT / "data" / "replay_logs"
TENSORBOARD_DIR = ROOT / "data" / "tensorboard"
EXPERIMENT_NO_ROBOT = "no_robot"
EXPERIMENT_PLANNER_ONLY = "planner_only"
EXPERIMENT_FULL_AGENT = "full_agent"
EXPERIMENT_FULL_AGENT_STRONGER = "full_agent_stronger_model"
EXPERIMENT_PURE_HUMAN = "pure_human"
TENSORBOARD_ACTION_ORDER = ("move", "pick", "place", "press", "open", "close", "brush")
TENSORBOARD_ACTION_INDEX = {name: index for index, name in enumerate(TENSORBOARD_ACTION_ORDER)}
EXCLUDED_REPLAY_JSON_NAMES = {"experiment_report.json"}


def _slug(value: str | None) -> str:
    text = str(value or "").strip().lower()
    cleaned = []
    for ch in text:
        if ch.isalnum():
            cleaned.append(ch)
        else:
            cleaned.append("_")
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
    if model == "planner_only":
        return "planner_only"
    compact = model.replace("local-", "").replace(":", "-")
    return _slug(compact)


def canonical_run_name(scene_id: str, experiment_type: str, agent_model: str | None) -> str:
    return "__".join(
        [
            f"scene_{_slug(scene_id)}",
            f"exp_{_slug(experiment_type)}",
            f"model_{canonical_model_label(agent_model)}",
        ]
    )


def _normalize_tensorboard_action(action_type: str | None) -> str:
    value = str(action_type or "").strip().lower()
    return value if value in TENSORBOARD_ACTION_INDEX else "unknown"


def normalize_experiment_type(experiment_type: str | None, agent_model: str | None = None) -> str:
    value = str(experiment_type or "").strip().lower()
    if value in {
        EXPERIMENT_NO_ROBOT,
        EXPERIMENT_PLANNER_ONLY,
        EXPERIMENT_FULL_AGENT,
        EXPERIMENT_FULL_AGENT_STRONGER,
        EXPERIMENT_PURE_HUMAN,
    }:
        return value
    model = str(agent_model or "").strip().lower()
    if model == "npc_only_baseline":
        return EXPERIMENT_NO_ROBOT
    if model == "planner_only":
        return EXPERIMENT_PLANNER_ONLY
    if "35b" in model:
        return EXPERIMENT_FULL_AGENT_STRONGER
    return EXPERIMENT_FULL_AGENT


def experiment_label(experiment_type: str, agent_model: str | None = None) -> str:
    normalized = normalize_experiment_type(experiment_type, agent_model)
    if normalized == EXPERIMENT_NO_ROBOT:
        return "No Robot"
    if normalized == EXPERIMENT_PLANNER_ONLY:
        return "Planner Only"
    if normalized == EXPERIMENT_FULL_AGENT_STRONGER:
        model = str(agent_model or "").strip()
        return f"Full Agent + Stronger Model ({model})" if model else "Full Agent + Stronger Model"
    if normalized == EXPERIMENT_PURE_HUMAN:
        return "Pure Human"
    return "Full Agent"


class _TeeStream:
    def __init__(self, *streams: Any) -> None:
        self._streams = [stream for stream in streams if stream is not None]

    def write(self, data: str) -> int:
        for stream in self._streams:
            stream.write(data)
        if "\n" in data:
            self.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(bool(getattr(stream, "isatty", lambda: False)()) for stream in self._streams)

    @property
    def encoding(self) -> str:
        for stream in self._streams:
            encoding = getattr(stream, "encoding", None)
            if encoding:
                return str(encoding)
        return "utf-8"


class ReplayStore:
    def __init__(self) -> None:
        REPLAY_DIR.mkdir(parents=True, exist_ok=True)
        REPLAY_LOG_DIR.mkdir(parents=True, exist_ok=True)
        TENSORBOARD_DIR.mkdir(parents=True, exist_ok=True)
        self._cache_id: str | None = None
        self._cache_payload: dict[str, Any] | None = None
        self._cache_mtime: float | None = None

    def _path(self, replay_id: str) -> Path:
        return REPLAY_DIR / f"{replay_id}.json"

    def _is_replay_payload_path(self, path: Path) -> bool:
        if path.name in EXCLUDED_REPLAY_JSON_NAMES:
            return False
        if path.name.endswith(".summary.json") or path.name.endswith(".metrics.json") or path.name.endswith(".analysis.json"):
            return False
        return path.suffix == ".json"

    def _summary_path(self, replay_id: str) -> Path:
        return REPLAY_DIR / f"{replay_id}.summary.json"

    def _metrics_path(self, replay_id: str) -> Path:
        return REPLAY_DIR / f"{replay_id}.metrics.json"

    def _analysis_path(self, replay_id: str) -> Path:
        return REPLAY_DIR / f"{replay_id}.analysis.json"

    def _steps_dir(self, replay_id: str) -> Path:
        return REPLAY_DIR / f"{replay_id}.steps"

    def _step_path(self, replay_id: str, step_index: int) -> Path:
        return self._steps_dir(replay_id) / f"{step_index:06d}.json"

    def _steps_ready_path(self, replay_id: str) -> Path:
        return self._steps_dir(replay_id) / ".ready"

    def _log_path(self, replay_id: str) -> Path:
        return REPLAY_LOG_DIR / f"{replay_id}.log"

    def _tensorboard_run_dir(
        self,
        replay_id: str,
        scene_id: str,
        experiment_type: str,
        agent_model: str,
    ) -> Path:
        run_name = canonical_run_name(scene_id, experiment_type, agent_model)
        return TENSORBOARD_DIR / run_name / replay_id

    def _next_replay_id(self) -> str:
        return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]

    def _write_tensorboard_run(
        self,
        *,
        replay_id: str,
        scene_id: str,
        run: dict[str, Any],
        summary: dict[str, Any],
        experiment_type: str,
        agent_model: str,
        task: dict[str, Any] | str | None = None,
    ) -> str:
        run_dir = self._tensorboard_run_dir(replay_id, scene_id, experiment_type, agent_model)
        run_dir.mkdir(parents=True, exist_ok=True)
        writer = SummaryWriter(log_dir=str(run_dir))
        try:
            self._write_tensorboard_metadata(
                writer,
                replay_id=replay_id,
                scene_id=scene_id,
                experiment_type=experiment_type,
                agent_model=agent_model,
                task=task,
            )
            steps = run.get("steps") or []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                self._write_tensorboard_step(writer, step)
            self._write_tensorboard_summary(
                writer,
                summary=summary,
                scene_id=scene_id,
                experiment_type=experiment_type,
                agent_model=agent_model,
            )
        finally:
            writer.flush()
            writer.close()
        return str(run_dir)

    def _persist_live_step(self, replay_id: str, step: dict[str, Any]) -> None:
        step_index = int(step.get("episode_step") or 0)
        steps_dir = self._steps_dir(replay_id)
        steps_dir.mkdir(parents=True, exist_ok=True)
        self._step_path(replay_id, step_index).write_text(
            json.dumps(step, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _metrics_series(self, steps: list[dict[str, Any]], experiment_type: str, agent_model: str | None) -> dict[str, Any]:
        return {
            "experiment_type": experiment_type,
            "experiment_label": experiment_label(experiment_type, agent_model),
            "series": [
                {
                    "step": int(step.get("episode_step") or index),
                    "world_score": float((((step.get("scene_metrics") or {}).get("world_metrics") or {}).get("world_score") or 0.0)),
                    "human_score": float((((step.get("scene_metrics") or {}).get("world_metrics") or {}).get("human_score") or 0.0)),
                    "resident_role_score": float(self._primary_resident_metrics(step.get("scene_metrics") or {}).get("role_score") or 0.0),
                    "resident_mood_score": float(self._primary_resident_metrics(step.get("scene_metrics") or {}).get("mood_score") or 0.0),
                    "day": int((((step.get("scene") or {}).get("world_state") or {}).get("day") or 1)),
                    "clock_minute": int((((step.get("scene") or {}).get("world_state") or {}).get("time_min") or 0)),
                }
                for index, step in enumerate(steps)
            ],
        }

    def _write_replay_outputs(
        self,
        *,
        replay_id: str,
        scene_id: str,
        payload: dict[str, Any],
        run: dict[str, Any],
        normalized_experiment: str,
        agent_model: str,
        run_dir: Path | None = None,
    ) -> None:
        self._path(replay_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        run_name = str((payload.get("summary") or {}).get("run_name") or "")
        summary_payload = {
            "replay_id": replay_id,
            "scene_id": scene_id,
            "created_at": str(payload.get("created_at") or ""),
            "agent_model": str((payload.get("summary") or {}).get("agent_model") or agent_model),
            "experiment_type": str((payload.get("summary") or {}).get("experiment_type") or normalized_experiment),
            "experiment_label": str((payload.get("summary") or {}).get("experiment_label") or experiment_label(normalized_experiment, agent_model)),
            "run_name": run_name,
            "log_path": str((payload.get("summary") or {}).get("log_path") or ""),
            "tensorboard_log_dir": str((payload.get("summary") or {}).get("tensorboard_log_dir") or ""),
            "analysis_path": str(self._analysis_path(replay_id)),
            "max_days": int((payload.get("summary") or {}).get("max_days") or 0),
            "step_count": int((payload.get("summary") or {}).get("step_count") or 0),
            "terminated": bool((payload.get("summary") or {}).get("terminated", False)),
            "termination_reason": str((payload.get("summary") or {}).get("termination_reason") or ""),
            "final_world_score": float((payload.get("summary") or {}).get("final_world_score") or 0.0),
        }
        self._summary_path(replay_id).write_text(
            json.dumps(summary_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        metrics_payload = {
            "replay_id": replay_id,
            "scene_id": scene_id,
            **self._metrics_series(run.get("steps") or [], normalized_experiment, agent_model),
        }
        self._metrics_path(replay_id).write_text(
            json.dumps(metrics_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        ready_path = self._steps_ready_path(replay_id)
        ready_path.parent.mkdir(parents=True, exist_ok=True)
        ready_path.write_text("ready\n", encoding="utf-8")
        analysis_payload = write_replay_analysis(payload, self._analysis_path(replay_id))
        self.write_experiment_report()
        if run_dir is not None:
            writer = SummaryWriter(log_dir=str(run_dir))
            try:
                self._write_tensorboard_action_timeline(
                    writer,
                    run.get("steps") or [],
                    global_step=int((payload.get("summary") or {}).get("step_count") or 0),
                )
            finally:
                writer.flush()
                writer.close()
        payload.setdefault("summary", {})
        payload["summary"]["analysis_path"] = str(self._analysis_path(replay_id))
        self._path(replay_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if analysis_payload:
            self._summary_path(replay_id).write_text(
                json.dumps(
                    {
                        **summary_payload,
                        "analysis_path": str(self._analysis_path(replay_id)),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    def write_experiment_report(self) -> Path:
        report_path = REPLAY_DIR / "experiment_report.json"
        replay_paths = sorted(
            path for path in REPLAY_DIR.glob("*.json")
            if not path.name.endswith(".summary.json")
            and not path.name.endswith(".metrics.json")
            and not path.name.endswith(".analysis.json")
            and path.name != report_path.name
        )
        report = [summarize_replay(json.loads(path.read_text(encoding="utf-8"))) for path in replay_paths]
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report_path

    def _write_tensorboard_metadata(
        self,
        writer: SummaryWriter,
        *,
        replay_id: str,
        scene_id: str,
        experiment_type: str,
        agent_model: str,
        task: dict[str, Any] | str | None = None,
    ) -> None:
        run_name = canonical_run_name(scene_id, experiment_type, agent_model)
        task_text = json.dumps(task, ensure_ascii=False, indent=2) if isinstance(task, dict) else str(task or "")
        metadata_lines = [
            f"run_name: {run_name}",
            f"replay_id: {replay_id}",
            f"scene_id: {scene_id}",
            f"experiment_type: {experiment_type}",
            f"experiment_label: {experiment_label(experiment_type, agent_model)}",
            f"agent_model: {agent_model}",
        ]
        if task_text:
            metadata_lines.append("task:")
            metadata_lines.append(task_text)
        writer.add_text("meta/run", "\n".join(metadata_lines), 0)
        action_map_lines = [f"{index}: {name}" for name, index in TENSORBOARD_ACTION_INDEX.items()]
        writer.add_text("meta/action_index_map", "\n".join(action_map_lines), 0)
        writer.add_text(
            "meta/action_index_legend",
            "0=move\n1=pick\n2=place\n3=press\n4=open\n5=close\n6=brush",
            0,
        )

    def _write_tensorboard_step(
        self,
        writer: SummaryWriter,
        step: dict[str, Any],
    ) -> None:
        global_step = int(step.get("episode_step") or 0)
        scene_metrics = step.get("scene_metrics") or {}
        world_metrics = scene_metrics.get("world_metrics") or {}
        world_state = ((step.get("scene") or {}).get("world_state") or {})
        world_details = scene_metrics.get("world_details") or {}
        issues = scene_metrics.get("issues") or []
        resident_metrics = self._primary_resident_metrics(scene_metrics)
        day_phase = str(world_state.get("day_phase") or "")
        is_daytime = 1.0 if bool(world_state.get("is_daytime", day_phase in {"dawn", "day", "dusk"})) else 0.0

        scalar_pairs = {
            "score/world": float(world_metrics.get("world_score") or 0.0),
            "score/human": float(world_metrics.get("human_score") or 0.0),
            "score/entropy": float(world_metrics.get("entropy_score") or 0.0),
            "score/collapse_pressure": float(world_metrics.get("collapse_pressure") or 0.0),
            "score/resident_role": float(resident_metrics.get("role_score") or 0.0),
            "score/resident_mood": float(resident_metrics.get("mood_score") or 0.0),
            "step/day": float(world_state.get("day") or 1),
            "step/clock_minute": float(world_state.get("time_min") or 0),
            "step/world_step": float(world_state.get("step") or global_step),
            "step/day_night": is_daytime,
            "system/entropy": float(world_details.get("entropy") or 0.0),
            "issues/count": float(len(issues) if isinstance(issues, list) else 0),
        }
        for tag, value in scalar_pairs.items():
            if math.isfinite(value):
                writer.add_scalar(tag, value, global_step)

        action = step.get("action") or {}
        raw_action_type = str(action.get("action_type") or action.get("action") or "none")
        action_type = _normalize_tensorboard_action(raw_action_type)
        if action_type in TENSORBOARD_ACTION_INDEX:
            writer.add_scalar("action/index", float(TENSORBOARD_ACTION_INDEX[action_type]), global_step)
        writer.add_scalar("execution/success", 1.0 if bool(step.get("ok", False)) else 0.0, global_step)

        text_lines = [
            f"action_type: {raw_action_type}",
            f"action_index: {TENSORBOARD_ACTION_INDEX[action_type]}" if action_type in TENSORBOARD_ACTION_INDEX else "action_index: unknown",
            f"target_id: {action.get('target_id') or action.get('target') or ''}",
            f"reason: {action.get('reason') or step.get('reasoning') or ''}",
            f"result_ok: {bool(step.get('ok', False))}",
        ]
        failed_preconds = step.get("failed_preconds") or []
        if failed_preconds:
            text_lines.append("failed_preconds:")
            text_lines.extend(str(item) for item in failed_preconds)
        reasoning = step.get("reasoning")
        if reasoning:
            text_lines.append("reasoning:")
            text_lines.append(json.dumps(reasoning, ensure_ascii=False, indent=2))
        reflection = step.get("reflection")
        if reflection:
            text_lines.append("reflection:")
            text_lines.append(json.dumps(reflection, ensure_ascii=False, indent=2))
        writer.add_text("step/action", "\n".join(text_lines), global_step)
        writer.flush()

    def _write_tensorboard_action_timeline(
        self,
        writer: SummaryWriter,
        steps: list[dict[str, Any]],
        *,
        global_step: int = 0,
    ) -> None:
        if not steps:
            return
        xs: list[int] = []
        ys: list[int] = []
        colors: list[str] = []
        for index, step in enumerate(steps):
            action = step.get("action") or {}
            action_type = str(action.get("action_type") or action.get("action") or "").strip().lower()
            if action_type not in TENSORBOARD_ACTION_INDEX:
                continue
            xs.append(int(step.get("episode_step") or index))
            ys.append(TENSORBOARD_ACTION_INDEX[action_type])
            colors.append("#2f7d32" if bool(step.get("ok", False)) else "#c62828")
        if not xs:
            return
        fig, ax = plt.subplots(figsize=(12, 4.2))
        ax.scatter(xs, ys, c=colors, s=28, alpha=0.9, edgecolors="none")
        ax.set_xlabel("Step")
        ax.set_ylabel("Action")
        ax.set_yticks(range(len(TENSORBOARD_ACTION_ORDER)))
        ax.set_yticklabels(TENSORBOARD_ACTION_ORDER)
        ax.set_ylim(-0.5, len(TENSORBOARD_ACTION_ORDER) - 0.5)
        ax.set_title("Action Timeline")
        ax.grid(axis="x", linestyle="--", alpha=0.22)
        ax.grid(axis="y", linestyle=":", alpha=0.18)
        fig.tight_layout()
        writer.add_figure("action/timeline", fig, global_step=global_step, close=True)
        writer.flush()

    def _write_tensorboard_summary(
        self,
        writer: SummaryWriter,
        *,
        summary: dict[str, Any],
        scene_id: str,
        experiment_type: str,
        agent_model: str,
    ) -> None:
        config_lines = [
            f"run_name: {canonical_run_name(scene_id, experiment_type, agent_model)}",
            f"scene_id: {scene_id}",
            f"experiment_type: {experiment_type}",
            f"agent_model: {agent_model}",
            f"max_days: {float(summary.get('max_days') or 0)}",
            f"step_count: {int(summary.get('step_count') or 0)}",
            f"terminated: {bool(summary.get('terminated', False))}",
            f"final_world_score: {float(summary.get('final_world_score') or 0.0)}",
        ]
        writer.add_text("summary/config", "\n".join(config_lines), 0)
        writer.add_scalar("summary/final_world_score", float(summary.get("final_world_score") or 0.0), 0)
        writer.add_scalar("summary/step_count", float(summary.get("step_count") or 0), 0)
        writer.add_scalar("summary/terminated", 1.0 if bool(summary.get("terminated", False)) else 0.0, 0)
        writer.add_text("summary/termination_reason", str(summary.get("termination_reason") or ""), 0)
        writer.flush()

    @contextlib.contextmanager
    def _capture_run_log(self, replay_id: str, scene_id: str, experiment_type: str, agent_model: str) -> Any:
        log_path = self._log_path(replay_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8", buffering=1) as log_file:
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = _TeeStream(original_stdout, log_file)
            sys.stderr = _TeeStream(original_stderr, log_file)
            try:
                print(
                    f"[ReplayStart] replay_id={replay_id} scene_id={scene_id} "
                    f"experiment_type={experiment_type} agent_model={agent_model}"
                )
                print(f"[ReplayLog] {log_path}")
                yield log_path
                print(f"[ReplayEnd] replay_id={replay_id}")
            except Exception as exc:
                print(f"[ReplayError] replay_id={replay_id} error={exc}")
                raise
            finally:
                sys.stdout.flush()
                sys.stderr.flush()
                sys.stdout = original_stdout
                sys.stderr = original_stderr

    def _load_payload(self, replay_id: str) -> dict[str, Any] | None:
        path = self._path(replay_id)
        if not path.exists():
            return None
        mtime = path.stat().st_mtime
        if self._cache_id == replay_id and self._cache_payload is not None and self._cache_mtime == mtime:
            return self._cache_payload
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        self._cache_id = replay_id
        self._cache_payload = payload
        self._cache_mtime = mtime
        return payload

    def _load_summary(self, replay_id: str) -> dict[str, Any] | None:
        path = self._summary_path(replay_id)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        normalized_experiment = normalize_experiment_type(payload.get("experiment_type"), payload.get("agent_model"))
        payload.setdefault("experiment_type", normalized_experiment)
        payload.setdefault("experiment_label", experiment_label(normalized_experiment, payload.get("agent_model")))
        payload.setdefault(
            "run_name",
            canonical_run_name(
                str(payload.get("scene_id") or ""),
                normalized_experiment,
                str(payload.get("agent_model") or ""),
            ),
        )
        payload.setdefault("log_path", str(self._log_path(str(payload.get("replay_id") or replay_id))))
        payload.setdefault("tensorboard_log_dir", "")
        return payload

    def list_replays(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(REPLAY_DIR.glob("*.json"), reverse=True):
            if not self._is_replay_payload_path(path):
                continue
            replay_id = path.stem
            summary_payload = self._load_summary(replay_id)
            if summary_payload is not None:
                items.append(summary_payload)
                continue
            if path.stat().st_size > 5 * 1024 * 1024:
                items.append(
                    {
                        "replay_id": replay_id,
                        "scene_id": "",
                        "created_at": datetime.utcfromtimestamp(path.stat().st_mtime).isoformat() + "Z",
                        "agent_model": "",
                        "experiment_type": "",
                        "experiment_label": "",
                        "run_name": "",
                        "log_path": str(self._log_path(replay_id)),
                        "tensorboard_log_dir": "",
                        "max_days": 0,
                        "step_count": 0,
                        "terminated": False,
                        "termination_reason": "",
                        "final_world_score": 0.0,
                        "summary_unavailable": True,
                    }
                )
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            summary = payload.get("summary") or {}
            items.append(
                {
                    "replay_id": str(payload.get("replay_id") or path.stem),
                    "scene_id": str(payload.get("scene_id") or ""),
                    "created_at": str(payload.get("created_at") or ""),
                    "agent_model": str(summary.get("agent_model") or ""),
                    "experiment_type": normalize_experiment_type(summary.get("experiment_type"), summary.get("agent_model")),
                    "experiment_label": experiment_label(summary.get("experiment_type"), summary.get("agent_model")),
                    "run_name": str(summary.get("run_name") or canonical_run_name(str(payload.get("scene_id") or ""), summary.get("experiment_type"), summary.get("agent_model"))),
                    "log_path": str(summary.get("log_path") or self._log_path(str(payload.get("replay_id") or path.stem))),
                    "tensorboard_log_dir": str(summary.get("tensorboard_log_dir") or ""),
                    "max_days": int(summary.get("max_days") or 0),
                    "step_count": int(summary.get("step_count") or 0),
                    "terminated": bool(summary.get("terminated", False)),
                    "termination_reason": str(summary.get("termination_reason") or ""),
                    "final_world_score": float(summary.get("final_world_score") or 0.0),
                }
            )
        return items

    def _load_metrics(self, replay_id: str) -> dict[str, Any] | None:
        path = self._metrics_path(replay_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _primary_resident_metrics(self, scene_metrics: dict[str, Any]) -> dict[str, Any]:
        role_metrics = scene_metrics.get("role_metrics") or {}
        if not isinstance(role_metrics, dict):
            return {}
        primary_actor = str((((scene_metrics.get("world_details") or {}).get("human") or {}).get("primary_actor")) or "")
        if primary_actor and isinstance(role_metrics.get(primary_actor), dict):
            return role_metrics.get(primary_actor) or {}
        if isinstance(role_metrics.get("human_resident"), dict):
            return role_metrics.get("human_resident") or {}
        for metrics in role_metrics.values():
            if isinstance(metrics, dict) and metrics.get("is_primary"):
                return metrics
        for actor_id in sorted(role_metrics):
            metrics = role_metrics.get(actor_id)
            if isinstance(metrics, dict):
                return metrics
        return {}

    def get_replay_metrics(self, replay_id: str) -> dict[str, Any] | None:
        metrics = self._load_metrics(replay_id)
        if metrics is not None:
            series = metrics.get("series") or []
            if isinstance(series, list) and all(
                isinstance(point, dict) and ("season_name" in point or "season_name_cn" in point)
                for point in series
            ):
                return metrics
            # Fall through to rebuild older cached metrics that are missing calendar context.
        if metrics is not None:
            metrics = None
        payload = self._load_payload(replay_id)
        if payload is None:
            return metrics
        steps = (((payload.get("run") or {}).get("steps")) or [])
        series = []
        for index, step in enumerate(steps):
            if not isinstance(step, dict):
                continue
            scene_metrics = step.get("scene_metrics") or {}
            world_metrics = scene_metrics.get("world_metrics") or {}
            resident = self._primary_resident_metrics(scene_metrics)
            scene = step.get("scene") or {}
            world_state = scene.get("world_state") or {}
            series.append(
                {
                    "step": int(step.get("episode_step") or index),
                    "world_score": float(world_metrics.get("world_score") or 0.0),
                    "human_score": float(world_metrics.get("human_score") or 0.0),
                    "resident_role_score": float(resident.get("role_score") or 0.0),
                    "resident_mood_score": float(resident.get("mood_score") or 0.0),
                    "day": int(world_state.get("day") or 1),
                    "clock_minute": int(world_state.get("time_min") or 0),
                    "season_name": str(world_state.get("season_name") or ""),
                    "season_name_cn": str(world_state.get("season_name_cn") or ""),
                    "weekday_name": str(world_state.get("weekday_name") or ""),
                    "weekday_name_cn": str(world_state.get("weekday_name_cn") or ""),
                }
            )
        metrics = {
            "replay_id": str(payload.get("replay_id") or replay_id),
            "scene_id": str(payload.get("scene_id") or ""),
            "experiment_type": normalize_experiment_type(
                ((payload.get("summary") or {}).get("experiment_type")),
                ((payload.get("summary") or {}).get("agent_model")),
            ),
            "experiment_label": experiment_label(
                ((payload.get("summary") or {}).get("experiment_type")),
                ((payload.get("summary") or {}).get("agent_model")),
            ),
            "series": series,
        }
        self._metrics_path(replay_id).write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        return metrics

    def _materialize_step(self, replay_id: str, step_index: int) -> bool:
        payload = self._load_payload(replay_id)
        if payload is None:
            return False
        steps = (payload.get("run") or {}).get("steps") or []
        if not isinstance(steps, list):
            return False
        if step_index < 0 or step_index >= len(steps):
            return False
        steps_dir = self._steps_dir(replay_id)
        steps_dir.mkdir(parents=True, exist_ok=True)
        step_path = self._step_path(replay_id, step_index)
        if not step_path.exists():
            step_path.write_text(json.dumps(steps[step_index], ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    def get_replay(self, replay_id: str) -> dict[str, Any] | None:
        return self._load_payload(replay_id)

    def get_replay_summary(self, replay_id: str) -> dict[str, Any] | None:
        summary = self._load_summary(replay_id)
        if summary is not None:
            return {
                "replay_id": str(summary.get("replay_id") or replay_id),
                "scene_id": str(summary.get("scene_id") or ""),
                "created_at": str(summary.get("created_at") or ""),
                "summary": {
                "agent_model": str(summary.get("agent_model") or ""),
                "experiment_type": normalize_experiment_type(summary.get("experiment_type"), summary.get("agent_model")),
                "experiment_label": experiment_label(summary.get("experiment_type"), summary.get("agent_model")),
                "run_name": str(summary.get("run_name") or canonical_run_name(str(summary.get("scene_id") or ""), summary.get("experiment_type"), summary.get("agent_model"))),
                "log_path": str(summary.get("log_path") or self._log_path(replay_id)),
                "tensorboard_log_dir": str(summary.get("tensorboard_log_dir") or ""),
                "max_days": int(summary.get("max_days") or 0),
                "step_count": int(summary.get("step_count") or 0),
                "terminated": bool(summary.get("terminated", False)),
                    "termination_reason": str(summary.get("termination_reason") or ""),
                    "final_world_score": float(summary.get("final_world_score") or 0.0),
                },
            }
        payload = self._load_payload(replay_id)
        if payload is None:
            return None
        summary_block = payload.get("summary") or {}
        return {
            "replay_id": str(payload.get("replay_id") or replay_id),
            "scene_id": str(payload.get("scene_id") or ""),
            "created_at": str(payload.get("created_at") or ""),
            "summary": {
                "agent_model": str(summary_block.get("agent_model") or ""),
                "experiment_type": normalize_experiment_type(summary_block.get("experiment_type"), summary_block.get("agent_model")),
                "experiment_label": experiment_label(summary_block.get("experiment_type"), summary_block.get("agent_model")),
                "run_name": str(summary_block.get("run_name") or canonical_run_name(str(payload.get("scene_id") or ""), summary_block.get("experiment_type"), summary_block.get("agent_model"))),
                "log_path": str(summary_block.get("log_path") or self._log_path(replay_id)),
                "tensorboard_log_dir": str(summary_block.get("tensorboard_log_dir") or ""),
                "max_days": int(summary_block.get("max_days") or 0),
                "step_count": int(summary_block.get("step_count") or 0),
                "terminated": bool(summary_block.get("terminated", False)),
                "termination_reason": str(summary_block.get("termination_reason") or ""),
                "final_world_score": float(summary_block.get("final_world_score") or 0.0),
            },
        }

    def get_replay_step(self, replay_id: str, step_index: int) -> dict[str, Any] | None:
        if step_index < 0:
            return None
        step_path = self._step_path(replay_id, step_index)
        if not step_path.exists() and not self._materialize_step(replay_id, step_index):
            return None
        try:
            step_payload = json.loads(step_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        summary_payload = self.get_replay_summary(replay_id) or {}
        summary = summary_payload.get("summary") or {}
        return {
            "replay_id": str(summary_payload.get("replay_id") or replay_id),
            "scene_id": str(summary_payload.get("scene_id") or ""),
            "summary": summary,
            "step_index": int(step_index),
            "step": step_payload,
            "total_steps": int(summary.get("step_count") or 0),
        }

    def run_and_save_replay(
        self,
        scene_id: str,
        scene: dict[str, Any],
        *,
        task: dict[str, Any] | str | None = None,
        agent_id: str = "robot_01",
        agent_model: str = "local-qwen3.5-35b",
        timeout: int = 30,
        enable_search: bool = False,
        image_path: str | None = None,
        max_days: float = 1.5,
        experiment_type: str | None = None,
    ) -> dict[str, Any]:
        normalized_experiment = normalize_experiment_type(experiment_type, agent_model)
        if normalized_experiment == EXPERIMENT_NO_ROBOT:
            return self.run_and_save_npc_baseline(
                scene_id,
                scene,
                max_days=max_days,
                experiment_type=normalized_experiment,
            )
        decision_mode = DECISION_MODE_PLANNER_ONLY if normalized_experiment == EXPERIMENT_PLANNER_ONLY else DECISION_MODE_LLM
        replay_id = self._next_replay_id()
        log_path = self._log_path(replay_id)
        run_dir = self._tensorboard_run_dir(replay_id, scene_id, normalized_experiment, agent_model)
        run_dir.mkdir(parents=True, exist_ok=True)
        writer = SummaryWriter(log_dir=str(run_dir))
        steps_dir = self._steps_dir(replay_id)
        steps_dir.mkdir(parents=True, exist_ok=True)
        self._write_tensorboard_metadata(
            writer,
            replay_id=replay_id,
            scene_id=scene_id,
            experiment_type=normalized_experiment,
            agent_model=agent_model,
            task=task,
        )
        try:
            with self._capture_run_log(replay_id, scene_id, normalized_experiment, agent_model):
                run = run_robot_episode(
                    scene,
                    task=task,
                    agent_id=agent_id,
                    agent_model=agent_model,
                    timeout=timeout,
                    enable_search=enable_search,
                    image_path=image_path,
                    max_days=max_days,
                    decision_mode=decision_mode,
                    on_step=lambda step: (
                        self._write_tensorboard_step(writer, step),
                        self._persist_live_step(replay_id, step),
                    ),
                )
        finally:
            writer.flush()
            writer.close()
        final_world_score = float((((run.get("final_metrics") or {}).get("world_metrics") or {}).get("world_score") or 0.0))
        run_name = canonical_run_name(scene_id, normalized_experiment, agent_model)
        summary_block = {
            "agent_id": agent_id,
            "agent_model": agent_model,
            "experiment_type": normalized_experiment,
            "experiment_label": experiment_label(normalized_experiment, agent_model),
            "run_name": run_name,
            "log_path": str(log_path),
            "max_days": float(max_days),
            "step_count": len(run.get("steps") or []),
            "terminated": bool(run.get("terminated", False)),
            "termination_reason": str(run.get("termination_reason") or ""),
            "final_world_score": final_world_score,
        }
        writer = SummaryWriter(log_dir=str(run_dir))
        try:
            self._write_tensorboard_summary(
                writer,
                summary=summary_block,
                scene_id=scene_id,
                experiment_type=normalized_experiment,
                agent_model=agent_model,
            )
        finally:
            writer.flush()
            writer.close()
        tensorboard_log_dir = str(run_dir)
        summary_block["tensorboard_log_dir"] = tensorboard_log_dir
        payload = {
            "replay_id": replay_id,
            "scene_id": scene_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "summary": summary_block,
            "run": copy.deepcopy(run),
        }
        self._write_replay_outputs(
            replay_id=replay_id,
            scene_id=scene_id,
            payload=payload,
            run=run,
            normalized_experiment=normalized_experiment,
            agent_model=agent_model,
            run_dir=run_dir,
        )
        return payload

    def run_and_save_npc_baseline(
        self,
        scene_id: str,
        scene: dict[str, Any],
        *,
        max_days: float = 1.5,
        experiment_type: str | None = None,
    ) -> dict[str, Any]:
        normalized_experiment = normalize_experiment_type(experiment_type, "npc_only_baseline")
        replay_id = self._next_replay_id()
        log_path = self._log_path(replay_id)
        run_dir = self._tensorboard_run_dir(replay_id, scene_id, normalized_experiment, "npc_only_baseline")
        run_dir.mkdir(parents=True, exist_ok=True)
        writer = SummaryWriter(log_dir=str(run_dir))
        steps_dir = self._steps_dir(replay_id)
        steps_dir.mkdir(parents=True, exist_ok=True)
        self._write_tensorboard_metadata(
            writer,
            replay_id=replay_id,
            scene_id=scene_id,
            experiment_type=normalized_experiment,
            agent_model="npc_only_baseline",
            task=None,
        )
        try:
            with self._capture_run_log(replay_id, scene_id, normalized_experiment, "npc_only_baseline"):
                run = run_npc_baseline_episode(
                    scene,
                    max_days=max_days,
                    on_step=lambda step: (
                        self._write_tensorboard_step(writer, step),
                        self._persist_live_step(replay_id, step),
                    ),
                )
        finally:
            writer.flush()
            writer.close()
        final_world_score = float((((run.get("final_metrics") or {}).get("world_metrics") or {}).get("world_score") or 0.0))
        run_name = canonical_run_name(scene_id, normalized_experiment, "npc_only_baseline")
        summary_block = {
            "agent_id": "npc_only",
            "agent_model": "npc_only_baseline",
            "experiment_type": normalized_experiment,
            "experiment_label": experiment_label(normalized_experiment, "npc_only_baseline"),
            "run_name": run_name,
            "log_path": str(log_path),
            "max_days": float(max_days),
            "step_count": len(run.get("steps") or []),
            "terminated": bool(run.get("terminated", False)),
            "termination_reason": str(run.get("termination_reason") or ""),
            "final_world_score": final_world_score,
        }
        writer = SummaryWriter(log_dir=str(run_dir))
        try:
            self._write_tensorboard_summary(
                writer,
                summary=summary_block,
                scene_id=scene_id,
                experiment_type=normalized_experiment,
                agent_model="npc_only_baseline",
            )
        finally:
            writer.flush()
            writer.close()
        tensorboard_log_dir = str(run_dir)
        summary_block["tensorboard_log_dir"] = tensorboard_log_dir
        payload = {
            "replay_id": replay_id,
            "scene_id": scene_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "summary": summary_block,
            "run": copy.deepcopy(run),
        }
        self._write_replay_outputs(
            replay_id=replay_id,
            scene_id=scene_id,
            payload=payload,
            run=run,
            normalized_experiment=normalized_experiment,
            agent_model="npc_only_baseline",
            run_dir=run_dir,
        )
        return payload
