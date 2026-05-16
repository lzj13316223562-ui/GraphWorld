from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.runtime.eval.matrix_evaluator import build_matrix_snapshot

RUN_BASE = (
    ROOT
    / "backend/data/experiments/simple_home_1f/"
    / "steps_1600__robots_0__humans_1__model_npc_only_baseline"
)
FIG_DIR = ROOT / "paper/figures/overview"
OUT_PNG = FIG_DIR / "home_no_robot_step1599_state_matrix.png"
OUT_MD = ROOT / "paper/analysis/home_no_robot_step1599_state_matrix.md"


def main() -> None:
    run_dirs = [path for path in RUN_BASE.glob("*/no_robot") if (path / "replay.json").exists()]
    if not run_dirs:
        raise FileNotFoundError(f"No replay found under {RUN_BASE}")
    run_dir = max(run_dirs, key=lambda path: path.stat().st_mtime)
    replay_path = run_dir / "replay.json"
    replay = json.loads(replay_path.read_text())
    baseline_scene = replay[0]["scene"]
    current_scene = replay[-1]["scene"]
    step = int(replay[-1]["episode_step"])

    baseline = build_matrix_snapshot(baseline_scene)
    current = build_matrix_snapshot(current_scene)
    baseline_index = {node_id: idx for idx, node_id in enumerate(baseline.node_ids)}

    row_labels: list[str] = []
    heat: list[list[int]] = []
    cell_text: list[list[str]] = []
    comparable = 0
    different = 0
    diff_rows: list[tuple[str, str, object, object]] = []
    by_state: dict[str, list[int]] = {}

    for current_idx, node_id in enumerate(current.node_ids):
        baseline_idx = baseline_index.get(node_id)
        if baseline_idx is None:
            continue

        row: list[int] = []
        labels: list[str] = []
        has_any_state = False
        for col_idx, state_name in enumerate(current.state_columns):
            value = current.state_matrix[current_idx][col_idx]
            expected = baseline.state_matrix[baseline_idx][col_idx]
            if value is None or expected is None:
                row.append(0)
                labels.append("")
                continue

            has_any_state = True
            comparable += 1
            by_state.setdefault(state_name, [0, 0])
            by_state[state_name][1] += 1
            if value == expected:
                row.append(1)
                labels.append(str(value))
            else:
                row.append(2)
                labels.append(f"{expected}->{value}")
                different += 1
                by_state[state_name][0] += 1
                diff_rows.append((node_id, state_name, expected, value))

        if has_any_state:
            row_labels.append(node_id)
            heat.append(row)
            cell_text.append(labels)

    state_score = 1.0 - different / comparable if comparable else 1.0

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_width = max(11, len(current.state_columns) * 0.72)
    fig_height = max(7, len(row_labels) * 0.23)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    cmap = ListedColormap(["#f2f2f2", "#5cb85c", "#d9534f"])
    ax.imshow(heat, cmap=cmap, vmin=0, vmax=2, aspect="auto")

    ax.set_xticks(range(len(current.state_columns)))
    ax.set_xticklabels(current.state_columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=7)
    ax.set_title(
        f"Home no_robot step {step}: state matrix vs initial "
        f"({comparable - different}/{comparable} matched, score={state_score:.4f})",
        fontsize=12,
        pad=10,
    )

    for y, row in enumerate(heat):
        for x, value in enumerate(row):
            if value == 2:
                ax.text(x, y, cell_text[y][x], ha="center", va="center", fontsize=5.2, color="white")

    ax.set_xlabel("Discrete state")
    ax.set_ylabel("Node")
    ax.grid(which="major", color="white", linewidth=0.35)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=220)
    plt.close(fig)

    by_state_lines = [
        f"| `{state}` | {diff_total[0]} | {diff_total[1]} |"
        for state, diff_total in sorted(by_state.items(), key=lambda item: (-item[1][0], item[0]))
    ]
    diff_lines = [
        f"| `{node_id}` | `{state}` | `{expected}` | `{value}` |"
        for node_id, state, expected, value in diff_rows
    ]
    OUT_MD.write_text(
        "\n".join(
            [
                "# Home no_robot Step 1599 State Matrix Example",
                "",
                f"- Run: `{run_dir.parent.name}`",
                f"- Step: `{step}`",
                f"- Comparable state cells: `{comparable}`",
                f"- Different state cells: `{different}`",
                f"- Formula: `state_score = 1 - different / comparable = 1 - {different}/{comparable} = {state_score:.4f}`",
                f"- Figure: `{OUT_PNG.relative_to(ROOT)}`",
                "",
                "颜色含义：白色是不参与比较的空状态，绿色是当前值等于初始值，红色是当前值不同于初始值。",
                "",
                "## Diff By State",
                "",
                "| State | Different | Comparable |",
                "| --- | ---: | ---: |",
                *by_state_lines,
                "",
                "## Different Cells",
                "",
                "| Node | State | Initial | Step 1599 |",
                "| --- | --- | ---: | ---: |",
                *diff_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"wrote {OUT_PNG}")
    print(f"wrote {OUT_MD}")
    print(f"state_score = 1 - {different}/{comparable} = {state_score:.4f}")


if __name__ == "__main__":
    main()
