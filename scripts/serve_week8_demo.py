"""Serve the interactive Week 8 3D mission simulator locally."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shepherd_ai.grounding import load_map_locations  # noqa: E402
from shepherd_ai.interactive_demo import InteractiveMissionDemo  # noqa: E402
from shepherd_ai.safety import load_safety_policy  # noqa: E402


WEB_ROOT = ROOT / "web" / "week8_3d"
DEFAULT_MAP = ROOT / "datasets" / "maps" / "shepherd_test_map_v1.csv"
DEFAULT_FLEET = ROOT / "datasets" / "drones" / "week5_three_drone_fleet_v1.json"
DEFAULT_POLICY = ROOT / "datasets" / "safety" / "week7_safety_policy_v1.json"
MAX_REQUEST_BYTES = 64 * 1024


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    fleet = json.loads(DEFAULT_FLEET.read_text(encoding="utf-8"))
    demo = InteractiveMissionDemo(
        load_map_locations(DEFAULT_MAP),
        fleet,
        load_safety_policy(DEFAULT_POLICY),
    )
    handler = _handler_factory(demo)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Shepherd-AI 3D simulator: http://{args.host}:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _handler_factory(demo: InteractiveMissionDemo):
    class DemoHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

        def do_GET(self) -> None:  # noqa: N802
            if urlparse(self.path).path == "/api/config":
                self._send_json(HTTPStatus.OK, demo.config())
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/api/mission":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "endpoint_not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_REQUEST_BYTES:
                    raise ValueError("request body size is invalid")
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("request body must be a JSON object")
                command = str(payload.get("command", ""))
                resolutions = payload.get("grounding_resolutions", {})
                if not isinstance(resolutions, dict):
                    raise ValueError("grounding_resolutions must be an object")
                result = demo.run(
                    command,
                    grounding_resolutions={str(key): str(value) for key, value in resolutions.items()},
                )
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            except Exception as exc:  # pragma: no cover - server boundary
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "mission_pipeline_failed", "detail": str(exc)},
                )
                return
            self._send_json(HTTPStatus.OK, result)

        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            super().end_headers()

        def _send_json(self, status: HTTPStatus, payload: Any) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status.value)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DemoHandler


if __name__ == "__main__":
    main()
