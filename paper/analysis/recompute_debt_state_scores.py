from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from itertools import chain
from json import JSONDecodeError
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.runtime.eval.matrix_evaluator import build_matrix_snapshot, scene_nodes


EXP_ROOT = ROOT / "backend/data/experiments"
FIG_DIR = ROOT / "paper/figures/overview"
OUT_CSV = ROOT / "paper/analysis/debt_state_scores.csv"
OUT_SUMMARY = ROOT / "paper/analysis/debt_state_summary.md"

SCENES = [
    ("simple_home_1f", "Home", 1),
    ("simple_hospital_1f", "Hospital", 3),
    ("simple_supermarket_1f", "Supermarket", 3),
    ("simple_office_1f", "Office", 3),
    ("simple_factory_1f", "Factory", 3),
]

METHODS = [
    ("no_robot", "No robot", "#777777", "--"),
    ("reactive", "Reactive", "#D62728", "-"),
    ("single_round", "Single-round", "#F2B701", "-"),
    ("goal_review", "Goal-review", "#1F77B4", "-"),
]


def latest(paths: list[Path]) -> Path | None:
    paths = [path for path in paths if path.exists()]
    return max(paths, key=lambda path: path.stat().st_mtime) if paths else None


def find_replay(scene: str, humans: int, method: str) -> Path | None:
    scene_dir = EXP_ROOT / scene
    if method == "no_robot":
        return latest(list(scene_dir.glob(f"steps_1600__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/replay.json")))
    labelled = list(scene_dir.glob(f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_{method}/*/with_robot/replay.json"))
    if labelled:
        return latest(labelled)
    if method == "goal_review":
        return latest(list(scene_dir.glob(f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b/*/with_robot/replay.json")))
    return None


def iter_json_array(path: Path):
    decoder = json.JSONDecoder()
    buffer = ""
    pos = 0
    with path.open(encoding="utf-8") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            buffer += chunk
            while True:
                while pos < len(buffer) and buffer[pos] in " \r\n\t,[":
                    pos += 1
                if pos < len(buffer) and buffer[pos] == "]":
                    return
                if pos >= len(buffer):
                    break
                try:
                    item, end = decoder.raw_decode(buffer, pos)
                except JSONDecodeError:
                    if pos:
                        buffer = buffer[pos:]
                        pos = 0
                    break
                yield item
                pos = end
                if pos > 4 * 1024 * 1024:
                    buffer = buffer[pos:]
                    pos = 0
        while True:
            while pos < len(buffer) and buffer[pos] in " \r\n\t,[":
                pos += 1
            if pos >= len(buffer) or buffer[pos] == "]":
                break
            item, end = decoder.raw_decode(buffer, pos)
            yield item
            pos = end


def iter_replay_records(replay_path: Path):
    jsonl_path = replay_path.with_suffix(".jsonl")
    if jsonl_path.exists():
        with jsonl_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)
        return
    yield from iter_json_array(replay_path)


def iter_full_frames(replay_path: Path):
    for item in iter_replay_records(replay_path):
        if scene_nodes(item.get("scene") or {}):
            yield item


def full_state_score(snapshot, baseline) -> tuple[float, int, int]:
    baseline_index = {node_id: idx for idx, node_id in enumerate(baseline.node_ids)}
    comparable = 0
    different = 0
    for current_idx, node_id in enumerate(snapshot.node_ids):
        baseline_idx = baseline_index.get(node_id)
        if baseline_idx is None:
            continue
        for col_idx, value in enumerate(snapshot.state_matrix[current_idx]):
            expected = baseline.state_matrix[baseline_idx][col_idx]
            if value is None or expected is None:
                continue
            comparable += 1
            different += int(value != expected)
    return (1.0 - different / comparable if comparable else 1.0), different, comparable


def debt_score(snapshot, baseline, debt_mask: set[tuple[str, int, str]]) -> tuple[float, int, int]:
    current_index = {node_id: idx for idx, node_id in enumerate(snapshot.node_ids)}
    baseline_index = {node_id: idx for idx, node_id in enumerate(baseline.node_ids)}
    comparable = 0
    different = 0
    for node_id, col_idx, _state in debt_mask:
        current_idx = current_index.get(node_id)
        baseline_idx = baseline_index.get(node_id)
        if current_idx is None or baseline_idx is None:
            continue
        value = snapshot.state_matrix[current_idx][col_idx]
        expected = baseline.state_matrix[baseline_idx][col_idx]
        if value is None or expected is None:
            continue
        comparable += 1
        different += int(value != expected)
    return (1.0 - different / comparable if comparable else 1.0), different, comparable


def build_debt_mask(no_robot_path: Path) -> tuple[set[tuple[str, int, str]], dict[str, int]]:
    frames = iter_full_frames(no_robot_path)
    first = next(frames, None)
    if first is None:
        return set(), {}
    baseline = build_matrix_snapshot(first["scene"])
    baseline_index = {node_id: idx for idx, node_id in enumerate(baseline.node_ids)}
    mask: set[tuple[str, int, str]] = set()
    for item in chain((first,), frames):
        snapshot = build_matrix_snapshot(item["scene"])
        for current_idx, node_id in enumerate(snapshot.node_ids):
            baseline_idx = baseline_index.get(node_id)
            if baseline_idx is None:
                continue
            for col_idx, state_name in enumerate(snapshot.state_columns):
                value = snapshot.state_matrix[current_idx][col_idx]
                expected = baseline.state_matrix[baseline_idx][col_idx]
                if value is None or expected is None:
                    continue
                if value != expected:
                    mask.add((node_id, col_idx, state_name))
    return mask, dict(sorted(Counter(state for _, _, state in mask).items()))


def recompute() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for scene, scene_label, humans in SCENES:
        no_robot_path = find_replay(scene, humans, "no_robot")
        if no_robot_path is None:
            continue
        debt_mask, mask_by_state = build_debt_mask(no_robot_path)
        if not debt_mask:
            continue
        summaries[scene] = {
            "scene_label": scene_label,
            "debt_cells": len(debt_mask),
            "mask_by_state": mask_by_state,
            "runs": {},
        }
        for method, method_label, _color, _linestyle in METHODS:
            replay_path = find_replay(scene, humans, method)
            if replay_path is None:
                continue
            series = []
            baseline = None
            for item in iter_full_frames(replay_path):
                if baseline is None:
                    baseline = build_matrix_snapshot(item["scene"])
                snapshot = build_matrix_snapshot(item["scene"])
                full_score, full_diff, full_total = full_state_score(snapshot, baseline)
                masked_score, masked_diff, masked_total = debt_score(snapshot, baseline, debt_mask)
                step = int(item["episode_step"])
                row = {
                    "scene": scene,
                    "scene_label": scene_label,
                    "method": method,
                    "method_label": method_label,
                    "run_id": replay_path.parents[1].name,
                    "step": step,
                    "full_state_instant": full_score,
                    "full_state_diff": full_diff,
                    "full_state_total": full_total,
                    "debt_state_instant": masked_score,
                    "debt_state_diff": masked_diff,
                    "debt_state_total": masked_total,
                    "debt_cells": len(debt_mask),
                    "replay_path": str(replay_path.relative_to(ROOT)),
                }
                rows.append(row)
                series.append(row)
            if not series:
                continue
            summaries[scene]["runs"][method] = {
                "method_label": method_label,
                "run_id": replay_path.parents[1].name,
                "frames": len(series),
                "last_step": series[-1]["step"],
                "full_final": series[-1]["full_state_instant"],
                "debt_final": series[-1]["debt_state_instant"],
                "full_auc": sum(row["full_state_instant"] for row in series) / len(series),
                "debt_auc": sum(row["debt_state_instant"] for row in series) / len(series),
                "replay_path": str(replay_path.relative_to(ROOT)),
            }
    return rows, summaries


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "scene",
        "method",
        "run_id",
        "step",
        "full_state_instant",
        "full_state_diff",
        "full_state_total",
        "debt_state_instant",
        "debt_state_diff",
        "debt_state_total",
        "debt_cells",
        "replay_path",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            for key in ("full_state_instant", "debt_state_instant"):
                out[key] = f"{float(out[key]):.4f}"
            writer.writerow({key: out.get(key, "") for key in columns})


def expanded_ylim(values: list[float]) -> tuple[float, float]:
    values = [value for value in values if not math.isnan(value)]
    if not values:
        return 0.0, 1.0
    lo, hi = min(values), max(values)
    if hi - lo < 0.05:
        mid = (lo + hi) / 2
        lo, hi = mid - 0.05, mid + 0.05
    pad = max((hi - lo) * 0.14, 0.025)
    return max(0.0, lo - pad), min(1.02, hi + pad)


def plot_grid(rows: list[dict[str, Any]]) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        by_key.setdefault((row["scene"], row["method"]), []).append(row)
    fig, axes = plt.subplots(nrows=2, ncols=len(SCENES), figsize=(14.5, 5.7), sharex=False)
    legend_handles = []
    legend_labels = []
    for col, (scene, scene_label, _humans) in enumerate(SCENES):
        for row_idx, (metric_key, title) in enumerate((("full_state_instant", "Full state"), ("debt_state_instant", "Human-debt state"))):
            ax = axes[row_idx][col]
            values: list[float] = []
            for method, method_label, color, linestyle in METHODS:
                series = by_key.get((scene, method), [])
                if not series:
                    continue
                series = sorted(series, key=lambda item: item["step"])
                xs = [item["step"] for item in series]
                ys = [float(item[metric_key]) for item in series]
                line = ax.plot(xs, ys, color=color, linestyle=linestyle, linewidth=1.8, label=method_label)[0]
                values.extend(ys)
                if method_label not in legend_labels:
                    legend_handles.append(line)
                    legend_labels.append(method_label)
            ax.set_ylim(*expanded_ylim(values))
            ax.grid(True, color="#E6E6E6", linewidth=0.7)
            if row_idx == 0:
                ax.set_title(scene_label, fontsize=11)
            if col == 0:
                ax.set_ylabel(title)
            if row_idx == 1:
                ax.set_xlabel("Step")
    fig.suptitle("Offline recomputed state scores: full matrix vs human-debt mask", fontsize=13, y=0.99)
    fig.legend(legend_handles, legend_labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.94))
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(FIG_DIR / "debt_state_score_grid.png", dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def write_summary(summaries: dict[str, dict[str, Any]]) -> None:
    lines = [
        "# Offline Human-Debt State Recompute",
        "",
        "Mask 定义：对每个场景，先用 no_robot replay 找出曾经偏离初始值的状态格子；之后所有方法都只在这些格子上重算 state 分。",
        "",
        "注意：这里使用 replay 里保存了完整 scene 的帧，因此是离线重算曲线，不是改评分器后逐 step 重跑。",
        "",
        f"- CSV: `{OUT_CSV.relative_to(ROOT)}`",
        f"- Figure: `paper/figures/overview/debt_state_score_grid.png`",
        "",
    ]
    for scene, _scene_label, _humans in SCENES:
        summary = summaries.get(scene)
        if not summary:
            continue
        lines.extend(
            [
                f"## {summary['scene_label']}",
                "",
                f"- Debt cells: `{summary['debt_cells']}`",
                f"- Mask by state: `{summary['mask_by_state']}`",
                "",
                "| Method | Frames | Last step | Full final | Debt final | Full AUC | Debt AUC |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for method, method_label, _color, _linestyle in METHODS:
            run = summary["runs"].get(method)
            if not run:
                continue
            lines.append(
                f"| {method_label} | {run['frames']} | {run['last_step']} | "
                f"{run['full_final']:.4f} | {run['debt_final']:.4f} | "
                f"{run['full_auc']:.4f} | {run['debt_auc']:.4f} |"
            )
        lines.append("")
    OUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows, summaries = recompute()
    write_csv(rows)
    plot_grid(rows)
    write_summary(summaries)
    print(f"wrote {OUT_CSV}")
    print(f"wrote {FIG_DIR / 'debt_state_score_grid.png'}")
    print(f"wrote {OUT_SUMMARY}")
    for scene, summary in summaries.items():
        print(scene, "debt_cells=", summary["debt_cells"], "mask=", summary["mask_by_state"])


if __name__ == "__main__":
    main()
