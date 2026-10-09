from unittest.mock import MagicMock, patch

import pytest

from src.config import Settings
from src.start_conversation import SIGNED_URL_ENDPOINT, build_dynamic_variables, get_signed_url
from src.summarize_incident import load_incident


def make_settings(api_key: str | None = "el-key", agent_id: str | None = "agent-id") -> Settings:
    return Settings(api_key, agent_id, None, "claude-haiku-5-5", True)


def test_dynamic_variables_have_exactly_the_four_agent_keys() -> None:
    variables = build_dynamic_variables(load_incident(), "briefing text")
    assert variables == {
        "incident_id": "INC-4821",
        "service": "payments-api (production)",
        "severity": "SEV-1",
        "incident_briefing": "briefing text",
    }


@patch("src.start_conversation.requests.get")
def test_get_signed_url_calls_documented_endpoint(mock_get: MagicMock) -> None:
    mock_get.return_value.json.return_value = {"signed_url": "wss://example.test/abc"}

    assert get_signed_url(make_settings()) == "wss://example.test/abc"

    args, kwargs = mock_get.call_args
    assert args[0] == SIGNED_URL_ENDPOINT
    assert kwargs["params"] == {"agent_id": "agent-id"}
    assert kwargs["headers"] == {"xi-api-key": "el-key"}


@patch("src.start_conversation.requests.get")
def test_get_signed_url_error_includes_body_but_not_key(mock_get: MagicMock) -> None:
    mock_get.return_value.ok = False
    mock_get.return_value.status_code = 401
    mock_get.return_value.text = '{"detail": {"status": "missing_permissions", "key": "el-key"}}'

    with pytest.raises(RuntimeError) as exc_info:
        get_signed_url(make_settings())

    message = str(exc_info.value)
    assert "401" in message and "missing_permissions" in message
    assert "el-key" not in message


@patch("src.start_conversation.requests.get")
def test_get_signed_url_requires_credentials(mock_get: MagicMock) -> None:
    with pytest.raises(RuntimeError):
        get_signed_url(make_settings(api_key=None))
    mock_get.assert_not_called()
