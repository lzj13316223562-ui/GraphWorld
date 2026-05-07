from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path("/opt/data/private/zijian/GraphWorld")
REPLAY_DIR = ROOT / "backend" / "data" / "replays"
OUT_DIR = ROOT / "docs" / "figs" / "replay_analysis"

OLD_ID = "20260423T143129Z_25509adc"
NEW_ID = "20260423T162931Z_39ca225d"
BASELINE_ID = "20260422T120342Z_a0ac37d6"

RUNS = {
    "baseline": BASELINE_ID,
    "before_refactor": OLD_ID,
    "after_refactor": NEW_ID,
}

RUN_LABELS = {
    "baseline": "Baseline (no_robot)",
    "before_refactor": "Before Refactor",
    "after_refactor": "After Refactor",
}

RUN_COLORS = {
    "baseline": "#7f7f7f",
    "before_refactor": "#d95f02",
    "after_refactor": "#1b9e77",
}

ACTION_ORDER = ["move", "pick", "place", "press", "open", "close", "brush"]
ACTION_COLORS = {
    "move": "#4e79a7",
    "pick": "#f28e2b",
    "place": "#e15759",
    "press": "#76b7b2",
    "open": "#edc948",
    "close": "#b07aa1",
    "brush": "#ff9da7",
}

CHANGE_ORDER = [
    "room_cleanliness",
    "room_temperature",
    "food_freshness",
    "resident_activity_mood",
    "plant_vitality",
    "open_close_or_scan",
    "holding_and_carry",
    "object_state_misc",
]

PHASE_COLORS = {
    "Day": "#fff4cc",
    "Night": "#e8eef9",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_metrics_series(replay_id: str):
    obj = load_json(REPLAY_DIR / f"{replay_id}.metrics.json")
    return obj["series"]


def load_steps(replay_id: str):
    obj = load_json(REPLAY_DIR / f"{replay_id}.json")
    return obj["run"]["steps"]


def classify_change(state_key: str, semantic_type: str) -> str:
    if semantic_type == "room" and state_key == "cleanliness":
        return "room_cleanliness"
    if semantic_type == "room" and state_key == "temperature":
        return "room_temperature"
    if state_key == "freshness":
        return "food_freshness"
    if state_key == "vitality":
        return "plant_vitality"
    if state_key in {
        "mood",
        "current_activity",
        "_phase_queue",
        "_phase_backlog",
        "_phase_name",
        "_scheduled_phase",
        "is_home",
    }:
        return "resident_activity_mood"
    if state_key in {"is_open", "isOpen", "pushed", "pulled", "scanned"}:
        return "open_close_or_scan"
    if state_key in {"holding", "handempty", "held_by", "heldBy"}:
        return "holding_and_carry"
    return "object_state_misc"


def clock_to_day_night(clock_minute: int | float | None) -> str:
    if clock_minute is None:
        return "Day"
    minute = int(clock_minute) % (24 * 60)
    return "Day" if 6 * 60 <= minute < 18 * 60 else "Night"


def build_phase_segments(series: list[dict]):
    if not series:
        return []
    segments = []
    current_phase = clock_to_day_night(series[0].get("clock_minute"))
    start_step = series[0]["step"]
    prev_step = start_step
    for item in series[1:]:
        step = item["step"]
        phase = clock_to_day_night(item.get("clock_minute"))
        if phase != current_phase:
            segments.append((start_step, prev_step + 1, current_phase))
            current_phase = phase
            start_step = step
        prev_step = step
    segments.append((start_step, prev_step + 1, current_phase))
    return segments


def add_day_night_background(ax, phase_segments, y_text=0.98):
    for start_step, end_step, phase in phase_segments:
        ax.axvspan(
            start_step - 0.5,
            end_step - 0.5,
            color=PHASE_COLORS[phase],
            alpha=0.28,
            zorder=0,
        )
        mid = (start_step + end_step - 1) / 2
        ax.text(
            mid,
            y_text,
            phase,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=9,
            color="#555555",
        )


def extract_action_records(run_key: str, replay_id: str):
    steps = load_steps(replay_id)
    rows = []
    for step in steps:
        action = step.get("action") or {}
        rows.append(
            {
                "run_key": run_key,
                "run_label": RUN_LABELS[run_key],
                "step": step["episode_step"],
                "action_type": action.get("action", "unknown"),
                "target": action.get("target", ""),
                "ok": step.get("ok", True),
                "world_score": step.get("world_score"),
                "human_score": ((step.get("scene_metrics") or {}).get("world_metrics") or {}).get(
                    "human_score"
                ),
                "resident_mood_score": ((step.get("scene_metrics") or {}).get("world_metrics") or {}).get(
                    "mood_score"
                ),
            }
        )
    return rows


def extract_change_records(run_key: str, replay_id: str):
    steps = load_steps(replay_id)
    prev_nodes = {node["id"]: node for node in steps[0]["scene"]["nodes"]}
    rows = []
    heat = []
    for step in steps[1:]:
        curr_nodes = {node["id"]: node for node in step["scene"]["nodes"]}
        counts = defaultdict(int)
        detail_parts = []
        for node_id, node in curr_nodes.items():
            prev_states = (prev_nodes.get(node_id) or {}).get("states", {}) or {}
            curr_states = node.get("states", {}) or {}
            if prev_states == curr_states:
                continue
            semantic_type = node.get("semantic_type", "unknown")
            for state_key in set(prev_states) | set(curr_states):
                before = prev_states.get(state_key)
                after = curr_states.get(state_key)
                if before == after:
                    continue
                category = classify_change(state_key, semantic_type)
                counts[category] += 1
                detail_parts.append(
                    f"{node_id}:{state_key}({before}->{after})"
                )
        prev_nodes = curr_nodes
        row = {
            "run_key": run_key,
            "run_label": RUN_LABELS[run_key],
            "step": step["episode_step"],
            "action_type": (step.get("action") or {}).get("action", "unknown"),
            "total_state_changes": sum(counts.values()),
            "change_details": " | ".join(detail_parts[:20]),
        }
        for category in CHANGE_ORDER:
            row[category] = counts.get(category, 0)
        rows.append(row)
        heat.append([counts.get(category, 0) for category in CHANGE_ORDER])
    return rows, np.array(heat, dtype=float)


def plot_score_curves(out_dir: Path):
    metrics = {k: load_metrics_series(v) for k, v in RUNS.items()}
    phase_segments = build_phase_segments(metrics["before_refactor"])
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fields = [
        ("world_score", "World Score"),
        ("human_score", "Human Score"),
        ("resident_mood_score", "Resident Mood Score"),
    ]
    for ax, (field, title) in zip(axes, fields):
        add_day_night_background(ax, phase_segments)
        for run_key in ["baseline", "before_refactor", "after_refactor"]:
            series = metrics[run_key]
            steps = [x["step"] for x in series]
            values = [x.get(field) for x in series]
            ax.plot(
                steps,
                values,
                label=RUN_LABELS[run_key],
                color=RUN_COLORS[run_key],
                linewidth=2.2 if run_key != "baseline" else 1.8,
                linestyle="--" if run_key == "baseline" else "-",
                alpha=0.95 if run_key != "baseline" else 0.85,
            )
        ax.set_ylabel(title)
        ax.grid(alpha=0.25, linestyle=":")
        ax.legend(loc="best", frameon=False)
    axes[-1].set_xlabel("Step (day/night segmented)")
    fig.suptitle("Score Curves Across Steps", fontsize=15, y=0.98)
    fig.tight_layout()
    fig.savefig(out_dir / "score_curves_world_human_resident_mood.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_action_timeline(action_rows: list[dict], out_dir: Path):
    phase_segments = build_phase_segments(load_metrics_series(RUNS["before_refactor"]))
    fig, axes = plt.subplots(2, 1, figsize=(15, 7), sharex=True)
    for ax, run_key in zip(axes, ["before_refactor", "after_refactor"]):
        add_day_night_background(ax, phase_segments, y_text=0.96)
        rows = [r for r in action_rows if r["run_key"] == run_key]
        for action_type in ACTION_ORDER:
            xs = [r["step"] for r in rows if r["action_type"] == action_type]
            ys = [ACTION_ORDER.index(action_type)] * len(xs)
            ax.scatter(
                xs,
                ys,
                s=22,
                color=ACTION_COLORS[action_type],
                label=action_type,
                alpha=0.9,
            )
        ax.set_yticks(range(len(ACTION_ORDER)))
        ax.set_yticklabels(ACTION_ORDER)
        ax.set_title(RUN_LABELS[run_key])
        ax.grid(axis="x", alpha=0.18, linestyle=":")
    axes[-1].set_xlabel("Step (day/night segmented)")
    handles, labels = axes[0].get_legend_handles_labels()
    uniq = dict(zip(labels, handles))
    fig.legend(uniq.values(), uniq.keys(), ncol=8, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle("Action Timeline by Step", fontsize=15, y=1.05)
    fig.tight_layout()
    fig.savefig(out_dir / "action_timeline_before_after.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_world_change_timeline(change_heatmaps: dict[str, np.ndarray], out_dir: Path):
    phase_segments = build_phase_segments(load_metrics_series(RUNS["before_refactor"]))
    fig, axes = plt.subplots(2, 1, figsize=(16, 7), sharex=True)
    vmax = max(float(change_heatmaps["before_refactor"].max()), float(change_heatmaps["after_refactor"].max()), 1.0)
    for ax, run_key in zip(axes, ["before_refactor", "after_refactor"]):
        heat = change_heatmaps[run_key].T
        im = ax.imshow(heat, aspect="auto", interpolation="nearest", cmap="YlGnBu", vmin=0, vmax=vmax)
        add_day_night_background(ax, phase_segments, y_text=0.94)
        ax.set_yticks(range(len(CHANGE_ORDER)))
        ax.set_yticklabels(CHANGE_ORDER)
        ax.set_title(RUN_LABELS[run_key])
    axes[-1].set_xlabel("Step (day/night segmented)")
    fig.colorbar(im, ax=axes, fraction=0.016, pad=0.02, label="Changed state count")
    fig.suptitle("World State Changes After Each Step", fontsize=15, y=0.98)
    fig.tight_layout()
    fig.savefig(out_dir / "world_change_timeline_before_after.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    action_rows = []
    for run_key in ["before_refactor", "after_refactor"]:
        action_rows.extend(extract_action_records(run_key, RUNS[run_key]))

    change_rows = []
    change_heatmaps = {}
    for run_key in ["before_refactor", "after_refactor"]:
        rows, heat = extract_change_records(run_key, RUNS[run_key])
        change_rows.extend(rows)
        change_heatmaps[run_key] = heat

    plot_score_curves(OUT_DIR)
    plot_action_timeline(action_rows, OUT_DIR)
    plot_world_change_timeline(change_heatmaps, OUT_DIR)

    write_csv(OUT_DIR / "step_action_table_before_after.csv", action_rows)
    write_csv(OUT_DIR / "step_world_changes_before_after.csv", change_rows)

    print("Wrote plots to", OUT_DIR)


if __name__ == "__main__":
    main()
