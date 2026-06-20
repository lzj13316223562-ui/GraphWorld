#!/usr/bin/env python3
"""Compare final experiment scores across robot models.

The script reads the latest metrics.csv for each configured model/method and
writes one compact comparison figure plus the numeric table used by the plot.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / "backend" / "data" / "experiments"
FIG_DIR = ROOT / "paper" / "figures" / "model_comparison"
EXPERIMENT_STEPS = int(os.environ.get("EXPERIMENT_STEPS", "800"))

SCENES = [
    ("simple_home_1f", "Home", 1),
    ("simple_hospital_1f", "Hospital", 3),
    ("simple_supermarket_1f", "Supermarket", 3),
    ("simple_office_1f", "Office", 3),
    ("simple_factory_1f", "Factory", 3),
]

MODELS = [
    ("vllm_qwen3_5_9b", "Qwen3.5-9B", "#4C78A8"),
    ("vllm_deepseek_r1_14b", "DeepSeek-R1-14B", "#F58518"),
    ("vllm_llama3_1_8b", "Llama-3.1-8B", "#54A24B"),
]

METHODS = [
    ("reactive", "Reactive"),
    ("single_round", "Single-round"),
    ("goal_review", "Goal-review"),
]


def latest(paths: list[Path]) -> Path | None:
    paths = [path for path in paths if path.exists()]
    return max(paths, key=lambda path: path.stat().st_mtime) if paths else None


def find_metrics(scene: str, humans: int, model_slug: str | None, method: str | None) -> Path | None:
    scene_dir = EXP_ROOT / scene
    if model_slug is None:
        pattern = f"steps_{EXPERIMENT_STEPS}__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/metrics.csv"
        return latest(list(scene_dir.glob(pattern)))
    pattern = f"steps_{EXPERIMENT_STEPS}__robots_1__humans_{humans}__model_{model_slug}_{method}/*/with_robot/metrics.csv"
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
        baseline_path = find_metrics(scene, humans, None, None)
        baseline_score = None
        baseline_run = ""
        if baseline_path:
            row = final_row(baseline_path)
            baseline_score = float(row["final_score"])
            baseline_run = baseline_path.parents[1].name
            rows.append(
                {
                    "scene": scene,
                    "scene_label": scene_label,
                    "method": "no_robot",
                    "method_label": "No robot",
                    "model_slug": "npc_only_baseline",
                    "model_label": "No robot",
                    "run_id": baseline_run,
                    "final_score": baseline_score,
                    "delta_vs_no_robot": 0.0,
                }
            )

        for method, method_label in METHODS:
            for model_slug, model_label, _color in MODELS:
                path = find_metrics(scene, humans, model_slug, method)
                if not path:
                    continue
                row = final_row(path)
                final_score = float(row["final_score"])
                rows.append(
                    {
                        "scene": scene,
                        "scene_label": scene_label,
                        "method": method,
                        "method_label": method_label,
                        "model_slug": model_slug,
                        "model_label": model_label,
                        "run_id": path.parents[1].name,
                        "final_score": final_score,
                        "delta_vs_no_robot": final_score - baseline_score if baseline_score is not None else "",
                    }
                )
    return rows


def write_csv(rows: list[dict[str, str | float]]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / "model_final_scores_summary.csv"
    fieldnames = [
        "scene",
        "scene_label",
        "method",
        "method_label",
        "model_slug",
        "model_label",
        "run_id",
        "final_score",
        "delta_vs_no_robot",
    ]
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out}")


def plot_final_scores(rows: list[dict[str, str | float]]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    scene_labels = [label for _scene, label, _humans in SCENES]
    x_positions = list(range(len(SCENES)))
    width = 0.24

    fig, axes = plt.subplots(1, len(METHODS), figsize=(12.5, 3.9), sharey=True)
    handles = []
    labels = []

    baseline_by_scene = {
        row["scene_label"]: float(row["final_score"])
        for row in rows
        if row["method"] == "no_robot"
    }

    for ax, (method, method_label) in zip(axes, METHODS):
        for model_idx, (model_slug, model_label, color) in enumerate(MODELS):
            values: list[float] = []
            for scene, scene_label, _humans in SCENES:
                match = next(
                    (
                        row
                        for row in rows
                        if row["scene"] == scene and row["method"] == method and row["model_slug"] == model_slug
                    ),
                    None,
                )
                values.append(float(match["final_score"]) if match else float("nan"))
            offset = (model_idx - (len(MODELS) - 1) / 2) * width
            bars = ax.bar(
                [x + offset for x in x_positions],
                values,
                width=width,
                color=color,
                alpha=0.9,
                label=model_label,
            )
            if model_label not in labels:
                handles.append(bars)
                labels.append(model_label)

        baseline_values = [baseline_by_scene.get(scene_label, float("nan")) for scene_label in scene_labels]
        baseline_line = ax.plot(
            x_positions,
            baseline_values,
            color="#666666",
            linestyle="--",
            linewidth=1.4,
            marker="o",
            markersize=3.5,
            label="No robot",
        )[0]
        if "No robot" not in labels:
            handles.append(baseline_line)
            labels.append("No robot")

        ax.set_title(method_label, fontsize=11, fontweight="bold")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(scene_labels, rotation=25, ha="right")
        ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        ax.grid(True, axis="y", color="#E6E6E6", linewidth=0.7)
        ax.set_axisbelow(True)

    axes[0].set_ylabel(f"Final score at step {EXPERIMENT_STEPS}")
    fig.suptitle("Model comparison by scene and robot policy", fontsize=13, fontweight="bold", y=1.02)
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 0.98))

    out_png = FIG_DIR / "model_final_score_comparison.png"
    out_pdf = FIG_DIR / "model_final_score_comparison.pdf"
    fig.savefig(out_png, dpi=240, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(out_pdf, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"wrote {out_png}")
    print(f"wrote {out_pdf}")


def main() -> None:
    rows = collect_rows()
    write_csv(rows)
    plot_final_scores(rows)


if __name__ == "__main__":
    main()
