#!/usr/bin/env python3
"""Plot latest no-robot score curves for the five base scenes."""

from __future__ import annotations

import csv
import math
from pathlib import Path

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

METRICS = [
    ("final_score", "Final"),
    ("state_score", "State"),
    ("spatial_score", "Spatial"),
    ("human_event_score", "Human"),
]


def latest(paths: list[Path]) -> Path:
    existing = [path for path in paths if path.exists()]
    if not existing:
        raise FileNotFoundError("No matching no_robot metrics.csv found.")
    return max(existing, key=lambda path: path.stat().st_mtime)


def find_metrics(scene: str, humans: int) -> Path:
    pattern = f"steps_1600__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/metrics.csv"
    return latest(list((EXP_ROOT / scene).glob(pattern)))


def load_metrics(path: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parsed: dict[str, float] = {"step": float(row["step"])}
            for key, _ in METRICS:
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


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict[str, dict[str, object]] = {}
    for scene, _, humans in SCENES:
        path = find_metrics(scene, humans)
        data[scene] = {
            "path": path,
            "run_id": path.parents[1].name,
            "rows": load_metrics(path),
        }

    fig, axes = plt.subplots(
        nrows=len(METRICS),
        ncols=len(SCENES),
        figsize=(12.5, 7.8),
        sharex=True,
        constrained_layout=False,
    )

    color = "#555555"
    for col, (scene, scene_label, _) in enumerate(SCENES):
        rows = data[scene]["rows"]
        steps = [row["step"] for row in rows]  # type: ignore[index]
        for row_idx, (metric_key, metric_label) in enumerate(METRICS):
            ax = axes[row_idx][col]
            values = [row[metric_key] for row in rows]  # type: ignore[index]
            ax.plot(steps, values, color=color, linewidth=1.7)
            ax.set_ylim(*expanded_ylim(values))
            ax.grid(True, color="#E6E6E6", linewidth=0.7)
            ax.tick_params(axis="both", labelsize=8)
            if col == 0:
                ax.set_ylabel(metric_label, fontsize=9)
            if row_idx == 0:
                ax.set_title(scene_label, fontsize=10, pad=4)
            if row_idx == len(METRICS) - 1:
                ax.set_xlabel("Step", fontsize=8)

    fig.suptitle("No-Robot Baseline Score Curves", fontsize=13, y=0.995)
    fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.965), h_pad=0.7, w_pad=0.55)
    out = FIG_DIR / "no_robot_score_grid.png"
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)

    print(f"wrote {out}")
    for scene, label, _ in SCENES:
        run = data[scene]
        final = run["rows"][-1]  # type: ignore[index]
        print(
            f"{label}: {run['run_id']} "
            f"final={final['final_score']:.4f} state={final['state_score']:.4f} "
            f"spatial={final['spatial_score']:.4f} human={final['human_event_score']:.4f}"
        )


if __name__ == "__main__":
    main()
