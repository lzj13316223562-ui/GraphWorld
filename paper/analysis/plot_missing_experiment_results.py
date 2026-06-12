#!/usr/bin/env python3
"""Plot the completed diversity and schedule supplement experiments."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / "backend" / "data" / "experiments"
OUT_DIR = ROOT / "paper" / "figures" / "overview"

SCENES = [
    ("simple_home_1f", "Home", 1),
    ("simple_hospital_1f", "Hospital", 3),
    ("simple_supermarket_1f", "Supermarket", 3),
    ("simple_office_1f", "Office", 3),
    ("simple_factory_1f", "Factory", 3),
]

PROFILES = [
    ("compact_cleaning", "Compact", "#2CA02C"),
    ("normal_logistics", "Normal", "#F2B701"),
    ("spread_device", "Spread", "#D62728"),
]

SCHEDULES = [
    ("fixed", "Fixed"),
    ("calendar", "Calendar"),
    ("stochastic", "Stochastic"),
]

METHODS = [
    ("no_robot", "No robot", "#777777", "--"),
    ("reactive", "Reactive", "#D62728", "-"),
    ("single_round", "Single-round", "#F2B701", "-"),
    ("goal_review", "Goal-review", "#1F77B4", "-"),
]

METRICS = [
    ("final_score", "Final"),
    ("state_score", "State"),
    ("spatial_score", "Spatial"),
    ("human_event_score", "Human"),
]


def read_summary(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_metrics(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parsed: dict[str, float] = {"step": float(row["step"])}
            for key, _label in METRICS:
                parsed[key] = float(row.get(key) or "nan")
            rows.append(parsed)
    return rows


def latest_run(scene_dir: str, exp_dir: str, split: str, *, schedule: str | None = None, method: str | None = None) -> Path:
    candidates: list[tuple[float, Path]] = []
    for summary_path in (EXP_ROOT / scene_dir).glob(f"{exp_dir}/*/summary.json"):
        try:
            summary = read_summary(summary_path)
        except Exception:
            continue
        if int(summary.get("steps", -1)) != 1600:
            continue
        if schedule is not None and str(summary.get("schedule_mode") or "fixed") != schedule:
            continue
        if method is not None and method != "no_robot" and str(summary.get("agent_mode") or "") != method:
            continue
        metrics = summary_path.parent / split / "metrics.csv"
        if metrics.exists():
            candidates.append((summary_path.stat().st_mtime, metrics))
    if not candidates:
        raise FileNotFoundError(f"missing {scene_dir} {exp_dir} {split} schedule={schedule} method={method}")
    return max(candidates, key=lambda item: item[0])[1]


def expanded_ylim(values: list[float]) -> tuple[float, float]:
    values = [value for value in values if not math.isnan(value)]
    if not values:
        return 0.0, 1.0
    lo, hi = min(values), max(values)
    if hi - lo < 0.04:
        mid = (lo + hi) / 2.0
        lo, hi = mid - 0.04, mid + 0.04
    pad = max((hi - lo) * 0.14, 0.015)
    return max(0.0, lo - pad), min(1.02, hi + pad)


def auc(rows: list[dict[str, float]], metric: str) -> float:
    if not rows:
        return float("nan")
    return sum(row[metric] for row in rows) / len(rows)


def load_diversity() -> dict[tuple[str, str, str], dict[str, Any]]:
    data: dict[tuple[str, str, str], dict[str, Any]] = {}
    for scene, _label, humans in SCENES:
        for profile, _profile_label, _color in PROFILES:
            scene_dir = f"{scene}_{profile}"
            base_exp = f"steps_1600__robots_0__humans_{humans}__model_npc_only_baseline"
            agent_exp = f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_goal_review"
            for method, exp_dir, split in (
                ("no_robot", base_exp, "no_robot"),
                ("goal_review", agent_exp, "with_robot"),
            ):
                metrics = latest_run(scene_dir, exp_dir, split, method=method)
                data[(scene, profile, method)] = {"path": metrics, "rows": read_metrics(metrics)}
    return data


def load_schedule_all_methods() -> dict[tuple[str, str, str], dict[str, Any]]:
    data: dict[tuple[str, str, str], dict[str, Any]] = {}
    for scene, _label, humans in SCENES:
        for schedule, _schedule_label in SCHEDULES:
            if schedule == "fixed":
                base_suffix = ""
                seed_suffix = ""
            elif schedule == "calendar":
                base_suffix = "__schedule_calendar__seed_0"
                seed_suffix = "__schedule_calendar__seed_0"
            else:
                base_suffix = "__schedule_stochastic__seed_42"
                seed_suffix = "__schedule_stochastic__seed_42"

            no_robot_exp = f"steps_1600__robots_0__humans_{humans}__model_npc_only_baseline{base_suffix}"
            metrics = latest_run(scene, no_robot_exp, "no_robot", schedule=schedule, method="no_robot")
            data[(scene, schedule, "no_robot")] = {"path": metrics, "rows": read_metrics(metrics)}

            for method in ("reactive", "single_round", "goal_review"):
                exp = f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_{method}{seed_suffix}"
                metrics = latest_run(scene, exp, "with_robot", schedule=schedule, method=method)
                data[(scene, schedule, method)] = {"path": metrics, "rows": read_metrics(metrics)}
    return data


def plot_diversity(data: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    fig, axes = plt.subplots(len(METRICS), len(SCENES), figsize=(13.2, 7.8), sharex=True)
    handles = []
    labels = []
    for col, (scene, scene_label, _humans) in enumerate(SCENES):
        for row_idx, (metric, metric_label) in enumerate(METRICS):
            ax = axes[row_idx][col]
            values: list[float] = []
            for profile, profile_label, color in PROFILES:
                for method, method_label, linestyle, alpha, lw in (
                    ("no_robot", "No robot", ":", 0.65, 1.15),
                    ("goal_review", "Goal-review", "-", 0.95, 1.7),
                ):
                    rows = data[(scene, profile, method)]["rows"]
                    steps = [r["step"] for r in rows]
                    ys = [r[metric] for r in rows]
                    values.extend(ys)
                    label = f"{profile_label} {method_label}"
                    line = ax.plot(steps, ys, color=color, linestyle=linestyle, alpha=alpha, linewidth=lw, label=label)[0]
                    if label not in labels:
                        handles.append(line)
                        labels.append(label)
            ax.set_ylim(*expanded_ylim(values))
            ax.grid(True, color="#E8E8E8", linewidth=0.65)
            ax.tick_params(axis="both", labelsize=7.3)
            if col == 0:
                ax.set_ylabel(metric_label, fontsize=9)
            if row_idx == 0:
                ax.set_title(scene_label, fontsize=10, pad=3)
            if row_idx == len(METRICS) - 1:
                ax.set_xlabel("Step", fontsize=8)
    fig.suptitle("Graph Diversity: Goal-Review Agent vs No-Robot Baseline", fontsize=13, y=0.992)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.964), ncol=6, frameon=False, fontsize=7.7)
    fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.925), h_pad=0.55, w_pad=0.45)
    out = OUT_DIR / "diversity_profile_grid.png"
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"wrote {out}")


def plot_schedule_methods(data: dict[tuple[str, str, str], dict[str, Any]]) -> None:
    for schedule, schedule_label in SCHEDULES:
        fig, axes = plt.subplots(len(METRICS), len(SCENES), figsize=(13.2, 7.8), sharex=True)
        handles = []
        labels = []
        for col, (scene, scene_label, _humans) in enumerate(SCENES):
            for row_idx, (metric, metric_label) in enumerate(METRICS):
                ax = axes[row_idx][col]
                values: list[float] = []
                for method, method_label, color, linestyle in METHODS:
                    rows = data[(scene, schedule, method)]["rows"]
                    steps = [r["step"] for r in rows]
                    ys = [r[metric] for r in rows]
                    values.extend(ys)
                    line = ax.plot(steps, ys, color=color, linestyle=linestyle, linewidth=1.55 if method != "no_robot" else 1.15, alpha=0.95 if method != "no_robot" else 0.7, label=method_label)[0]
                    if method_label not in labels:
                        handles.append(line)
                        labels.append(method_label)
                ax.set_ylim(*expanded_ylim(values))
                ax.grid(True, color="#E8E8E8", linewidth=0.65)
                ax.tick_params(axis="both", labelsize=7.3)
                if col == 0:
                    ax.set_ylabel(metric_label, fontsize=9)
                if row_idx == 0:
                    ax.set_title(scene_label, fontsize=10, pad=3)
                if row_idx == len(METRICS) - 1:
                    ax.set_xlabel("Step", fontsize=8)
        fig.suptitle(f"Schedule Methods: {schedule_label}", fontsize=13, y=0.992)
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.964), ncol=4, frameon=False, fontsize=8)
        fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.925), h_pad=0.55, w_pad=0.45)
        out = OUT_DIR / f"schedule_methods_{schedule}_grid.png"
        fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.03)
        plt.close(fig)
        print(f"wrote {out}")


def write_summary(
    diversity: dict[tuple[str, str, str], dict[str, Any]],
    schedule_data: dict[tuple[str, str, str], dict[str, Any]],
) -> None:
    out = OUT_DIR / "missing_experiment_summary.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["experiment", "scene", "condition", "method", "final", "state", "spatial", "human", "auc_final", "delta_vs_no_robot"])
        for scene, scene_label, _humans in SCENES:
            for profile, profile_label, _color in PROFILES:
                base_rows = diversity[(scene, profile, "no_robot")]["rows"]
                base_final = base_rows[-1]["final_score"]
                for method in ("no_robot", "goal_review"):
                    rows = diversity[(scene, profile, method)]["rows"]
                    last = rows[-1]
                    writer.writerow([
                        "diversity",
                        scene_label,
                        profile_label,
                        method,
                        f"{last['final_score']:.4f}",
                        f"{last['state_score']:.4f}",
                        f"{last['spatial_score']:.4f}",
                        f"{last['human_event_score']:.4f}",
                        f"{auc(rows, 'final_score'):.4f}",
                        f"{last['final_score'] - base_final:+.4f}",
                    ])
            for schedule, schedule_label in SCHEDULES:
                base_rows = schedule_data[(scene, schedule, "no_robot")]["rows"]
                base_final = base_rows[-1]["final_score"]
                for method, _label, _color, _linestyle in METHODS:
                    rows = schedule_data[(scene, schedule, method)]["rows"]
                    last = rows[-1]
                    writer.writerow([
                        "schedule",
                        scene_label,
                        schedule_label,
                        method,
                        f"{last['final_score']:.4f}",
                        f"{last['state_score']:.4f}",
                        f"{last['spatial_score']:.4f}",
                        f"{last['human_event_score']:.4f}",
                        f"{auc(rows, 'final_score'):.4f}",
                        f"{last['final_score'] - base_final:+.4f}",
                    ])
    print(f"wrote {out}")


def print_key_findings(
    diversity: dict[tuple[str, str, str], dict[str, Any]],
    schedule_data: dict[tuple[str, str, str], dict[str, Any]],
) -> None:
    print("\nDiversity final score deltas:")
    for scene, scene_label, _humans in SCENES:
        chunks = []
        for profile, profile_label, _color in PROFILES:
            base = diversity[(scene, profile, "no_robot")]["rows"][-1]["final_score"]
            agent = diversity[(scene, profile, "goal_review")]["rows"][-1]["final_score"]
            chunks.append(f"{profile_label}: {agent:.3f} vs {base:.3f} ({agent - base:+.3f})")
        print(f"{scene_label}: " + " | ".join(chunks))

    print("\nSchedule final score method ranking:")
    for scene, scene_label, _humans in SCENES:
        for schedule, schedule_label in SCHEDULES:
            scores = []
            for method, method_label, _color, _style in METHODS:
                score = schedule_data[(scene, schedule, method)]["rows"][-1]["final_score"]
                scores.append((score, method_label))
            scores.sort(reverse=True)
            print(f"{scene_label}/{schedule_label}: " + " > ".join(f"{label} {score:.3f}" for score, label in scores))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    diversity = load_diversity()
    schedule_data = load_schedule_all_methods()
    plot_diversity(diversity)
    plot_schedule_methods(schedule_data)
    write_summary(diversity, schedule_data)
    print_key_findings(diversity, schedule_data)


if __name__ == "__main__":
    main()
