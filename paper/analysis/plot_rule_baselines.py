#!/usr/bin/env python3
"""Plot 800-step rule-baseline scores for construct-validity analysis."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / "backend" / "data" / "experiments"
FIG_DIR = ROOT / "paper" / "figures" / "rule_baselines"
EXPERIMENT_STEPS = 800

SCENES = [
    ("simple_home_1f", "Home", 1),
    ("simple_hospital_1f", "Hospital", 3),
    ("simple_supermarket_1f", "Supermarket", 3),
    ("simple_office_1f", "Office", 3),
    ("simple_factory_1f", "Factory", 3),
]

METHODS = [
    ("no_robot", "No robot", "#8A8A8A"),
    ("nearest_repair", "Nearest repair", "#4C78A8"),
    ("human_blocking_first", "Human-blocking first", "#F58518"),
]

METRICS = [
    ("final_score", "Final"),
    ("state_score", "State"),
    ("spatial_score", "Spatial"),
    ("human_event_score", "Human"),
]


def latest(paths: list[Path]) -> Path | None:
    paths = [path for path in paths if path.exists()]
    return max(paths, key=lambda path: path.stat().st_mtime) if paths else None


def find_metrics(scene: str, humans: int, method: str) -> Path | None:
    scene_dir = EXP_ROOT / scene
    if method == "no_robot":
        pattern = f"steps_{EXPERIMENT_STEPS}__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/metrics.csv"
    else:
        pattern = f"steps_{EXPERIMENT_STEPS}__robots_1__humans_{humans}__model_rule_{method}/*/with_robot/metrics.csv"
    return latest(list(scene_dir.glob(pattern)))


def final_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty metrics file: {path}")
    return max(rows, key=lambda row: int(float(row["step"])))


def collect_rows() -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    for scene, scene_label, humans in SCENES:
        for method, method_label, _color in METHODS:
            path = find_metrics(scene, humans, method)
            if path is None:
                raise FileNotFoundError(f"missing metrics for {scene} {method}")
            row = final_row(path)
            if int(float(row["step"])) < EXPERIMENT_STEPS - 1:
                raise ValueError(f"incomplete metrics for {scene} {method}: {path}")
            item: dict[str, str | float] = {
                "scene": scene,
                "scene_label": scene_label,
                "method": method,
                "method_label": method_label,
                "run_id": path.parents[1].name,
            }
            for metric, _metric_label in METRICS:
                item[metric] = float(row[metric])
            rows.append(item)
    return rows


def write_csv(rows: list[dict[str, str | float]]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "rule_baseline_scores.csv"
    fieldnames = ["scene", "scene_label", "method", "method_label", "run_id", *[metric for metric, _ in METRICS]]
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out}")


def plot_scores(rows: list[dict[str, str | float]]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    scene_labels = [scene_label for _scene, scene_label, _humans in SCENES]
    x_positions = list(range(len(SCENES)))
    width = 0.24

    fig, axes = plt.subplots(1, len(METRICS), figsize=(13.2, 3.8), sharey=True)
    handles = []
    labels = []

    for ax, (metric, metric_label) in zip(axes, METRICS):
        for method_idx, (method, method_label, color) in enumerate(METHODS):
            values: list[float] = []
            for scene, _scene_label, _humans in SCENES:
                match = next(
                    row for row in rows if row["scene"] == scene and row["method"] == method
                )
                values.append(float(match[metric]))
            offset = (method_idx - (len(METHODS) - 1) / 2) * width
            bars = ax.bar(
                [x + offset for x in x_positions],
                values,
                width=width,
                color=color,
                alpha=0.9,
                label=method_label,
            )
            if method_label not in labels:
                handles.append(bars)
                labels.append(method_label)

        ax.set_title(metric_label)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(scene_labels, rotation=35, ha="right")
        ax.set_ylim(0.0, 1.03)
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.grid(axis="y", alpha=0.18, linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Score at step 799")
    fig.legend(handles, labels, loc="upper center", ncol=len(METHODS), frameon=False, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout(rect=[0, 0, 1, 0.92])

    out = FIG_DIR / "rule_baseline_scores.png"
    fig.savefig(out, dpi=240, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    rows = collect_rows()
    write_csv(rows)
    plot_scores(rows)


if __name__ == "__main__":
    main()
