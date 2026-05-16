from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.runtime.eval.matrix_evaluator import build_matrix_snapshot, scene_nodes


RUN_DIR = ROOT / (
    "backend/data/experiments/simple_home_1f/"
    "steps_1600__robots_0__humans_1__model_npc_only_baseline/"
    "20260513T123622Z_04ec31ee/no_robot"
)
FIG_DIR = ROOT / "paper/figures/overview"
OUT_PNG = FIG_DIR / "home_no_robot_debt_state_score.png"
OUT_MD = ROOT / "paper/analysis/home_no_robot_debt_state_score.md"


def score_on_mask(snapshot, baseline, mask: set[tuple[str, int, str]]) -> tuple[float, int, int]:
    current_index = {node_id: idx for idx, node_id in enumerate(snapshot.node_ids)}
    baseline_index = {node_id: idx for idx, node_id in enumerate(baseline.node_ids)}
    comparable = 0
    different = 0
    for node_id, col_idx, _state in mask:
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


def main() -> None:
    replay = json.loads((RUN_DIR / "replay.json").read_text())
    full_frames = [item for item in replay if scene_nodes(item["scene"])]
    baseline = build_matrix_snapshot(full_frames[0]["scene"])
    baseline_index = {node_id: idx for idx, node_id in enumerate(baseline.node_ids)}

    debt_mask: set[tuple[str, int, str]] = set()
    snapshots = []
    for item in full_frames:
        snapshot = build_matrix_snapshot(item["scene"])
        snapshots.append((int(item["episode_step"]), snapshot))
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
                    debt_mask.add((node_id, col_idx, state_name))

    rows = []
    for step, snapshot in snapshots:
        debt_score, debt_diff, debt_total = score_on_mask(snapshot, baseline, debt_mask)
        full_score, full_diff, full_total = full_state_score(snapshot, baseline)
        rows.append((step, full_score, full_diff, full_total, debt_score, debt_diff, debt_total))

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.plot([row[0] for row in rows], [row[1] for row in rows], marker="o", label="Full state score")
    ax.plot([row[0] for row in rows], [row[4] for row in rows], marker="o", label="Human-debt state score")
    ax.set_xlabel("Step")
    ax.set_ylabel("Instant state score")
    ax.set_ylim(-0.04, 1.04)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    ax.set_title("Home no_robot: full state score vs human-debt state score")
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=220)
    plt.close(fig)

    mask_lines = [
        f"| `{state}` | {count} |" for state, count in sorted(Counter(state for *_prefix, state in debt_mask).items())
    ]
    row_lines = [
        f"| {step} | {full_score:.4f} | {full_diff}/{full_total} | {debt_score:.4f} | {debt_diff}/{debt_total} |"
        for step, full_score, full_diff, full_total, debt_score, debt_diff, debt_total in rows
    ]
    OUT_MD.write_text(
        "\n".join(
            [
                "# Home no_robot Human-Debt State Score",
                "",
                "这个实验只看 no_robot 轨迹里曾经被人类事件或时间流逝扰动过的状态格子。",
                "",
                f"- Debt mask cells: `{len(debt_mask)}`",
                f"- Figure: `{OUT_PNG.relative_to(ROOT)}`",
                "",
                "## Debt Mask By State",
                "",
                "| State | Cells |",
                "| --- | ---: |",
                *mask_lines,
                "",
                "## Score Over Full Scene Frames",
                "",
                "| Step | Full state score | Full diff | Debt state score | Debt diff |",
                "| ---: | ---: | ---: | ---: | ---: |",
                *row_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"wrote {OUT_PNG}")
    print(f"wrote {OUT_MD}")
    print(f"debt mask cells: {len(debt_mask)}")
    for row in rows:
        print(
            f"step={row[0]} full={row[1]:.4f} ({row[2]}/{row[3]}) "
            f"debt={row[4]:.4f} ({row[5]}/{row[6]})"
        )


if __name__ == "__main__":
    main()
