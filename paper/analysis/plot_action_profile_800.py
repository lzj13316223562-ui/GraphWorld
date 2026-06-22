#!/usr/bin/env python3
"""Plot action-profile radar from available current Qwen fixed action logs."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / "backend" / "data" / "experiments"
FIG_DIR = ROOT / "paper" / "figures" / "overview"
STEPS = 800

SCENES = [
    ("simple_home_1f", 1),
    ("simple_hospital_1f", 3),
    ("simple_supermarket_1f", 3),
    ("simple_office_1f", 3),
    ("simple_factory_1f", 3),
]

METHODS = [
    ("reactive", "Reactive", "#D62728"),
    ("single_round", "Single-round", "#E0A800"),
    ("goal_review", "Goal-review", "#1F77B4"),
]

ACTION_BUCKETS = [
    ("move", {"move"}),
    ("pick", {"pick"}),
    ("place", {"place"}),
    ("clean", {"brush"}),
    ("open/close", {"open", "close"}),
    ("operate", {"press", "dump", "fold", "use"}),
    ("other", set()),
]


def latest_metrics(scene: str, humans: int, method: str) -> Path:
    pattern = f"steps_{STEPS}__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_{method}/*/with_robot/metrics.csv"
    paths = list((EXP_ROOT / scene).glob(pattern))
    if not paths:
        raise FileNotFoundError(f"missing {scene} {method}")
    return max(paths, key=lambda path: path.stat().st_mtime)


def max_step(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        steps = [int(float(row["step"])) for row in csv.DictReader(handle)]
    return max(steps) if steps else -1


def bucket_action(action: str) -> str:
    action = (action or "").strip()
    for bucket, names in ACTION_BUCKETS:
        if action in names:
            return bucket
    return "other"


def collect_counts() -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for scene, humans in SCENES:
        for method, _label, _color in METHODS:
            path = latest_metrics(scene, humans, method)
            if max_step(path) < STEPS - 1:
                raise ValueError(f"incomplete run for {scene} {method}: {path}")
            with path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    action = row.get("action", "")
                    if action:
                        counts[method][bucket_action(action)] += 1
    return counts


def write_summary(counts: dict[str, Counter[str]]) -> None:
    out = FIG_DIR / "action_profile_800_summary.csv"
    labels = [bucket for bucket, _names in ACTION_BUCKETS]
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["method", "total", *labels])
        writer.writeheader()
        for method, _label, _color in METHODS:
            total = sum(counts[method].values())
            row = {"method": method, "total": total}
            for bucket in labels:
                row[bucket] = counts[method][bucket] / total if total else 0.0
            writer.writerow(row)
    print(f"wrote {out}")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    counts = collect_counts()
    write_summary(counts)

    labels = [bucket for bucket, _names in ACTION_BUCKETS]
    angles = [idx / len(labels) * 2.0 * 3.141592653589793 for idx in range(len(labels))]
    angles += angles[:1]

    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_offset(3.141592653589793 / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 0.55)
    ax.set_yticks([0.15, 0.30, 0.45])
    ax.set_yticklabels(["0.15", "0.30", "0.45"], fontsize=8)
    ax.grid(True, color="#E1E1E1")

    for method, label, color in METHODS:
        total = sum(counts[method].values()) or 1
        series = [counts[method][bucket] / total for bucket in labels]
        series += series[:1]
        ax.plot(angles, series, color=color, linewidth=2.1, label=label)
        ax.fill(angles, series, color=color, alpha=0.055)

    ax.set_title("Qwen3.5-9B Action Profile by Method (available 800-step logs)", y=1.12, fontsize=14)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.14), frameon=False)
    fig.tight_layout()

    out = FIG_DIR / "action_profile_radar_by_method.png"
    fig.savefig(out, dpi=240)
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
