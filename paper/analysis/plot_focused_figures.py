#!/usr/bin/env python3
"""Generate focused experiment-analysis figures.

The script only reads experiment outputs and writes figures under
paper/figures/overview and paper/figures/failure. It does not modify raw
experiment data.
"""

from __future__ import annotations

import csv
import json
import math
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator


ROOT = Path(__file__).resolve().parents[2]
EXP_ROOT = ROOT / "backend" / "data" / "experiments"
FIG_ROOT = ROOT / "paper" / "figures"
OVERVIEW_DIR = FIG_ROOT / "overview"
FAILURE_DIR = FIG_ROOT / "failure"

SCENES = [
    ("simple_home_1f", "Home"),
    ("simple_hospital_1f", "Hospital"),
    ("simple_supermarket_1f", "Supermarket"),
    ("simple_office_1f", "Office"),
    ("simple_factory_1f", "Factory"),
]

SCENE_HUMANS = {
    "simple_home_1f": 1,
    "simple_hospital_1f": 3,
    "simple_supermarket_1f": 3,
    "simple_office_1f": 3,
    "simple_factory_1f": 3,
}

METRICS = [
    ("final_score", "Final"),
    ("state_score", "State"),
    ("spatial_score", "Spatial"),
    ("human_event_score", "Human"),
]

METHODS = [
    ("no_robot", "No robot", "#777777", "--"),
    ("reactive", "Reactive", "#D62728", "-"),
    ("single_round", "Single-round", "#F2B701", "-"),
    ("goal_review", "Goal-review", "#1F77B4", "-"),
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

CASE_ACTION_COLORS = {
    "move": "#7F7F7F",
    "pick": "#1F77B4",
    "place": "#2CA02C",
    "open": "#9467BD",
    "close": "#8C564B",
    "press": "#FF7F0E",
    "fold": "#17BECF",
    "brush": "#D62728",
    "dump": "#BCBD22",
}

CASE_PHASES = [
    (96, 98, "Navigate\n& pick", "#E9EEF7"),
    (99, 102, "Load\nwasher", "#F2EAF7"),
    (103, 107, "Washer\ncycle", "#FFF1D6"),
    (108, 120, "Dry on\nrack", "#E7F4EA"),
    (121, 121, "Fold", "#E2F5F7"),
    (122, 126, "Store in\nwardrobe", "#F7E8E6"),
]

CASE_PATHS = {
    ("simple_factory_1f", "reactive"): (
        "steps_1600__robots_1__humans_3__model_vllm_qwen3_5_9b_reactive",
        "20260511T101301Z_70ccf04f",
        "with_robot",
    ),
    ("simple_hospital_1f", "single_round"): (
        "steps_1600__robots_1__humans_3__model_vllm_qwen3_5_9b_single_round",
        "20260511T090731Z_181d94f3",
        "with_robot",
    ),
}

CASE_SHORT_LABELS = {
    "factory": {
        "cabinet_entrance": "cabinet",
        "workshop": "workshop",
        "assembly_line": "line",
        "button_assembly_line": "line button",
        "break_room": "break room",
        "fridge_break_room": "fridge",
        "table_workshop": "table",
        "machine_workshop": "machine",
        "box_workshop_parts": "parts box",
        "shelf_warehouse": "shelf",
    },
    "hospital": {
        "waiting_area": "waiting",
        "corridor_main": "corridor",
        "outpatient_clinic_1": "clinic",
        "exam_bed_clinic_1": "exam bed",
        "button_outpatient_clinic_1": "clinic button",
        "doctor_coat_staff_room": "doctor coat",
        "door_outpatient_clinic_1": "clinic door",
        "pharmacy": "pharmacy",
        "medicine_fridge_pharmacy": "medicine fridge",
    },
}


def latest(paths: list[Path]) -> Path | None:
    paths = [p for p in paths if p.exists()]
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def find_metrics(scene: str, method: str) -> Path | None:
    scene_dir = EXP_ROOT / scene
    humans = SCENE_HUMANS[scene]
    if method == "no_robot":
        pattern = f"steps_1600__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/metrics.csv"
        return latest(list(scene_dir.glob(pattern)))

    if method in {"reactive", "single_round", "goal_review"}:
        labelled = list(
            scene_dir.glob(
                f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_{method}/*/with_robot/metrics.csv"
            )
        )
        if labelled:
            return latest(labelled)

    if method == "goal_review":
        # Earlier goal-review runs were created before agent_mode was added to
        # the directory name. Keep using them so existing long runs remain useful.
        legacy = list(
            scene_dir.glob(
                f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b/*/with_robot/metrics.csv"
            )
        )
        return latest(legacy)

    return None


def find_replay(scene: str, method: str) -> Path | None:
    scene_dir = EXP_ROOT / scene
    humans = SCENE_HUMANS[scene]
    if method == "no_robot":
        pattern = f"steps_1600__robots_0__humans_{humans}__model_npc_only_baseline/*/no_robot/replay.json"
        return latest(list(scene_dir.glob(pattern)))

    if method in {"reactive", "single_round", "goal_review"}:
        labelled = list(
            scene_dir.glob(
                f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b_{method}/*/with_robot/replay.json"
            )
        )
        if labelled:
            return latest(labelled)

    if method == "goal_review":
        legacy = list(
            scene_dir.glob(
                f"steps_1600__robots_1__humans_{humans}__model_vllm_qwen3_5_9b/*/with_robot/replay.json"
            )
        )
        return latest(legacy)

    return None


def load_runs() -> dict[tuple[str, str], dict]:
    runs: dict[tuple[str, str], dict] = {}
    for scene, _ in SCENES:
        for method, _, _, _ in METHODS:
            path = find_metrics(scene, method)
            if path is None:
                continue
            rows_by_step = {}
            with path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    parsed = dict(row)
                    try:
                        parsed["step"] = float(row.get("step", ""))
                    except ValueError:
                        continue
                    for col, _ in METRICS:
                        try:
                            parsed[col] = float(row.get(col, ""))
                        except ValueError:
                            parsed[col] = float("nan")
                    rows_by_step[int(parsed["step"])] = parsed
            rows = [rows_by_step[k] for k in sorted(rows_by_step)]
            runs[(scene, method)] = {
                "path": path,
                "run_id": path.parents[1].name,
                "rows": rows,
            }
    return runs


def expanded_ylim(values: list[float]) -> tuple[float, float]:
    values = [v for v in values if not math.isnan(v)]
    if not values:
        return 0.0, 1.0
    lo, hi = min(values), max(values)
    if hi - lo < 0.03:
        mid = (hi + lo) / 2
        lo, hi = mid - 0.03, mid + 0.03
    pad = max((hi - lo) * 0.18, 0.02)
    return max(0.0, lo - pad), min(1.02, hi + pad)


def plot_score_curves(runs: dict[tuple[str, str], dict]) -> None:
    fig, axes = plt.subplots(
        nrows=len(METRICS),
        ncols=len(SCENES),
        figsize=(13.5, 9),
        sharex=True,
        constrained_layout=False,
    )
    handles = []
    labels = []

    for c, (scene, scene_name) in enumerate(SCENES):
        for r, (metric, metric_name) in enumerate(METRICS):
            ax = axes[r][c]
            subplot_values: list[float] = []
            for method, method_name, color, linestyle in METHODS:
                run = runs.get((scene, method))
                if run is None:
                    continue
                rows = run["rows"]
                xs = [row["step"] for row in rows]
                ys = [row[metric] for row in rows]
                line = ax.plot(
                    xs,
                    ys,
                    color=color,
                    linestyle=linestyle,
                    linewidth=1.8 if method != "no_robot" else 1.5,
                    alpha=0.95 if method != "no_robot" else 0.8,
                    label=method_name,
                )[0]
                subplot_values.extend(ys)
                if method_name not in labels:
                    handles.append(line)
                    labels.append(method_name)

            ax.set_ylim(*expanded_ylim(subplot_values))
            ax.xaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
            ax.grid(True, color="#E6E6E6", linewidth=0.7)
            if r == 0:
                ax.set_title(scene_name, fontsize=11)
            if c == 0:
                ax.set_ylabel(metric_name, fontsize=11)
            if r == len(METRICS) - 1:
                ax.set_xlabel("Step")

    fig.suptitle("Score curves by scene and metric", fontsize=14, y=0.995)
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.965))
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OVERVIEW_DIR / "score_curves_by_scene_metric.png", dpi=220, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def final_values(runs: dict[tuple[str, str], dict]) -> dict[tuple[str, str], dict[str, float]]:
    out: dict[tuple[str, str], dict[str, float]] = {}
    for key, run in runs.items():
        rows = [
            row
            for row in run["rows"]
            if all(not math.isnan(row.get(metric, float("nan"))) for metric, _ in METRICS)
        ]
        if not rows:
            continue
        row = rows[-1]
        out[key] = {metric: float(row[metric]) for metric, _ in METRICS}
    return out


def radar_axes(fig, rect, labels: list[str]):
    angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
    angles += angles[:1]
    ax = fig.add_subplot(rect, polar=True)
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.5", "0.75", "1.0"], fontsize=8)
    ax.grid(True, color="#E1E1E1")
    return ax, angles


def plot_metric_radar_by_scene(runs: dict[tuple[str, str], dict]) -> None:
    finals = final_values(runs)
    labels = [name for _, name in METRICS]
    fig = plt.figure(figsize=(16, 7))
    legend_handles = []
    legend_labels = []

    for i, (scene, scene_name) in enumerate(SCENES, start=1):
        ax, angles = radar_axes(fig, 230 + i, labels)
        ax.set_title(scene_name, y=1.12, fontsize=12)
        for method, method_name, color, linestyle in METHODS:
            vals = finals.get((scene, method))
            if not vals:
                continue
            series = [vals[metric] for metric, _ in METRICS]
            series += series[:1]
            line = ax.plot(angles, series, color=color, linestyle=linestyle, linewidth=1.8, label=method_name)[0]
            ax.fill(angles, series, color=color, alpha=0.04 if method != "no_robot" else 0.02)
            if method_name not in legend_labels:
                legend_handles.append(line)
                legend_labels.append(method_name)

    fig.legend(legend_handles, legend_labels, loc="upper center", ncol=4, frameon=False)
    fig.suptitle("Final metric radar by scene", y=1.03, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(OVERVIEW_DIR / "final_metric_radar_by_scene.png", dpi=220)
    plt.close(fig)


def plot_final_score_radar_by_method(runs: dict[tuple[str, str], dict]) -> None:
    finals = final_values(runs)
    labels = [name for _, name in SCENES]
    fig = plt.figure(figsize=(8, 8))
    ax, angles = radar_axes(fig, 111, labels)

    for method, method_name, color, linestyle in METHODS:
        series = []
        for scene, _ in SCENES:
            vals = finals.get((scene, method))
            series.append(vals["final_score"] if vals else float("nan"))
        closed = series + series[:1]
        ax.plot(angles, closed, color=color, linestyle=linestyle, linewidth=2.0, label=method_name)
        ax.fill(angles, closed, color=color, alpha=0.04)

    ax.set_title("Final score radar by method", y=1.12, fontsize=15)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.15), frameon=False)
    fig.tight_layout()
    fig.savefig(OVERVIEW_DIR / "final_score_radar_by_method.png", dpi=220)
    plt.close(fig)


def bucket_action(action: str) -> str:
    action = (action or "").strip()
    for bucket, actions in ACTION_BUCKETS:
        if action in actions:
            return bucket
    return "other"


def plot_action_profile_radar(runs: dict[tuple[str, str], dict]) -> None:
    counts: dict[str, Counter] = defaultdict(Counter)
    for (scene, method), run in runs.items():
        if method == "no_robot":
            continue
        for row in run["rows"]:
            action = str(row.get("action", "") or "")
            if action:
                counts[method][bucket_action(action)] += 1

    labels = [bucket for bucket, _ in ACTION_BUCKETS]
    fig = plt.figure(figsize=(8, 8))
    ax, angles = radar_axes(fig, 111, labels)

    for method, method_name, color, linestyle in METHODS:
        if method == "no_robot" or method not in counts:
            continue
        total = sum(counts[method].values()) or 1
        series = [counts[method][bucket] / total for bucket in labels]
        series += series[:1]
        ax.plot(angles, series, color=color, linestyle=linestyle, linewidth=2.0, label=method_name)
        ax.fill(angles, series, color=color, alpha=0.05)

    ax.set_ylim(0, max(0.35, ax.get_ylim()[1]))
    ax.set_title("Robot action profile by method", y=1.12, fontsize=15)
    ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.15), frameon=False)
    fig.tight_layout()
    fig.savefig(OVERVIEW_DIR / "action_profile_radar_by_method.png", dpi=220)
    plt.close(fig)


def case_action_label(action: dict) -> str:
    action_name = str(action.get("action") or "")
    target = str(action.get("target") or "")
    obj = str(action.get("object") or "")
    short = {
        "clothes_bedroom_1": "clothes",
        "washer_bathroom": "washer",
        "drying_rack_balcony": "rack",
        "wardrobe_bedroom": "wardrobe",
        "door_balcony": "balcony door",
        "bedroom": "bedroom",
        "bathroom": "bathroom",
        "living_room": "living room",
        "balcony": "balcony",
    }
    target_label = short.get(target, target.replace("_", " "))
    obj_label = short.get(obj, obj.replace("_", " "))
    if action_name in {"pick", "fold"}:
        label = obj_label or target_label
    elif action_name == "place":
        label = f"{obj_label} -> {target_label}" if obj_label else target_label
    elif action_name == "move":
        label = target_label
    else:
        label = target_label
    return "\n".join(textwrap.wrap(label, width=13))


def event_label(record: dict) -> str:
    events = []
    for item in record.get("event_log") or []:
        event = str(item.get("event") or item.get("activity") or "")
        if event:
            events.append(event)
    return events[0] if events else ""


def contiguous_spans(values: list[tuple[int, str]]) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    start = None
    previous_step = None
    previous_value = ""
    for step, value in values:
        if start is None:
            start = step
            previous_step = step
            previous_value = value
            continue
        if value != previous_value or step != int(previous_step or step) + 1:
            spans.append((int(start), int(previous_step or start), previous_value))
            start = step
        previous_step = step
        previous_value = value
    if start is not None:
        spans.append((int(start), int(previous_step or start), previous_value))
    return spans


def plot_home_laundry_case() -> None:
    replay_path = find_replay("simple_home_1f", "single_round")
    if replay_path is None:
        return
    with replay_path.open(encoding="utf-8") as f:
        records = json.load(f)

    start, end = 96, 126
    window = [record for record in records if start <= int(record.get("episode_step", -1)) <= end]
    if not window:
        return

    action_order = ["move", "open", "close", "press", "pick", "place", "fold", "brush", "dump"]
    action_to_y = {action: idx for idx, action in enumerate(action_order)}
    fig, (event_ax, action_ax) = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(14, 5.6),
        sharex=True,
        gridspec_kw={"height_ratios": [0.72, 4.0], "hspace": 0.08},
    )

    for ax in (event_ax, action_ax):
        for left, right, label, color in CASE_PHASES:
            ax.axvspan(left - 0.5, right + 0.5, color=color, alpha=0.75, zorder=0)
        ax.set_xlim(start - 0.8, end + 0.8)
        ax.grid(axis="x", color="#E7E7E7", linewidth=0.7)

    for left, right, label, _ in CASE_PHASES:
        action_ax.text(
            (left + right) / 2,
            len(action_order) - 0.05,
            label,
            ha="center",
            va="top",
            fontsize=8,
            color="#555555",
        )

    event_spans = contiguous_spans([(int(record.get("episode_step")), event_label(record)) for record in window])
    event_colors = {
        "sleeping": "#B8D8F6",
        "waking_up": "#FAD7A0",
        "getting_dressed": "#D7BDE2",
        "washing_up_morning": "#A9DFBF",
        "breakfast": "#F5B7B1",
        "leaving_home": "#D5DBDB",
    }
    for left, right, label in event_spans:
        if not label:
            continue
        event_ax.barh(
            [0],
            width=right - left + 1,
            left=left - 0.5,
            height=0.55,
            color=event_colors.get(label, "#DDDDDD"),
            edgecolor="white",
            linewidth=0.8,
        )
        event_ax.text((left + right) / 2, 0, label.replace("_", " "), ha="center", va="center", fontsize=8)
    event_ax.set_yticks([])
    event_ax.set_ylabel("Human\nevent", rotation=0, labelpad=34, va="center", fontsize=9)
    event_ax.spines[["left", "right", "top"]].set_visible(False)

    for idx, record in enumerate(window):
        step = int(record.get("episode_step"))
        action = record.get("action") or {}
        action_name = str(action.get("action") or "")
        y = action_to_y.get(action_name, len(action_order) - 1)
        action_ax.scatter(
            [step],
            [y],
            s=95,
            color=CASE_ACTION_COLORS.get(action_name, "#333333"),
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
        label = "" if action_name == "move" else case_action_label(action)
        if label:
            dy = 0.44 if idx % 2 == 0 else -0.44
            va = "bottom" if dy > 0 else "top"
            action_ax.text(step, y + dy, label, ha="center", va=va, fontsize=7.3, color="#333333")

    action_ax.set_yticks(range(len(action_order)))
    action_ax.set_yticklabels(action_order)
    action_ax.set_ylim(-0.7, len(action_order) - 0.05)
    action_ax.set_ylabel("Robot\naction", rotation=0, labelpad=36, va="center", fontsize=9)
    action_ax.set_xlabel("Step")
    action_ax.spines[["right", "top"]].set_visible(False)

    legend_handles = [
        Patch(facecolor=color, edgecolor="none", label=label.replace("\n", " "))
        for _, _, label, color in CASE_PHASES
    ]
    fig.legend(legend_handles, [h.get_label() for h in legend_handles], loc="upper center", ncol=6, frameon=False, fontsize=8, bbox_to_anchor=(0.56, 0.965))
    fig.suptitle("Home laundry case: complete executable skill chain (steps 96-126)", x=0.12, y=0.985, ha="left", fontsize=13)
    fig.text(
        0.01,
        0.01,
        f"Source: {replay_path.relative_to(ROOT)}",
        fontsize=7,
        color="#666666",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.91))
    fig.savefig(FAILURE_DIR / "home_laundry_case_timeline.png", dpi=240, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(FAILURE_DIR / "home_laundry_case_timeline.pdf", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def load_metrics_rows(scene: str, method: str) -> list[dict[str, str]]:
    fixed = CASE_PATHS.get((scene, method))
    if fixed:
        group, run_id, split = fixed
        path = EXP_ROOT / scene / group / run_id / split / "metrics.csv"
        if not path.exists():
            path = find_metrics(scene, method)
    else:
        path = find_metrics(scene, method)
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8") as f:
        rows_by_step = {}
        for row in csv.DictReader(f):
            try:
                rows_by_step[int(float(row.get("step", "")))] = row
            except ValueError:
                continue
        return [rows_by_step[k] for k in sorted(rows_by_step)]


def active_goal_label(active_goal_text: str) -> str:
    try:
        payload = json.loads(active_goal_text or "{}")
    except Exception:
        return ""
    goal = payload.get("robot_01") if isinstance(payload, dict) else None
    if not isinstance(goal, dict):
        return ""
    return str(goal.get("skill") or goal.get("type") or goal.get("task") or "")


def short_target(target: str, label_set: str) -> str:
    table = CASE_SHORT_LABELS.get(label_set, {})
    return table.get(target, str(target or "").replace("_", " "))


def plot_metrics_case(
    *,
    scene: str,
    method: str,
    start: int,
    end: int,
    title: str,
    outfile_stem: str,
    label_set: str,
    phase_spans: list[tuple[int, int, str, str]],
    annotate_actions: set[str] | None = None,
) -> None:
    rows = load_metrics_rows(scene, method)
    window = [row for row in rows if start <= int(row.get("step", -1)) <= end]
    if not window:
        return
    annotate_actions = annotate_actions or {"pick", "place", "open", "close", "press", "brush"}
    action_order = ["move", "open", "close", "press", "pick", "place", "brush", "fold", "dump"]
    action_to_y = {action: idx for idx, action in enumerate(action_order)}
    fig, (event_ax, goal_ax, action_ax, score_ax) = plt.subplots(
        nrows=4,
        ncols=1,
        figsize=(14, 7.0),
        sharex=True,
        gridspec_kw={"height_ratios": [0.55, 0.55, 3.0, 1.05], "hspace": 0.08},
    )
    axes = (event_ax, goal_ax, action_ax, score_ax)
    for ax in axes:
        for left, right, label, color in phase_spans:
            ax.axvspan(left - 0.5, right + 0.5, color=color, alpha=0.72, zorder=0)
        ax.set_xlim(start - 0.8, end + 0.8)
        ax.grid(axis="x", color="#E6E6E6", linewidth=0.7)

    events = [(int(row["step"]), str(row.get("event") or "")) for row in window]
    goals = [(int(row["step"]), active_goal_label(row.get("active_goal", ""))) for row in window]
    event_palette = defaultdict(lambda: "#DDDDDD")
    event_palette.update(
        {
            "factory_off_shift": "#D5DBDB",
            "factory_worker_prepare": "#FAD7A0",
            "factory_load_parts": "#D7BDE2",
            "factory_run_assembly": "#B8D8F6",
            "factory_shift_handover": "#F5B7B1",
            "hospital_away": "#D5DBDB",
            "patient_register": "#FAD7A0",
            "patient_wait": "#E8DAEF",
            "patient_consult": "#B8D8F6",
            "patient_take_medicine": "#F5B7B1",
            "patient_infusion": "#A9DFBF",
            "patient_leave": "#F9E79F",
        }
    )
    for ax, spans, ylabel, palette in (
        (event_ax, contiguous_spans(events), "Human\nevent", event_palette),
        (goal_ax, contiguous_spans(goals), "Active\ngoal", defaultdict(lambda: "#E9EEF7")),
    ):
        has_label = False
        for left, right, label in spans:
            if not label:
                continue
            has_label = True
            ax.barh(
                [0],
                width=right - left + 1,
                left=left - 0.5,
                height=0.55,
                color=palette[label],
                edgecolor="white",
                linewidth=0.8,
            )
            display = label.replace("_", " ")
            if right - left >= 2:
                ax.text((left + right) / 2, 0, display, ha="center", va="center", fontsize=7.5)
        if not has_label and ax is goal_ax:
            ax.text((start + end) / 2, 0, "no active goal", ha="center", va="center", fontsize=8, color="#666666")
        ax.set_yticks([])
        ax.set_ylabel(ylabel, rotation=0, labelpad=38, va="center", fontsize=9)
        ax.spines[["left", "right", "top"]].set_visible(False)

    for idx, row in enumerate(window):
        step = int(row["step"])
        action = str(row.get("action") or "")
        target = str(row.get("target") or "")
        y = action_to_y.get(action, len(action_order) - 1)
        action_ax.scatter(
            [step],
            [y],
            s=86,
            color=CASE_ACTION_COLORS.get(action, "#333333"),
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )
        if action in annotate_actions:
            label = short_target(target, label_set)
            if label:
                dy = 0.42 if idx % 2 == 0 else -0.42
                action_ax.text(
                    step,
                    y + dy,
                    "\n".join(textwrap.wrap(label, width=12)),
                    ha="center",
                    va="bottom" if dy > 0 else "top",
                    fontsize=7.0,
                    color="#333333",
                )

    action_ax.set_yticks(range(len(action_order)))
    action_ax.set_yticklabels(action_order)
    action_ax.set_ylim(-0.7, len(action_order) - 0.15)
    action_ax.set_ylabel("Robot\naction", rotation=0, labelpad=38, va="center", fontsize=9)
    action_ax.spines[["right", "top"]].set_visible(False)

    xs = [int(row["step"]) for row in window]
    final = [float(row["final_score"]) for row in window]
    spatial = [float(row["spatial_score"]) for row in window]
    human = [float(row["human_event_score"]) for row in window]
    score_ax.plot(xs, final, color="#111111", linewidth=1.9, label="final")
    score_ax.plot(xs, spatial, color="#59A14F", linewidth=1.5, label="spatial")
    score_ax.plot(xs, human, color="#E15759", linewidth=1.5, label="human")
    score_ax.set_ylabel("Score", fontsize=9)
    score_ax.set_xlabel("Step")
    score_values = final + spatial + human
    lo, hi = min(score_values), max(score_values)
    pad = max((hi - lo) * 0.18, 0.03)
    score_ax.set_ylim(max(0, lo - pad), min(1.02, hi + pad))
    score_ax.legend(loc="lower left", ncol=3, frameon=False, fontsize=8)
    score_ax.spines[["right", "top"]].set_visible(False)

    legend_handles = [Patch(facecolor=color, edgecolor="none", label=label) for _, _, label, color in phase_spans]
    fig.legend(legend_handles, [h.get_label() for h in legend_handles], loc="upper center", ncol=len(phase_spans), frameon=False, fontsize=8, bbox_to_anchor=(0.56, 0.955))
    fig.suptitle(title, x=0.12, y=0.985, ha="left", fontsize=13)
    fig.tight_layout(rect=(0, 0.02, 1, 0.91))
    fig.savefig(FAILURE_DIR / f"{outfile_stem}.png", dpi=240, bbox_inches="tight", pad_inches=0.04)
    fig.savefig(FAILURE_DIR / f"{outfile_stem}.pdf", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def plot_failure_case_timelines() -> None:
    plot_metrics_case(
        scene="simple_factory_1f",
        method="reactive",
        start=0,
        end=80,
        title="Factory reactive failure: legal local actions do not restore production resources",
        outfile_stem="factory_reactive_failure_timeline",
        label_set="factory",
        phase_spans=[
            (0, 10, "Cabinet toggle", "#E9EEF7"),
            (11, 29, "Resource debt emerges", "#F7E8E6"),
            (30, 65, "Fridge / line loop", "#FFF1D6"),
            (66, 80, "Persistent idle loop", "#E7F4EA"),
        ],
        annotate_actions={"pick", "press", "brush"},
    )
    plot_metrics_case(
        scene="simple_hospital_1f",
        method="single_round",
        start=18,
        end=45,
        title="Hospital single-round failure: active goal persists while spatial debt grows",
        outfile_stem="hospital_single_round_failure_timeline",
        label_set="hospital",
        phase_spans=[
            (18, 21, "Clean bed starts", "#E7F4EA"),
            (22, 30, "Goal/action mismatch", "#F7E8E6"),
            (31, 45, "Loop without closure", "#FFF1D6"),
        ],
        annotate_actions={"pick", "open", "brush"},
    )


def write_summary_csv(runs: dict[tuple[str, str], dict]) -> None:
    finals = final_values(runs)
    out_path = OVERVIEW_DIR / "final_scores_summary.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "scene",
                "method",
                "run_id",
                "final_score",
                "state_score",
                "spatial_score",
                "human_event_score",
                "metrics_path",
            ]
        )
        for scene, _ in SCENES:
            for method, _, _, _ in METHODS:
                vals = finals.get((scene, method))
                run = runs.get((scene, method))
                if not vals or not run:
                    continue
                writer.writerow(
                    [
                        scene,
                        method,
                        run["run_id"],
                        f"{vals['final_score']:.4f}",
                        f"{vals['state_score']:.4f}",
                        f"{vals['spatial_score']:.4f}",
                        f"{vals['human_event_score']:.4f}",
                        run["path"].relative_to(ROOT),
                    ]
                )


def main() -> None:
    OVERVIEW_DIR.mkdir(parents=True, exist_ok=True)
    FAILURE_DIR.mkdir(parents=True, exist_ok=True)
    runs = load_runs()
    plot_score_curves(runs)
    plot_metric_radar_by_scene(runs)
    plot_final_score_radar_by_method(runs)
    plot_action_profile_radar(runs)
    plot_home_laundry_case()
    plot_failure_case_timelines()
    write_summary_csv(runs)

    print("Loaded runs:")
    for scene, scene_name in SCENES:
        available = [method for method, _, _, _ in METHODS if (scene, method) in runs]
        print(f"- {scene_name}: {', '.join(available)}")
    print(f"Wrote overview figures to {OVERVIEW_DIR}")
    print(f"Wrote failure figures to {FAILURE_DIR}")


if __name__ == "__main__":
    main()
