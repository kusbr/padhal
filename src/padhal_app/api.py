from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .services import PadhalService


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
SERVICE = PadhalService()


def parse_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


class PadhalAPIHandler(BaseHTTPRequestHandler):
    server_version = "PadhalAPI/1.0"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_common_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]

        if parsed.path in {"/", "/index.html"}:
            self._write_file(STATIC_DIR / "index.html", content_type="text/html; charset=utf-8")
            return

        if parsed.path == "/app.js":
            self._write_file(STATIC_DIR / "app.js", content_type="application/javascript; charset=utf-8")
            return

        if len(parts) == 3 and parts[:2] == ["api", "games"]:
            try:
                game = SERVICE.get_game(parts[2])
            except KeyError:
                self._write_json({"error": "Game not found."}, status=HTTPStatus.NOT_FOUND)
                return
            self._write_json(game.to_dict())
            return

        self._write_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        parts = [part for part in parsed.path.split("/") if part]

        try:
            payload = parse_json_body(self)
        except json.JSONDecodeError:
            self._write_json({"error": "Invalid JSON body."}, status=HTTPStatus.BAD_REQUEST)
            return

        if parts == ["api", "games"]:
            try:
                game = SERVICE.create_game(
                    starts_with=payload.get("starts_with"),
                    part_of_speech=payload.get("part_of_speech"),
                )
            except RuntimeError as exc:
                self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_GATEWAY)
                return
            self._write_json(game.to_dict(), status=HTTPStatus.CREATED)
            return

        if len(parts) == 4 and parts[:2] == ["api", "games"] and parts[3] == "guesses":
            try:
                response = SERVICE.submit_guess(parts[2], str(payload.get("guess", "")))
            except KeyError:
                self._write_json({"error": "Game not found."}, status=HTTPStatus.NOT_FOUND)
                return
            except ValueError as exc:
                self._write_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._write_json(response)
            return

        self._write_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_common_headers(self) -> None:
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._send_common_headers()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._write_json({"error": "Not found."}, status=HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    with ThreadingHTTPServer((host, port), PadhalAPIHandler) as server:
        print(f"Padhal API listening on http://{host}:{port}")
        server.serve_forever()
