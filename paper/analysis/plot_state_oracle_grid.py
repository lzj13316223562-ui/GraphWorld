#!/usr/bin/env python3
"""Plot state-perfect oracle curves for goal-review runs."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / "backend" / "data" / "experiments"
FIG_DIR = ROOT / "paper" / "figures" / "overview"

SCENES = [
    ("simple_home_1f", "Home", 1),
    ("simple_hospital_1f", "Hospital", 3),
    ("simple_supermarket_1f", "Supermarket", 3),
    ("simple_office_1f", "Office", 3),
    ("simple_factory_1f", "Factory", 3),
]

SCHEDULES = [
    ("fixed", "Fixed", "#D62728"),
    ("calendar", "Calendar", "#E0A800"),
    ("stochastic", "Stochastic", "#1F77B4"),
]


def read_summary(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def latest_run(scene: str, humans: int, schedule_mode: str, *, robot: bool) -> Path:
    if robot:
        pattern = "steps_1600__robots_1__humans_*__model_vllm_qwen3_5_9b_goal_review*/**/summary.json"
    else:
        pattern = "steps_1600__robots_0__humans_*__model_npc_only_baseline*/**/summary.json"
    candidates: list[tuple[float, Path]] = []
    for summary_path in (EXP_ROOT / scene).glob(pattern):
        try:
            summary = read_summary(summary_path)
        except Exception:
            continue
        if summary.get("scene") != scene:
            continue
        if int(summary.get("steps", -1)) != 1600:
            continue
        if int(summary.get("robots", -1)) != (1 if robot else 0):
            continue
        if int(summary.get("humans", -1)) != humans:
            continue
        if robot and str(summary.get("agent_mode") or "") != "goal_review":
            continue
        if str(summary.get("schedule_mode") or "fixed") != schedule_mode:
            continue
        split = "with_robot" if robot else "no_robot"
        run_dir = summary_path.parent
        if (run_dir / split / "metrics.csv").exists():
            candidates.append((summary_path.stat().st_mtime, run_dir))
    if not candidates:
        raise FileNotFoundError(f"missing run: scene={scene} schedule={schedule_mode} robot={robot}")
    return max(candidates, key=lambda item: item[0])[1]


def load_rows(run_dir: Path, *, robot: bool) -> list[dict[str, float]]:
    split = "with_robot" if robot else "no_robot"
    path = run_dir / split / "metrics.csv"
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parsed = {
                "step": float(row["step"]),
                "final_score": float(row["final_score"]),
                "state_score": float(row["state_score"]),
                "spatial_score": float(row["spatial_score"]),
                "human_event_score": float(row["human_event_score"]),
            }
            parsed["state_perfect_final"] = 0.45 + 0.35 * parsed["spatial_score"] + 0.20 * parsed["human_event_score"]
            rows.append(parsed)
    return rows


def expanded_ylim(values: list[float]) -> tuple[float, float]:
    values = [value for value in values if not math.isnan(value)]
    if not values:
        return 0.0, 1.0
    lo, hi = min(values), max(values)
    if hi - lo < 0.04:
        mid = (lo + hi) / 2
        lo, hi = mid - 0.04, mid + 0.04
    pad = max((hi - lo) * 0.10, 0.015)
    return max(0.0, lo - pad), min(1.02, hi + pad)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(nrows=3, ncols=5, figsize=(13.0, 6.3), sharex=True, constrained_layout=False)
    handles = []
    labels = []
    for col, (scene, scene_label, humans) in enumerate(SCENES):
        for row_idx, (schedule, schedule_label, color) in enumerate(SCHEDULES):
            ax = axes[row_idx][col]
            baseline = load_rows(latest_run(scene, humans, schedule, robot=False), robot=False)
            agent = load_rows(latest_run(scene, humans, schedule, robot=True), robot=True)
            xs_base = [row["step"] for row in baseline]
            ys_base = [row["final_score"] for row in baseline]
            xs_agent = [row["step"] for row in agent]
            ys_agent = [row["final_score"] for row in agent]
            ys_oracle = [row["state_perfect_final"] for row in agent]
            panel_values = ys_base + ys_agent + ys_oracle
            specs = [
                (xs_base, ys_base, "No robot", ":", "#777777", 1.1, 0.75),
                (xs_agent, ys_agent, "Agent", "-", color, 1.5, 0.95),
                (xs_agent, ys_oracle, "State-perfect oracle", "-.", color, 1.25, 0.65),
            ]
            for xs, ys, label, linestyle, line_color, linewidth, alpha in specs:
                line = ax.plot(xs, ys, color=line_color, linestyle=linestyle, linewidth=linewidth, alpha=alpha, label=label)[0]
                if label not in labels:
                    labels.append(label)
                    handles.append(line)
            ax.set_ylim(*expanded_ylim(panel_values))
            ax.grid(True, color="#E8E8E8", linewidth=0.65)
            ax.tick_params(axis="both", labelsize=7.5)
            if col == 0:
                ax.set_ylabel(schedule_label, fontsize=9)
            if row_idx == 0:
                ax.set_title(scene_label, fontsize=10, pad=3)
            if row_idx == len(SCHEDULES) - 1:
                ax.set_xlabel("Step", fontsize=8)
    fig.suptitle("State-Perfect Oracle Test: Can State Maintenance Separate Scores?", fontsize=13, y=0.992)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=3, frameon=False, fontsize=9)
    fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.90), h_pad=0.55, w_pad=0.45)
    out = FIG_DIR / "state_perfect_oracle_grid.png"
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
