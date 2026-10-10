from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import anthropic
import httpx2
import pytest

from src.config import Settings
from src.summarize_incident import MOCK_BRIEFING, incident_for_prompt, load_incident, summarize


def make_settings(**overrides: object) -> Settings:
    base = dict(
        elevenlabs_api_key="el-key",
        elevenlabs_agent_id="agent-id",
        anthropic_api_key="sk-test",
        anthropic_model="claude-haiku-5-5",
        use_mock_summary=False,
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_load_incident_has_expected_fields() -> None:
    incident = load_incident()
    assert incident["id"] == "INC-4821"
    assert incident["service"]["name"] == "payments-api"
    assert incident["severity"] == "SEV-1"


@patch("src.summarize_incident.Anthropic")
def test_mock_flag_skips_api(mock_client: MagicMock) -> None:
    result = summarize(load_incident(), make_settings(use_mock_summary=True))
    assert result == MOCK_BRIEFING
    mock_client.assert_not_called()


@patch("src.summarize_incident.Anthropic")
def test_missing_api_key_uses_mock(mock_client: MagicMock) -> None:
    result = summarize(load_incident(), make_settings(anthropic_api_key=None))
    assert result == MOCK_BRIEFING
    mock_client.assert_not_called()


@patch("src.summarize_incident.Anthropic")
def test_live_summary_returns_model_text(mock_client: MagicMock) -> None:
    block = SimpleNamespace(type="text", text="  Payments is down.  ")
    mock_client.return_value.messages.create.return_value = SimpleNamespace(content=[block])

    result = summarize(load_incident(), make_settings())

    assert result == "Payments is down."
    kwargs = mock_client.return_value.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-5-5"


def test_prompt_payload_has_no_utc_offsets() -> None:
    text = incident_for_prompt(load_incident())
    assert "2026-10-07T03:12:00" in text
    assert "-04:00" not in text


@patch("src.summarize_incident.Anthropic")
def test_request_disables_thinking(mock_client: MagicMock) -> None:
    block = SimpleNamespace(type="text", text="ok")
    mock_client.return_value.messages.create.return_value = SimpleNamespace(content=[block])

    summarize(load_incident(), make_settings())

    kwargs = mock_client.return_value.messages.create.call_args.kwargs
    assert kwargs["thinking"] == {"type": "disabled"}


@patch("src.summarize_incident.Anthropic")
def test_empty_text_falls_back_with_warning(
    mock_client: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    thinking_only = SimpleNamespace(type="thinking")
    mock_client.return_value.messages.create.return_value = SimpleNamespace(
        content=[thinking_only], stop_reason="max_tokens"
    )

    assert summarize(load_incident(), make_settings()) == MOCK_BRIEFING
    assert "max_tokens" in capsys.readouterr().err


@patch("src.summarize_incident.Anthropic")
def test_api_error_falls_back_to_mock(mock_client: MagicMock) -> None:
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    mock_client.return_value.messages.create.side_effect = anthropic.APIConnectionError(
        request=request
    )
    assert summarize(load_incident(), make_settings()) == MOCK_BRIEFING
