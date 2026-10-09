"""Local demo server: starts a conversation with the ElevenLabs agent.

The server fetches a signed URL (so the API key never reaches the browser) and
serves a page that starts the session with the four dynamic variables.

Usage:
    python -m src.start_conversation --dry-run   # print the variables, start nothing
    python -m src.start_conversation             # serve http://localhost:8000
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import requests

from src.config import PROJECT_ROOT, Settings, load_settings
from src.summarize_incident import load_incident, summarize

SIGNED_URL_ENDPOINT = "https://api.elevenlabs.io/v1/convai/conversation/get-signed-url"
PAGE_PATH = PROJECT_ROOT / "web" / "index.html"


def build_dynamic_variables(incident: dict[str, Any], briefing: str) -> dict[str, str]:
    service = incident["service"]
    return {
        "incident_id": incident["id"],
        "service": f"{service['name']} ({service['environment']})",
        "severity": incident["severity"],
        "incident_briefing": briefing,
    }


def get_signed_url(settings: Settings) -> str:
    if not settings.elevenlabs_api_key or not settings.elevenlabs_agent_id:
        raise RuntimeError("Set ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID in .env")
    response = requests.get(
        SIGNED_URL_ENDPOINT,
        params={"agent_id": settings.elevenlabs_agent_id},
        headers={"xi-api-key": settings.elevenlabs_api_key},
        timeout=10,
    )
    response.raise_for_status()
    return str(response.json()["signed_url"])


def make_handler(settings: Settings, variables: dict[str, str]) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/":
                self._send(200, PAGE_PATH.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/session":
                try:
                    payload = {
                        "signed_url": get_signed_url(settings),
                        "dynamic_variables": variables,
                    }
                    self._send(200, json.dumps(payload).encode(), "application/json")
                except (RuntimeError, requests.RequestException) as exc:
                    error = json.dumps({"error": str(exc)}).encode()
                    self._send(502, error, "application/json")
            else:
                self._send(404, b"Not found", "text/plain")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print variables and exit")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    settings = load_settings()
    incident = load_incident()
    variables = build_dynamic_variables(incident, summarize(incident, settings))

    if args.dry_run:
        print(json.dumps(variables, indent=2))
        return

    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(settings, variables))
    print(f"Open http://localhost:{args.port}  (Ctrl+C to stop)")
    server.serve_forever()


if __name__ == "__main__":
    main()
