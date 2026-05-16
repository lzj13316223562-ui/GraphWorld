#!/usr/bin/env python3
"""Plot non-cumulative score curves by de-averaging recorded metrics.

The experiment records state_score and spatial_score as cumulative averages:

    avg_t = (x_0 + ... + x_t) / (t + 1)

So the instantaneous score is recovered exactly as:

    x_t = avg_t * (t + 1) - avg_{t-1} * t

Do not recompute this figure from replay scenes: most long runs use
--replay-scene-interval, so replay scene payloads are intentionally sparse.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / "backend" / "data" / "experiments"
FIG_DIR = ROOT / "paper" / "figures" / "overview"
CACHE_PATH = ROOT / "paper" / "analysis" / "realtime_scores_cache.csv"

SCENES = [
    ("simple_home_1f", "Home", 1),
    ("simple_hospital_1f", "Hospital", 3),
    ("simple_supermarket_1f", "Supermarket", 3),
    ("simple_office_1f", "Office", 3),
    ("simple_factory_1f", "Factory", 3),
]

METHODS = [
    ("no_robot", "No robot", "#777777", "--", 0),
    ("reactive", "Reactive", "#D62728", "-", 1),
    ("single_round", "Single-round", "#E0A800", "-", 1),
    ("goal_review", "Goal-review", "#1F77B4", "-", 1),
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


def find_run(scene: str, method: str, humans: int) -> Path | None:
    scene_dir = EXP_ROOT / scene
    if method == "no_robot":
        metrics = latest(
            list(scene_dir.glob(f"steps_1600__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/metrics.csv"))
        )
    else:
        metrics = latest(
            list(
                scene_dir.glob(
                    f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_{method}/*/with_robot/metrics.csv"
                )
            )
        )
    return metrics.parent.parent if metrics else None


def recompute_run(scene: str, method: str, run_dir: Path, humans: int) -> list[dict[str, float | str]]:
    split = "no_robot" if method == "no_robot" else "with_robot"
    metrics_path = run_dir / split / "metrics.csv"
    with metrics_path.open(newline="", encoding="utf-8") as handle:
        metric_rows = sorted(csv.DictReader(handle), key=lambda row: int(float(row["step"])))

    rows: list[dict[str, float | str]] = []
    has_instant_scores = bool(metric_rows and "instant_state_score" in metric_rows[0])
    prev_avg_state = 0.0
    prev_avg_spatial = 0.0
    prev_count = 0
    for metric_row in metric_rows:
        step = int(float(metric_row["step"]))
        human = float(metric_row["human_event_score"])
        if has_instant_scores:
            state = float(metric_row["instant_state_score"])
            spatial = float(metric_row["instant_spatial_score"])
            final = float(metric_row["instant_final_score"])
        else:
            count = step + 1
            avg_state = float(metric_row["state_score"])
            avg_spatial = float(metric_row["spatial_score"])
            state = avg_state * count - prev_avg_state * prev_count
            spatial = avg_spatial * count - prev_avg_spatial * prev_count
            # Rounding during logging can cause tiny overshoots after de-averaging.
            state = min(1.0, max(0.0, state))
            spatial = min(1.0, max(0.0, spatial))
            final = state * 0.45 + spatial * 0.35 + human * 0.20
            prev_avg_state = avg_state
            prev_avg_spatial = avg_spatial
            prev_count = count
        rows.append(
            {
                "scene": scene,
                "method": method,
                "run_id": run_dir.name,
                "step": step,
                "final_score": round(final, 4),
                "state_score": round(state, 4),
                "spatial_score": round(spatial, 4),
                "human_event_score": round(human, 4),
            }
        )
    return rows


def load_or_recompute() -> dict[tuple[str, str], list[dict[str, float | str]]]:
    run_dirs: dict[tuple[str, str], Path] = {}
    for scene, _label, humans in SCENES:
        for method, _method_label, _color, _linestyle, _robots in METHODS:
            run_dir = find_run(scene, method, humans)
            if run_dir:
                run_dirs[(scene, method)] = run_dir

    cache_rows: list[dict[str, str]] = []
    if CACHE_PATH.exists():
        with CACHE_PATH.open(newline="", encoding="utf-8") as handle:
            cache_rows = list(csv.DictReader(handle))
    cached_run_ids = {
        (row["scene"], row["method"]): row["run_id"]
        for row in cache_rows
        if row.get("scene") and row.get("method") and row.get("run_id")
    }
    if cache_rows and all(cached_run_ids.get(key) == run_dir.name for key, run_dir in run_dirs.items()):
        out: dict[tuple[str, str], list[dict[str, float | str]]] = {}
        for row in cache_rows:
            key = (row["scene"], row["method"])
            out.setdefault(key, []).append(
                {
                    "scene": row["scene"],
                    "method": row["method"],
                    "run_id": row["run_id"],
                    "step": float(row["step"]),
                    "final_score": float(row["final_score"]),
                    "state_score": float(row["state_score"]),
                    "spatial_score": float(row["spatial_score"]),
                    "human_event_score": float(row["human_event_score"]),
                }
            )
        return out

    all_rows: list[dict[str, float | str]] = []
    for scene, _label, humans in SCENES:
        for method, method_label, _color, _linestyle, _robots in METHODS:
            run_dir = run_dirs.get((scene, method))
            if not run_dir:
                continue
            print(f"recompute {scene} {method_label}: {run_dir.name}", flush=True)
            all_rows.extend(recompute_run(scene, method, run_dir, humans))

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = ["scene", "method", "run_id", "step", "final_score", "state_score", "spatial_score", "human_event_score"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    out: dict[tuple[str, str], list[dict[str, float | str]]] = {}
    for row in all_rows:
        out.setdefault((str(row["scene"]), str(row["method"])), []).append(row)
    return out


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


def plot_grid(data: dict[tuple[str, str], list[dict[str, float | str]]]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(
        nrows=len(METRICS),
        ncols=len(SCENES),
        figsize=(12.5, 7.8),
        sharex=True,
        constrained_layout=False,
    )
    handles = []
    labels = []
    for col, (scene, scene_label, _humans) in enumerate(SCENES):
        for row_idx, (metric_key, metric_label) in enumerate(METRICS):
            ax = axes[row_idx][col]
            subplot_values: list[float] = []
            for method, method_label, color, linestyle, _robots in METHODS:
                rows = sorted(data.get((scene, method), []), key=lambda item: float(item["step"]))
                if not rows:
                    continue
                xs = [float(item["step"]) for item in rows]
                ys = [float(item[metric_key]) for item in rows]
                line = ax.plot(xs, ys, color=color, linestyle=linestyle, linewidth=1.3, alpha=0.9, label=method_label)[0]
                subplot_values.extend(ys)
                if method_label not in labels:
                    handles.append(line)
                    labels.append(method_label)
            ax.set_ylim(*expanded_ylim(subplot_values))
            ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
            ax.grid(True, color="#E6E6E6", linewidth=0.7)
            ax.tick_params(axis="both", labelsize=8)
            if row_idx == 0:
                ax.set_title(scene_label, fontsize=10, pad=4)
            if col == 0:
                ax.set_ylabel(metric_label, fontsize=9)
            if row_idx == len(METRICS) - 1:
                ax.set_xlabel("Step", fontsize=8)
    fig.suptitle("Realtime Score Curves by Scene and Metric", fontsize=13, y=0.995)
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.965))
    fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.955), h_pad=0.7, w_pad=0.55)
    out = FIG_DIR / "realtime_score_curves_by_scene_metric.png"
    fig.savefig(out, dpi=240, bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    plot_grid(load_or_recompute())


if __name__ == "__main__":
    main()
