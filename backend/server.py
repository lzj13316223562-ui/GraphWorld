from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import socket
import time
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.scene_store import SceneStore


WEB_DIR = Path(__file__).resolve().parent.parent / "frontend" / "web"
STORE = SceneStore()
TENSORBOARD_LOGDIR = Path(__file__).resolve().parent / "data" / "tensorboard"
_TENSORBOARD_PROC: subprocess.Popen[str] | None = None
_TENSORBOARD_PORT: int | None = None


def _port_available(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False


def _ensure_tensorboard() -> int:
    global _TENSORBOARD_PROC, _TENSORBOARD_PORT
    if _TENSORBOARD_PROC is not None and _TENSORBOARD_PROC.poll() is None and _TENSORBOARD_PORT is not None:
        return _TENSORBOARD_PORT
    if not shutil.which("tensorboard"):
        raise RuntimeError("tensorboard is not installed or not on PATH")
    TENSORBOARD_LOGDIR.mkdir(parents=True, exist_ok=True)
    port = None
    for candidate in range(6006, 6020):
        if _port_available(candidate):
            port = candidate
            break
    if port is None:
        raise RuntimeError("No free port found for tensorboard (6006-6019)")
    proc = subprocess.Popen(
        [
            "tensorboard",
            "--logdir",
            str(TENSORBOARD_LOGDIR),
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--reload_interval",
            "2",
            "--path_prefix",
            "/tensorboard",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    _TENSORBOARD_PROC = proc
    _TENSORBOARD_PORT = port
    # Give it a moment to bind the port.
    time.sleep(0.15)
    return port


def _ollama_models() -> list[str]:
    fallback = ["local-qwen3.5-35b", "llama3.1:8b"]
    if not shutil.which("ollama"):
        return fallback
    try:
        proc = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except Exception:
        return fallback
    if proc.returncode != 0:
        return fallback
    models: list[str] = []
    for line in (proc.stdout or "").splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        name = parts[0].strip()
        if name and name not in models:
            models.append(name)
    return models or fallback


class GraphworldHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        lang = (query.get("lang") or ["en"])[0]
        if path == "/tensorboard" or path.startswith("/tensorboard/"):
            self._proxy_tensorboard(parsed)
            return
        if path == "/api/scenes":
            self._json({"scenes": STORE.list_scenes(lang=lang)})
            return
        if path.startswith("/api/scene/"):
            scene_id = unquote(path.removeprefix("/api/scene/")).strip("/")
            step_raw = (query.get("step") or [None])[0]
            step = None
            if step_raw is not None:
                try:
                    step = int(step_raw)
                except (TypeError, ValueError):
                    step = None
            payload = STORE.get_scene(scene_id, lang=lang, step_override=step)
            if payload is None:
                self._json({"error": f"Scene not found: {scene_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._json(payload)
            return
        if path == "/api/replays":
            self._json({"replays": STORE.list_replays()})
            return
        if path.startswith("/api/replays/") and path.endswith("/telemetry"):
            replay_id = unquote(path.removeprefix("/api/replays/").removesuffix("/telemetry")).strip("/")
            payload = STORE.get_replay_telemetry(replay_id)
            if payload is None:
                self._json({"error": f"Replay not found: {replay_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._json(payload)
            return
        if path.startswith("/api/human_sessions/") and path.endswith("/scene_view"):
            session_id = unquote(path.removeprefix("/api/human_sessions/").removesuffix("/scene_view")).strip("/")
            payload = STORE.get_human_session_scene_view(session_id)
            if payload is None:
                self._json({"error": f"Human session or scene view not found: {session_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._json(payload)
            return
        if path.startswith("/api/human_sessions/"):
            session_id = unquote(path.removeprefix("/api/human_sessions/")).strip("/")
            payload = STORE.get_human_session(session_id)
            if payload is None:
                self._json({"error": f"Human session not found: {session_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._json(payload)
            return
        if path.startswith("/api/replay/"):
            remainder = unquote(path.removeprefix("/api/replay/")).strip("/")
            if "/step/" in remainder:
                replay_id, step_str = remainder.split("/step/", 1)
                try:
                    step_index = int(step_str)
                except (TypeError, ValueError):
                    self._json({"error": "Invalid step index"}, HTTPStatus.BAD_REQUEST)
                    return
                payload = STORE.get_replay_step(replay_id, step_index)
                if payload is None:
                    self._json({"error": f"Replay or step not found: {replay_id}:{step_index}"}, HTTPStatus.NOT_FOUND)
                    return
                self._json(payload)
                return

            replay_id = remainder
            want_full = (query.get("full") or ["0"])[0] in {"1", "true", "yes"}
            want_summary = (query.get("summary") or ["0"])[0] in {"1", "true", "yes"}
            if want_summary and not want_full:
                payload = STORE.get_replay_summary(replay_id)
            else:
                payload = STORE.get_replay(replay_id)
            if payload is None:
                self._json({"error": f"Replay not found: {replay_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._json(payload)
            return
        if path == "/api/models":
            self._json({"models": _ollama_models()})
            return
        if path == "/api/tensorboard":
            try:
                _ensure_tensorboard()
            except Exception as error:
                self._json({"error": str(error)}, HTTPStatus.SERVICE_UNAVAILABLE)
                return
            self._json({"base_url": "/tensorboard/"})
            return
        if path.startswith("/api/replay_metrics/"):
            replay_id = unquote(path.removeprefix("/api/replay_metrics/")).strip("/")
            payload = STORE.get_replay_metrics(replay_id)
            if payload is None:
                self._json({"error": f"Replay not found: {replay_id}"}, HTTPStatus.NOT_FOUND)
                return
            self._json(payload)
            return
        if path in {"", "/"}:
            self.path = "/index.html"
        super().do_GET()

    def _proxy_tensorboard(self, parsed) -> None:
        try:
            port = _ensure_tensorboard()
            upstream_url = f"http://127.0.0.1:{port}{parsed.path}"
            if parsed.query:
                upstream_url += f"?{parsed.query}"
            req = urllib.request.Request(upstream_url, headers={"User-Agent": "GraphWorld"})
            with urllib.request.urlopen(req, timeout=10) as response:
                body = response.read()
                self.send_response(response.status)
                content_type = response.headers.get("Content-Type")
                if content_type:
                    self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as error:
            self.send_error(error.code, error.reason)
        except Exception as error:
            self._json({"error": f"TensorBoard proxy failed: {error}"}, HTTPStatus.SERVICE_UNAVAILABLE)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/human_sessions/start":
            self._handle_human_start()
            return
        if path.startswith("/api/human_sessions/") and path.endswith("/action"):
            session_id = unquote(path.removeprefix("/api/human_sessions/").removesuffix("/action")).strip("/")
            self._handle_human_action(session_id)
            return
        if path.startswith("/api/human_sessions/") and path.endswith("/end"):
            session_id = unquote(path.removeprefix("/api/human_sessions/").removesuffix("/end")).strip("/")
            self._handle_human_end(session_id)
            return
        if path != "/api/replays/run":
            self._json({"error": f"Unsupported POST path: {path}"}, HTTPStatus.NOT_FOUND)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._json({"error": "Invalid JSON body"}, HTTPStatus.BAD_REQUEST)
            return

        scene_id = str(payload.get("scene_id") or "").strip()
        if not scene_id:
            self._json({"error": "scene_id is required"}, HTTPStatus.BAD_REQUEST)
            return

        replay = STORE.run_replay(
            scene_id,
            task=payload.get("task"),
            agent_id=str(payload.get("agent_id") or "robot_01"),
            agent_model=str(payload.get("agent_model") or "local-qwen3.5-35b"),
            timeout=int(payload.get("timeout") or 30),
            enable_search=bool(payload.get("enable_search", False)),
            image_path=payload.get("image_path"),
            max_days=float(payload.get("max_days") or 1.5),
            experiment_type=str(payload.get("experiment_type") or ""),
        )
        if replay is None:
            self._json({"error": f"Scene not found: {scene_id}"}, HTTPStatus.NOT_FOUND)
            return
        summary = replay.get("summary") or {}
        self._json(
            {
                "replay_id": str(replay.get("replay_id") or ""),
                "scene_id": str(replay.get("scene_id") or scene_id),
                "created_at": str(replay.get("created_at") or ""),
                "summary": {
                    "agent_model": str(summary.get("agent_model") or ""),
                    "experiment_type": str(summary.get("experiment_type") or ""),
                    "experiment_label": str(summary.get("experiment_label") or ""),
                    "run_name": str(summary.get("run_name") or ""),
                    "step_count": int(summary.get("step_count") or 0),
                    "termination_reason": str(summary.get("termination_reason") or ""),
                    "final_world_score": float(summary.get("final_world_score") or 0.0),
                },
            },
            HTTPStatus.CREATED,
        )

    def _read_json_body(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            return json.loads(raw_body.decode("utf-8"))
        except Exception:
            return {}

    def _handle_human_start(self) -> None:
        payload = self._read_json_body()
        scene_id = str(payload.get("scene_id") or "").strip()
        if not scene_id:
            self._json({"error": "scene_id is required"}, HTTPStatus.BAD_REQUEST)
            return
        session = STORE.start_human_session(scene_id, agent_id=str(payload.get("agent_id") or "robot_01"))
        if session is None:
            self._json({"error": f"Scene not found: {scene_id}"}, HTTPStatus.NOT_FOUND)
            return
        self._json(session, HTTPStatus.CREATED)

    def _handle_human_action(self, session_id: str) -> None:
        payload = self._read_json_body()
        session = STORE.apply_human_action(session_id, payload)
        if session is None:
            self._json({"error": f"Human session not found: {session_id}"}, HTTPStatus.NOT_FOUND)
            return
        self._json(session, HTTPStatus.OK)

    def _handle_human_end(self, session_id: str) -> None:
        payload = self._read_json_body()
        session = STORE.end_human_session(session_id, reason=str(payload.get("reason") or "human_stopped"))
        if session is None:
            self._json({"error": f"Human session not found: {session_id}"}, HTTPStatus.NOT_FOUND)
            return
        self._json(session, HTTPStatus.OK)

    def log_message(self, format: str, *args) -> None:
        print(f"[Graphworld] {self.address_string()} - {format % args}")

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9876)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), GraphworldHandler)
    print(f"Graphworld running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Graphworld server...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
