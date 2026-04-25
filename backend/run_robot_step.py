from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.runtime.agent.robot_agent_runtime import step_robot_agent


DEFAULT_SCENE_DIR = Path(__file__).resolve().parent / "data" / "sg_output" / "simple_graph"


def _scene_path(scene_name: str) -> Path:
    if scene_name.endswith(".json"):
        path = Path(scene_name)
    else:
        path = DEFAULT_SCENE_DIR / f"{scene_name}.json"
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="simple_home_1f")
    parser.add_argument("--model", default="local-llama3.1-8b")
    parser.add_argument("--task", default="Explore the home and keep the world score high.")
    parser.add_argument("--agent-id", default="robot_01")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    scene_path = _scene_path(args.scene)
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    result = step_robot_agent(
        scene,
        task=args.task,
        agent_id=args.agent_id,
        agent_model=args.model,
        timeout=args.timeout,
        advance_step=True,
    )
    payload = {
        "scene": str(scene_path),
        "ok": result.get("ok"),
        "reasoning": result.get("agent_reasoning"),
        "action": result.get("agent_action"),
        "failed_preconds": result.get("failed_preconds"),
        "world_score": ((result.get("scene_metrics") or {}).get("world_metrics") or {}).get("world_score"),
        "game_over": result.get("game_over"),
        "game_over_reason": result.get("game_over_reason"),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
