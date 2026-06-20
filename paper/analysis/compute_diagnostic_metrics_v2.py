from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_CSV = ROOT / "docs" / "experiment_inventory_800_dedup.csv"
OUTPUT_CSV = ROOT / "docs" / "diagnostic_metrics_800_v2.csv"
OUTPUT_MD = ROOT / "docs" / "diagnostic_metrics_800_v2_summary.md"
STALE_STEPS = 12


def load_inventory() -> list[dict[str, str]]:
    with INVENTORY_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_metrics_final_score(metrics_path: Path) -> float:
    with metrics_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"Empty metrics file: {metrics_path}")
    return float(rows[-1]["final_score"])


def iter_replay_steps(run_dir: Path) -> Iterable[dict]:
    replay_jsonl_path = run_dir / "replay.jsonl"
    if replay_jsonl_path.exists():
        with replay_jsonl_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
        return

    replay_path = run_dir / "replay.json"
    with replay_path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Replay is not a JSON array: {replay_path}")
    for item in data:
        yield item


def normalize_method(model_name: str) -> tuple[str, str]:
    if model_name == "npc_only_baseline":
        return ("npc_only_baseline", "npc_only_baseline")
    for method in ("goal_review", "single_round", "reactive"):
        suffix = f"_{method}"
        if model_name.endswith(suffix):
            backbone = model_name[: -len(suffix)]
            return (backbone, method)
    parts = model_name.split("_")
    if len(parts) < 2:
        return (model_name, model_name)
    method = parts[-1]
    backbone = "_".join(parts[:-1])
    return backbone, method


def compute_run_metrics(replay_steps: Iterable[dict]) -> dict[str, float | int]:
    action_target_counts: Counter[tuple[str, str]] = Counter()
    total_actions = 0

    started_task_instances = 0
    completed_task_instances_proxy = 0
    premature_switch_count = 0

    prev_task = ""
    prev_phase = ""
    prev_steps_without_progress: int | None = None

    for step in replay_steps:
        action = step.get("action") or {}
        action_name = str(action.get("action") or "")
        target = str(action.get("target") or "")
        if action_name:
            total_actions += 1
            action_target_counts[(action_name, target)] += 1

        goal = ((step.get("active_goals") or {}).get("robot_01")) or None
        task = str(goal.get("task") or "") if isinstance(goal, dict) else ""
        phase = str(goal.get("phase") or "") if isinstance(goal, dict) else ""
        steps_without_progress = (
            int(goal.get("steps_without_progress") or 0) if isinstance(goal, dict) else None
        )

        if task and task != prev_task:
            started_task_instances += 1
            if prev_task and prev_phase != "done":
                premature_switch_count += 1

        if prev_task and not task:
            if prev_phase == "done" or (
                prev_steps_without_progress is not None and prev_steps_without_progress < STALE_STEPS
            ):
                completed_task_instances_proxy += 1

        prev_task = task
        prev_phase = phase
        prev_steps_without_progress = steps_without_progress

    fixation_ratio = (
        max(action_target_counts.values()) / total_actions if total_actions and action_target_counts else 0.0
    )
    phase_completion_rate_proxy = (
        completed_task_instances_proxy / started_task_instances if started_task_instances else 0.0
    )

    return {
        "总动作数": total_actions,
        "启动任务实例数": started_task_instances,
        "完成任务实例数_代理": completed_task_instances_proxy,
        "阶段完成率_代理": round(phase_completion_rate_proxy, 4),
        "局部固着率": round(fixation_ratio, 4),
        "过早切换次数": premature_switch_count,
    }


def format_mean(values: list[float]) -> str:
    if not values:
        return "0.0000"
    return f"{sum(values) / len(values):.4f}"


def main() -> None:
    rows = load_inventory()

    baseline_scores: dict[tuple[str, str, str], float] = {}
    for row in rows:
        if row["split"] != "no_robot":
            continue
        metrics_path = ROOT / row["metrics_path"]
        baseline_scores[(row["scene"], row["schedule"], row["seed"])] = read_metrics_final_score(metrics_path)

    output_rows: list[dict[str, object]] = []
    by_method: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in rows:
        if row["split"] != "with_robot":
            continue
        metrics_path = ROOT / row["metrics_path"]
        final_score = read_metrics_final_score(metrics_path)
        replay_steps = iter_replay_steps(metrics_path.parent)
        backbone, method = normalize_method(row["model"])
        baseline = baseline_scores[(row["scene"], row["schedule"], row["seed"])]
        computed = compute_run_metrics(replay_steps)

        result_row: dict[str, object] = {
            "scene": row["scene"],
            "model": row["model"],
            "backbone": backbone,
            "method": method,
            "schedule": row["schedule"],
            "seed": row["seed"],
            "final_score": round(final_score, 4),
            "delta_vs_no_robot": round(final_score - baseline, 4),
            **computed,
        }
        output_rows.append(result_row)
        by_method[method].append(result_row)

    output_rows.sort(key=lambda item: (str(item["scene"]), str(item["model"]), str(item["schedule"]), str(item["seed"])))

    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "scene",
                "model",
                "backbone",
                "method",
                "schedule",
                "seed",
                "final_score",
                "delta_vs_no_robot",
                "总动作数",
                "启动任务实例数",
                "完成任务实例数_代理",
                "阶段完成率_代理",
                "局部固着率",
                "过早切换次数",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    lines: list[str] = []
    lines.append("# 800-step 诊断指标 V2\n")
    lines.append(f"- 输入：`{INVENTORY_CSV.relative_to(ROOT)}` 中的 75 个 `with_robot` run")
    lines.append(f"- 输出：`{OUTPUT_CSV.relative_to(ROOT)}`\n")
    lines.append("## 指标定义\n")
    lines.append("1. `阶段完成率（代理）`：以 `active_goal.task` 为任务实例；任务从出现到消失，且消失前未进入 stale drop（`steps_without_progress < 12`），记为一次代理完成。")
    lines.append("2. `局部固着率`：单条轨迹里最常见 `(action, target)` 对的出现次数，占全部机器人动作的比例。")
    lines.append("3. `过早切换次数`：`active_goal.task` 从任务 A 直接切到任务 B，且中间没有回到空任务状态，记为一次过早切换代理。")
    lines.append("4. `reactive` 方法通常没有 `active_goal`，因此前两项任务级指标会天然更弱；这属于日志语义限制，不代表它完全没有任务行为。\n")
    lines.append("## 按方法平均\n")
    lines.append("| 方法 | run 数 | 平均 delta | 平均阶段完成率（代理） | 平均局部固着率 | 平均过早切换次数 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for method in ("reactive", "single_round", "goal_review"):
        method_rows = by_method.get(method, [])
        lines.append(
            "| "
            + " | ".join(
                [
                    method,
                    str(len(method_rows)),
                    format_mean([float(item["delta_vs_no_robot"]) for item in method_rows]),
                    format_mean([float(item["阶段完成率_代理"]) for item in method_rows]),
                    format_mean([float(item["局部固着率"]) for item in method_rows]),
                    format_mean([float(item["过早切换次数"]) for item in method_rows]),
                ]
            )
            + " |"
        )

    best_completion = sorted(output_rows, key=lambda item: (-float(item["阶段完成率_代理"]), -float(item["delta_vs_no_robot"])))[:5]
    worst_fixation = sorted(output_rows, key=lambda item: (-float(item["局部固着率"]), float(item["delta_vs_no_robot"])))[:5]

    lines.append("\n## Top 5：阶段完成率（代理）\n")
    lines.append("| scene | model | schedule | 阶段完成率（代理） | delta |")
    lines.append("|---|---|---|---:|---:|")
    for item in best_completion:
        lines.append(
            f"| {item['scene']} | {item['model']} | {item['schedule']} | {item['阶段完成率_代理']:.4f} | {item['delta_vs_no_robot']:.4f} |"
        )

    lines.append("\n## Top 5：局部固着率最高\n")
    lines.append("| scene | model | schedule | 局部固着率 | delta |")
    lines.append("|---|---|---|---:|---:|")
    for item in worst_fixation:
        lines.append(
            f"| {item['scene']} | {item['model']} | {item['schedule']} | {item['局部固着率']:.4f} | {item['delta_vs_no_robot']:.4f} |"
        )

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_CSV.relative_to(ROOT)}")
    print(f"Wrote {OUTPUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
