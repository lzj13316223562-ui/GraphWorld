#!/usr/bin/env python3
"""Plot schedule perturbation grid: goal-review agent vs matching no-robot baselines."""

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

AVG_METRICS = [
    ("final_score", "Final"),
    ("state_score", "State"),
    ("spatial_score", "Spatial"),
    ("human_event_score", "Human"),
]

INSTANT_METRICS = [
    ("instant_final_score", "Final"),
    ("instant_state_score", "State"),
    ("instant_spatial_score", "Spatial"),
    ("human_event_score", "Human"),
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
        expected_robots = 1 if robot else 0
        if int(summary.get("robots", -1)) != expected_robots or int(summary.get("humans", -1)) != humans:
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
        kind = "goal_review" if robot else "no_robot"
        raise FileNotFoundError(f"missing {kind}: scene={scene} humans={humans} schedule={schedule_mode}")
    return max(candidates, key=lambda item: item[0])[1]


def load_rows(run_dir: Path, *, robot: bool) -> list[dict[str, float]]:
    split = "with_robot" if robot else "no_robot"
    path = run_dir / split / "metrics.csv"
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parsed: dict[str, float] = {"step": float(row["step"])}
            for key, _label in set(AVG_METRICS + INSTANT_METRICS):
                if key in row and row[key] != "":
                    parsed[key] = float(row[key])
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
    pad = max((hi - lo) * 0.12, 0.015)
    return max(0.0, lo - pad), min(1.02, hi + pad)


def plot_grid(
    data: dict[tuple[str, str, str], dict[str, Any]],
    metrics: list[tuple[str, str]],
    title: str,
    output_name: str,
) -> None:
    fig, axes = plt.subplots(
        nrows=len(metrics),
        ncols=len(SCENES),
        figsize=(13.0, 7.7),
        sharex=True,
        constrained_layout=False,
    )
    handles = []
    labels = []

    for col, (scene, scene_label, _humans) in enumerate(SCENES):
        for row_idx, (metric_key, metric_label) in enumerate(metrics):
            ax = axes[row_idx][col]
            panel_values: list[float] = []
            for schedule, schedule_label, color in SCHEDULES:
                base_rows = data[(scene, schedule, "baseline")]["rows"]
                agent_rows = data[(scene, schedule, "agent")]["rows"]
                base_steps = [row["step"] for row in base_rows]
                base_values = [row[metric_key] for row in base_rows]
                agent_steps = [row["step"] for row in agent_rows]
                agent_values = [row[metric_key] for row in agent_rows]
                panel_values.extend(base_values)
                panel_values.extend(agent_values)
                base_label = f"{schedule_label} no robot"
                agent_label = f"{schedule_label} agent"
                base_line = ax.plot(
                    base_steps,
                    base_values,
                    color=color,
                    linestyle=":",
                    linewidth=1.05,
                    alpha=0.55,
                    label=base_label,
                )[0]
                agent_line = ax.plot(
                    agent_steps,
                    agent_values,
                    color=color,
                    linestyle="-",
                    linewidth=1.55,
                    alpha=0.95,
                    label=agent_label,
                )[0]
                for line, label in ((base_line, base_label), (agent_line, agent_label)):
                    if label not in labels:
                        handles.append(line)
                        labels.append(label)
            ax.set_ylim(*expanded_ylim(panel_values))
            ax.grid(True, color="#E8E8E8", linewidth=0.65)
            ax.tick_params(axis="both", labelsize=7.5)
            if col == 0:
                ax.set_ylabel(metric_label, fontsize=9)
            if row_idx == 0:
                ax.set_title(scene_label, fontsize=10, pad=3)
            if row_idx == len(metrics) - 1:
                ax.set_xlabel("Step", fontsize=8)

    fig.suptitle(title, fontsize=13, y=0.992)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.965), ncol=6, frameon=False, fontsize=8)
    fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.925), h_pad=0.55, w_pad=0.45)
    out = FIG_DIR / output_name
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict[tuple[str, str, str], dict[str, Any]] = {}
    for scene, _label, humans in SCENES:
        for schedule, _schedule_label, _color in SCHEDULES:
            baseline_run = latest_run(scene, humans, schedule, robot=False)
            agent_run = latest_run(scene, humans, schedule, robot=True)
            data[(scene, schedule, "baseline")] = {"run_dir": baseline_run, "rows": load_rows(baseline_run, robot=False)}
            data[(scene, schedule, "agent")] = {"run_dir": agent_run, "rows": load_rows(agent_run, robot=True)}

    plot_grid(
        data,
        AVG_METRICS,
        "Schedule Perturbation: Goal-Review Agent vs No-Robot Baseline",
        "schedule_agent_vs_baseline_avg_grid.png",
    )
    plot_grid(
        data,
        INSTANT_METRICS,
        "Schedule Perturbation: Instant Goal-Review Agent vs No-Robot Baseline",
        "schedule_agent_vs_baseline_instant_grid.png",
    )

    print("latest runs:")
    for scene, scene_label, _humans in SCENES:
        chunks = []
        for schedule, _schedule_label, _color in SCHEDULES:
            baseline = data[(scene, schedule, "baseline")]
            agent = data[(scene, schedule, "agent")]
            base_final = baseline["rows"][-1].get("final_score", float("nan"))
            agent_final = agent["rows"][-1].get("final_score", float("nan"))
            chunks.append(f"{schedule}: agent {agent_final:.4f} vs base {base_final:.4f}")
        print(f"{scene_label}: " + " | ".join(chunks))


if __name__ == "__main__":
    main()
