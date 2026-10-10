import json
import threading
import urllib.request
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from unittest.mock import MagicMock, patch

import pytest

from src.config import Settings
from src.start_conversation import make_handler

VARIABLES = {
    "incident_id": "INC-4821",
    "service": "payments-api (production)",
    "severity": "SEV-1",
    "incident_briefing": "briefing text",
}


@pytest.fixture
def base_url() -> Iterator[str]:
    settings = Settings("el-key", "agent-id", None, "claude-haiku-5-5", True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(settings, VARIABLES))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@patch("src.start_conversation.get_signed_url")
def test_incident_endpoint_returns_variables_without_signed_url(
    mock_signed_url: MagicMock, base_url: str
) -> None:
    with urllib.request.urlopen(f"{base_url}/api/incident") as response:
        assert json.load(response) == VARIABLES
    mock_signed_url.assert_not_called()


@patch("src.start_conversation.get_signed_url", return_value="wss://example.test/abc")
def test_session_endpoint_returns_only_signed_url(
    mock_signed_url: MagicMock, base_url: str
) -> None:
    with urllib.request.urlopen(f"{base_url}/api/session") as response:
        assert json.load(response) == {"signed_url": "wss://example.test/abc"}
