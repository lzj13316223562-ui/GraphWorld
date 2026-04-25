from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.replay_store import ReplayStore


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
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()

    scene_path = _scene_path(args.scene)
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    store = ReplayStore()
    replay = store.run_and_save_npc_baseline(
        scene_id=scene_path.stem,
        scene=scene,
        max_days=args.days,
    )
    print(json.dumps({
        "replay_id": replay.get("replay_id"),
        "scene_id": replay.get("scene_id"),
        "summary": replay.get("summary"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
