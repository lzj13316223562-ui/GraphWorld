from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
REPLAY_DIR = ROOT / "data" / "replays"


def _load_replay(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _action_name(step: dict[str, Any]) -> str:
    action = step.get("action") or {}
    return str(
        action.get("action_type")
        or action.get("action")
        or action.get("type")
        or "unknown"
    )


def _time_bucket(time_min: int) -> str:
    hour = int(time_min // 60)
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "noon"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def _phase_bucket(index: int, total: int) -> str:
    if total <= 0:
        return "unknown"
    ratio = index / total
    if ratio < 1 / 3:
        return "early"
    if ratio < 2 / 3:
        return "middle"
    return "late"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _world_score(step: dict[str, Any]) -> float:
    scene_metrics = step.get("scene_metrics") or {}
    world_metrics = scene_metrics.get("world_metrics") or {}
    return _safe_float(world_metrics.get("world_score"), _safe_float(step.get("world_score")))


def _human_score(step: dict[str, Any]) -> float:
    scene_metrics = step.get("scene_metrics") or {}
    world_metrics = scene_metrics.get("world_metrics") or {}
    return _safe_float(world_metrics.get("human_score"))


def _top_issues(step: dict[str, Any]) -> list[str]:
    scene_metrics = step.get("scene_metrics") or {}
    issues = scene_metrics.get("top_issues") or []
    if not isinstance(issues, list):
        return []
    return [str(item) for item in issues if str(item).strip()]


def _issue_category(issue_text: str) -> str:
    text = issue_text.lower()
    if "door_" in text or " is open" in text:
        return "door_or_access"
    if "dirty" in text:
        return "cleanliness"
    if "misplaced" in text or "scattered" in text:
        return "orderliness"
    if "standing water" in text or "active" in text:
        return "active_control_or_water"
    if "rotten" in text:
        return "food_decay"
    if "temperature" in text:
        return "comfort"
    if "current activity" in text:
        return "npc_activity"
    return "other"


def _response_actions_for_issue(issue_text: str) -> set[str]:
    text = issue_text.lower()
    if "door_" in text or " is open" in text:
        return {"open", "close", "press"}
    if "dirty" in text:
        return {"brush"}
    if "misplaced" in text or "scattered" in text:
        return {"pick", "place", "open", "close"}
    if "standing water" in text:
        return {"press", "open", "close", "brush"}
    if "active" in text:
        return {"press", "open", "close"}
    if "rotten" in text:
        return {"pick", "place", "close"}
    if "temperature" in text:
        return {"press"}
    return {"pick", "place", "press", "open", "close", "brush"}


def _share_rows(counter: Counter[str], score_rows: dict[str, list[float]], delta_rows: dict[str, list[float]], limit: int | None = None) -> list[dict[str, Any]]:
    total = sum(counter.values()) or 1
    items: Iterable[tuple[str, int]] = counter.most_common(limit) if limit is not None else counter.most_common()
    rows: list[dict[str, Any]] = []
    for action, count in items:
        rows.append(
            {
                "action": action,
                "count": count,
                "share": round(count / total, 4),
                "avg_world_score": round(mean(score_rows.get(action) or [0.0]), 4),
                "avg_next_world_score_delta": round(mean(delta_rows.get(action) or [0.0]), 4),
            }
        )
    return rows


def _issue_windows(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    active: dict[str, int] = {}
    previous_issues: set[str] = set()
    for index, step in enumerate(steps):
        current_issues = set(_top_issues(step))
        appeared = current_issues - previous_issues
        disappeared = previous_issues - current_issues
        for issue in appeared:
            active[issue] = index
        for issue in disappeared:
            start = active.pop(issue, index)
            windows.append({"issue": issue, "start_step": start, "end_step": index - 1})
        previous_issues = current_issues
    if steps:
        last_index = len(steps) - 1
        for issue, start in active.items():
            windows.append({"issue": issue, "start_step": start, "end_step": last_index})
    windows.sort(key=lambda item: (int(item["start_step"]), str(item["issue"])))
    return windows


def _issue_response_table(steps: list[dict[str, Any]], response_window: int = 10) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for window in _issue_windows(steps):
        start_step = int(window["start_step"])
        end_step = int(window["end_step"])
        issue = str(window["issue"])
        start_payload = steps[start_step]
        issue_actions = _response_actions_for_issue(issue)
        action_trace: list[dict[str, Any]] = []
        first_any_response_step: int | None = None
        first_relevant_response_step: int | None = None
        first_relevant_response_action: str | None = None
        resolved_within_window = False
        resolved_step: int | None = None
        max_probe = min(len(steps), start_step + response_window + 1)
        for probe in range(start_step, max_probe):
            action_name = _action_name(steps[probe])
            if action_name != "noop" and first_any_response_step is None and probe > start_step:
                first_any_response_step = probe
            if probe > start_step:
                action_trace.append(
                    {
                        "step": probe,
                        "action": action_name,
                        "world_score": round(_world_score(steps[probe]), 4),
                    }
                )
            if probe > start_step and first_relevant_response_step is None and action_name in issue_actions:
                first_relevant_response_step = probe
                first_relevant_response_action = action_name
            if probe > start_step and issue not in set(_top_issues(steps[probe])):
                resolved_within_window = True
                resolved_step = probe
                break
        rows.append(
            {
                "issue": issue,
                "issue_category": _issue_category(issue),
                "first_seen_step": start_step,
                "last_seen_step": end_step,
                "duration_steps": end_step - start_step + 1,
                "phase": _phase_bucket(start_step, max(len(steps), 1)),
                "time_bucket": _time_bucket(int((((start_payload.get("scene") or {}).get("world_state") or {}).get("time_min") or 0))),
                "world_score_when_seen": round(_world_score(start_payload), 4),
                "human_score_when_seen": round(_human_score(start_payload), 4),
                "expected_response_actions": sorted(issue_actions),
                "first_any_response_step": first_any_response_step,
                "first_relevant_response_step": first_relevant_response_step,
                "first_relevant_response_action": first_relevant_response_action,
                "responded_within_window": first_relevant_response_step is not None,
                "resolved_within_window": resolved_within_window,
                "resolved_step": resolved_step,
                "score_delta_after_window": round(_world_score(steps[min(max_probe - 1, len(steps) - 1)]) - _world_score(start_payload), 4),
                "observed_actions_within_window": action_trace[:10],
            }
        )
    return rows


def _issue_response_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "responded": 0, "resolved": 0})
    for row in rows:
        category = str(row.get("issue_category") or "other")
        grouped[category]["count"] += 1
        grouped[category]["responded"] += 1 if bool(row.get("responded_within_window")) else 0
        grouped[category]["resolved"] += 1 if bool(row.get("resolved_within_window")) else 0
    summary_rows: list[dict[str, Any]] = []
    for category, values in sorted(grouped.items()):
        count = values["count"] or 1
        summary_rows.append(
            {
                "issue_category": category,
                "count": values["count"],
                "responded_within_window": values["responded"],
                "respond_rate": round(values["responded"] / count, 4),
                "resolved_within_window": values["resolved"],
                "resolve_rate": round(values["resolved"] / count, 4),
            }
        )
    return summary_rows


def write_replay_analysis(payload: dict[str, Any], output_path: str | Path | None = None) -> dict[str, Any]:
    report = summarize_replay(payload)
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def summarize_replay(payload: dict[str, Any]) -> dict[str, Any]:
    replay_id = str(payload.get("replay_id") or "")
    scene_id = str(payload.get("scene_id") or "")
    summary = payload.get("summary") or {}
    run = payload.get("run") or {}
    steps = run.get("steps") or []

    action_counts: Counter[str] = Counter()
    actions_by_phase: dict[str, Counter[str]] = defaultdict(Counter)
    actions_by_time: dict[str, Counter[str]] = defaultdict(Counter)
    action_scores: dict[str, list[float]] = defaultdict(list)
    action_score_deltas: dict[str, list[float]] = defaultdict(list)
    world_scores: list[float] = []
    human_scores: list[float] = []

    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        action_name = _action_name(step)
        action_counts[action_name] += 1
        action_scores[action_name].append(_world_score(step))
        current_world_score = _world_score(step)
        next_world_score = _world_score(steps[idx + 1]) if idx + 1 < len(steps) else current_world_score
        action_score_deltas[action_name].append(next_world_score - current_world_score)

        scene = step.get("scene") or {}
        world_state = scene.get("world_state") or {}
        time_min = int(world_state.get("time_min") or 0)
        time_bucket = _time_bucket(time_min)
        phase_bucket = _phase_bucket(idx, max(len(steps), 1))
        actions_by_time[time_bucket][action_name] += 1
        actions_by_phase[phase_bucket][action_name] += 1

        world_scores.append(current_world_score)
        human_scores.append(_human_score(step))

    issue_response_table = _issue_response_table(steps)
    result = {
        "replay_id": replay_id,
        "scene_id": scene_id,
        "experiment_type": str(summary.get("experiment_type") or ""),
        "agent_model": str(summary.get("agent_model") or ""),
        "step_count": int(summary.get("step_count") or len(steps)),
        "terminated": bool(summary.get("terminated", False)),
        "termination_reason": str(summary.get("termination_reason") or ""),
        "final_world_score": _safe_float(summary.get("final_world_score")),
        "avg_world_score": mean(world_scores) if world_scores else 0.0,
        "min_world_score": min(world_scores) if world_scores else 0.0,
        "avg_human_score": mean(human_scores) if human_scores else 0.0,
        "top_actions": _share_rows(action_counts, action_scores, action_score_deltas, limit=8),
        "actions_by_phase": {
            phase: _share_rows(counter, action_scores, action_score_deltas)
            for phase, counter in sorted(actions_by_phase.items())
        },
        "actions_by_time": {
            bucket: _share_rows(counter, action_scores, action_score_deltas)
            for bucket, counter in sorted(actions_by_time.items())
        },
        "issue_response_summary": _issue_response_summary(issue_response_table),
        "issue_response_table": issue_response_table,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(REPLAY_DIR / "experiment_report.json"))
    args = parser.parse_args()
    output_path = Path(args.output)

    replay_paths = sorted(
        path for path in REPLAY_DIR.glob("*.json")
        if not path.name.endswith(".summary.json")
        and not path.name.endswith(".metrics.json")
        and not path.name.endswith(".analysis.json")
        and path.name != output_path.name
    )
    report = [summarize_replay(_load_replay(path)) for path in replay_paths]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
