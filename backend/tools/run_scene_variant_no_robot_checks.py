from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCENES = (
    "simple_home_1f",
    "simple_hospital_1f",
    "simple_supermarket_1f",
    "simple_office_1f",
    "simple_factory_1f",
)
PROFILES = ("compact_cleaning", "normal_logistics", "spread_device")


def humans_for_scene(scene: str) -> int:
    return 1 if scene == "simple_home_1f" else 3


def parse_summary(stdout: str, variant: str) -> dict[str, Any]:
    marker = '{\n  "run_id"'
    start = stdout.rfind(marker)
    if start < 0:
        tail = stdout[-5000:]
        raise RuntimeError(f"could not parse summary for {variant}\n{tail}")
    return json.loads(stdout[start:])


def run_variant(scene: str, profile: str, args: argparse.Namespace) -> dict[str, float]:
    variant = f"{scene}__{profile}"
    cmd = [
        sys.executable,
        "backend/run_experiment.py",
        "--scene",
        variant,
        "--steps",
        str(args.steps),
        "--only",
        "no_robot",
        "--robots",
        "0",
        "--humans",
        str(humans_for_scene(scene)),
        "--no-clean",
        "--replay-scene-interval",
        str(args.replay_scene_interval),
        "--metric-log-interval",
        str(args.metric_log_interval),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode:
        raise RuntimeError(f"{variant} failed with code {proc.returncode}\n{proc.stdout[-5000:]}")
    summary = parse_summary(proc.stdout, variant)
    run = summary["runs"][0]
    metrics = dict(run["final_metrics"])
    metrics.update(curve_stats(Path(run["metrics_csv"])))
    return metrics


def curve_stats(metrics_csv: Path) -> dict[str, float]:
    rows = []
    with metrics_csv.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                rows.append(float(row["final_score"]))
            except (KeyError, TypeError, ValueError):
                continue
    if not rows:
        return {
            "curve_first_final_score": 0.0,
            "curve_last_final_score": 0.0,
            "curve_auc_final_score": 0.0,
            "curve_drop_final_score": 0.0,
        }
    first = rows[0]
    last = rows[-1]
    return {
        "curve_first_final_score": round(first, 4),
        "curve_last_final_score": round(last, 4),
        "curve_auc_final_score": round(sum(rows) / len(rows), 4),
        "curve_drop_final_score": round(first - last, 4),
    }


def check_order(rows: dict[str, dict[str, dict[str, float]]], epsilon: float) -> list[str]:
    failures: list[str] = []
    for scene, by_profile in rows.items():
        compact = by_profile["compact_cleaning"]["final_score"]
        normal = by_profile["normal_logistics"]["final_score"]
        spread = by_profile["spread_device"]["final_score"]
        if compact + epsilon < normal or normal + epsilon < spread:
            failures.append(
                f"{scene}: expected final compact >= normal >= spread, got "
                f"{compact:.4f} >= {normal:.4f} >= {spread:.4f}"
            )
        compact_auc = by_profile["compact_cleaning"]["curve_auc_final_score"]
        normal_auc = by_profile["normal_logistics"]["curve_auc_final_score"]
        spread_auc = by_profile["spread_device"]["curve_auc_final_score"]
        if compact_auc + epsilon < normal_auc or normal_auc + epsilon < spread_auc:
            failures.append(
                f"{scene}: expected AUC compact >= normal >= spread, got "
                f"{compact_auc:.4f} >= {normal_auc:.4f} >= {spread_auc:.4f}"
            )
        compact_drop = by_profile["compact_cleaning"]["curve_drop_final_score"]
        normal_drop = by_profile["normal_logistics"]["curve_drop_final_score"]
        spread_drop = by_profile["spread_device"]["curve_drop_final_score"]
        if compact_drop > normal_drop + epsilon or normal_drop > spread_drop + epsilon:
            failures.append(
                f"{scene}: expected drop compact <= normal <= spread, got "
                f"{compact_drop:.4f} <= {normal_drop:.4f} <= {spread_drop:.4f}"
            )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Run no_robot checks for scene difficulty variants.")
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--epsilon", type=float, default=0.0001)
    parser.add_argument("--metric-log-interval", type=int, default=100)
    parser.add_argument("--replay-scene-interval", type=int, default=100)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()

    if not args.skip_build:
        subprocess.run([sys.executable, "backend/tools/build_scene_variants.py"], cwd=ROOT, check=True)

    rows: dict[str, dict[str, dict[str, float]]] = {}
    for scene in SCENES:
        rows[scene] = {}
        for profile in PROFILES:
            variant = f"{scene}__{profile}"
            print(f"RUN {variant}", flush=True)
            metrics = run_variant(scene, profile, args)
            rows[scene][profile] = metrics
            print(f"{variant} {json.dumps(metrics, ensure_ascii=False, sort_keys=True)}", flush=True)

    print("\nsummary")
    for scene in SCENES:
        scores = " | ".join(
            f"{profile}: final={rows[scene][profile]['final_score']:.4f}, "
            f"auc={rows[scene][profile]['curve_auc_final_score']:.4f}, "
            f"drop={rows[scene][profile]['curve_drop_final_score']:.4f}"
            for profile in PROFILES
        )
        print(f"{scene}: {scores}")

    failures = check_order(rows, args.epsilon)
    if failures:
        print("\nORDER_CHECK_FAILED")
        for item in failures:
            print(f"- {item}")
        raise SystemExit(1)
    print("\nORDER_CHECK_OK")


if __name__ == "__main__":
    main()
