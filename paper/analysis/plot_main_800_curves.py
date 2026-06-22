#!/usr/bin/env python3
"""Plot current 800-step Qwen main experiment curves."""

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

METHODS = [
    ("reactive", "Reactive", "#D62728"),
    ("single_round", "Single-round", "#E0A800"),
    ("goal_review", "Goal-review", "#1F77B4"),
]

METRICS = [
    ("final_score", "Final"),
    ("state_score", "State"),
    ("spatial_score", "Spatial"),
    ("human_event_score", "Human"),
]


def latest_metrics(scene: str, humans: int, method: str) -> Path:
    if method == "no_robot":
        pattern = f"steps_{STEPS}__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/metrics.csv"
    else:
        pattern = f"steps_{STEPS}__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_{method}/*/with_robot/metrics.csv"
    paths = list((EXP_ROOT / scene).glob(pattern))
    if not paths:
        raise FileNotFoundError(f"missing {scene} {method}")
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


def summarize(rows: list[dict[str, float]]) -> dict[str, float | int]:
    if not rows:
        raise ValueError("cannot summarize empty metrics rows")
    last = max(rows, key=lambda row: int(row["step"]))
    steps = {int(row["step"]) for row in rows}
    return {
        **{key: last[key] for key, _label in METRICS},
        "row_count": len(rows),
        "min_step": min(steps),
        "max_step": max(steps),
        "missing_steps": STEPS - len(steps),
    }


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict[tuple[str, str], list[dict[str, float]]] = {}
    summary_rows: list[dict[str, str | float]] = []

    for scene, _scene_label, humans in SCENES:
        rows = read_rows(latest_metrics(scene, humans, "no_robot"))
        data[(scene, "no_robot")] = rows
        summary_rows.append({"scene": scene, "method": "no_robot", **summarize(rows)})
        for method, _method_label, _color in METHODS:
            rows = read_rows(latest_metrics(scene, humans, method))
            data[(scene, method)] = rows
            summary_rows.append({"scene": scene, "method": method, **summarize(rows)})

    with (FIG_DIR / "final_scores_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "scene",
            "method",
            "final_score",
            "state_score",
            "spatial_score",
            "human_event_score",
            "row_count",
            "min_step",
            "max_step",
            "missing_steps",
        ]
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
            rows = data[(scene, "no_robot")]
            xs = [row["step"] for row in rows]
            ys = [row[metric] for row in rows]
            y_values.extend(ys)
            line = ax.plot(xs, ys, color="#666666", linestyle="--", linewidth=1.15, alpha=0.85, label="No robot")[0]
            if "No robot" not in labels:
                handles.append(line)
                labels.append("No robot")
            for method, method_label, color in METHODS:
                rows = data[(scene, method)]
                xs = [row["step"] for row in rows]
                ys = [row[metric] for row in rows]
                y_values.extend(ys)
                line = ax.plot(xs, ys, color=color, linewidth=1.45, label=method_label)[0]
                if method_label not in labels:
                    handles.append(line)
                    labels.append(method_label)
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
    fig.suptitle("Qwen3.5-9B Main Experiment: 800-step Score Curves", fontsize=13, y=0.995)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.965), ncol=4, frameon=False, fontsize=8.5)
    fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.925), h_pad=0.55, w_pad=0.45)
    out = FIG_DIR / "score_curves_by_scene_metric.png"
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
