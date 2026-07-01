from __future__ import annotations

import contextlib
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCENE_DIR = DATA_DIR / "sg_output" / "simple_graph"
SCENE_PATH = SCENE_DIR / "simple_home_1f.json"
LEGACY_REPLAY_DIR = DATA_DIR / "replay_logs"
TENSORBOARD_DIR = DATA_DIR / "tensorboard"
EXPERIMENT_DIR = DATA_DIR / "experiments"

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
    schedule_mode: str = "fixed",
    schedule_seed: int = 0,
) -> str:
    parts = [
        f"exp_{_slug(experiment_type)}",
        f"steps_{int(steps)}",
        f"robots_{int(robots)}",
        f"humans_{int(humans)}",
        f"model_{canonical_model_label(agent_model)}",
    ]
    if str(schedule_mode or "fixed") != "fixed":
        parts.append(f"schedule_{_slug(schedule_mode)}")
        parts.append(f"seed_{int(schedule_seed)}")
    return "__".join(
        parts
    )


def canonical_experiment_group(
    scene_id: str,
    steps: int,
    robots: int,
    humans: int,
    agent_model: str | None,
    schedule_mode: str = "fixed",
    schedule_seed: int = 0,
) -> str:
    parts = [
        f"steps_{int(steps)}",
        f"robots_{int(robots)}",
        f"humans_{int(humans)}",
        f"model_{canonical_model_label(agent_model)}",
    ]
    if str(schedule_mode or "fixed") != "fixed":
        parts.append(f"schedule_{_slug(schedule_mode)}")
        parts.append(f"seed_{int(schedule_seed)}")
    return "__".join(parts)


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
