#!/usr/bin/env python3
"""Plot current 800-step Qwen profile diversity runs."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / "backend" / "data" / "experiments"
FIG_DIR = ROOT / "paper" / "figures" / "overview"
STEPS = 800

SCENES = [
    ("simple_home_1f", "Home", 1),
    ("simple_hospital_1f", "Hospital", 3),
    ("simple_supermarket_1f", "Supermarket", 3),
    ("simple_office_1f", "Office", 3),
    ("simple_factory_1f", "Factory", 3),
]

PROFILES = [
    ("compact_cleaning", "Compact", "#2CA02C"),
    ("normal", "Normal", "#F2B701"),
    ("spread_device", "Spread", "#D62728"),
]

METHODS = [
    ("goal_review", "Goal-review", "with_robot", "-", 1.45, 1.0),
    ("no_robot", "No-robot", "no_robot", "--", 1.2, 0.78),
]

METRICS = [
    ("final_score", "Final"),
    ("state_score", "State"),
    ("spatial_score", "Spatial"),
    ("human_event_score", "Human"),
]


def scene_dir(base_scene: str, profile: str) -> str:
    return base_scene if profile == "normal" else f"{base_scene}_{profile}"


def latest_metrics(base_scene: str, humans: int, profile: str, method: str) -> Path:
    directory = EXP_ROOT / scene_dir(base_scene, profile)
    if method == "goal_review":
        pattern = f"steps_{STEPS}__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_goal_review/*/with_robot/metrics.csv"
    elif method == "no_robot":
        pattern = f"steps_{STEPS}__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/metrics.csv"
    else:
        raise ValueError(f"unknown method: {method}")
    paths = list(directory.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"missing {base_scene} {profile} {method}")
    return max(paths, key=lambda path: path.stat().st_mtime)


def read_rows(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    out: list[dict[str, float]] = []
    for row in rows:
        parsed = {"step": float(row["step"])}
        for key, _label in METRICS:
            parsed[key] = float(row[key])
        out.append(parsed)
    return out


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict[tuple[str, str, str], list[dict[str, float]]] = {}
    summary_rows: list[dict[str, str | float]] = []
    for scene, _label, humans in SCENES:
        for profile, profile_label, _color in PROFILES:
            for method, method_label, _experiment, _linestyle, _linewidth, _alpha in METHODS:
                rows = read_rows(latest_metrics(scene, humans, profile, method))
                data[(scene, profile, method)] = rows
                last = rows[-1]
                summary_rows.append(
                    {
                        "scene": scene,
                        "profile": profile_label,
                        "method": method_label,
                        "final_score": last["final_score"],
                        "state_score": last["state_score"],
                        "spatial_score": last["spatial_score"],
                        "human_event_score": last["human_event_score"],
                    }
                )

    with (FIG_DIR / "profile_diversity_800_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["scene", "profile", "method", "final_score", "state_score", "spatial_score", "human_event_score"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    fig, axes = plt.subplots(len(METRICS), len(SCENES), figsize=(12.6, 7.6), sharex=True)
    handles = []
    labels = []
    for col, (scene, scene_label, _humans) in enumerate(SCENES):
        for row_idx, (metric, metric_label) in enumerate(METRICS):
            ax = axes[row_idx][col]
            y_values: list[float] = []
            for profile, profile_label, color in PROFILES:
                for method, method_label, _experiment, linestyle, linewidth, alpha in METHODS:
                    rows = data[(scene, profile, method)]
                    xs = [row["step"] for row in rows]
                    ys = [row[metric] for row in rows]
                    y_values.extend(ys)
                    label = f"{profile_label} {method_label}"
                    line = ax.plot(
                        xs,
                        ys,
                        color=color,
                        linestyle=linestyle,
                        linewidth=linewidth,
                        alpha=alpha,
                        label=label,
                    )[0]
                    if label not in labels:
                        handles.append(line)
                        labels.append(label)
            lo, hi = min(y_values), max(y_values)
            pad = max((hi - lo) * 0.12, 0.02)
            ax.set_ylim(max(0.0, lo - pad), min(1.02, hi + pad))
            ax.grid(True, color="#E8E8E8", linewidth=0.65)
            ax.tick_params(axis="both", labelsize=7.5)
            if row_idx == 0:
                ax.set_title(scene_label, fontsize=10, pad=3)
            if col == 0:
                ax.set_ylabel(metric_label, fontsize=9)
            if row_idx == len(METRICS) - 1:
                ax.set_xlabel("Step", fontsize=8)
    fig.suptitle("Graph Profile Diversity: Qwen3.5-9B Goal-Review vs No-Robot", fontsize=13, y=0.995)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.965), ncol=3, frameon=False, fontsize=8.0)
    fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.9), h_pad=0.55, w_pad=0.45)
    out = FIG_DIR / "diversity_profile_grid.png"
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
