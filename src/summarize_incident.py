"""Turn a PagerDuty-style incident payload into a short, voice-friendly briefing."""

import json
import sys
from pathlib import Path
from typing import Any

from anthropic import Anthropic, APIError

from src.config import PROJECT_ROOT, Settings, load_settings

DEFAULT_INCIDENT_PATH = PROJECT_ROOT / "data" / "incident.json"

MOCK_BRIEFING = (
    "Payments API in production started failing at three twelve this morning. "
    "The error rate jumped from point two percent to eighteen percent, "
    "about eight minutes after version two point fourteen point zero was deployed. "
    "Datadog fired the alert, and charges and refunds are failing, "
    "roughly twelve percent of checkouts. "
    "Logs show the card gateway connection pool is exhausted. "
    "The previous version, two point thirteen point four, is available for rollback."
)

SUMMARY_SYSTEM_PROMPT = (
    "You write incident briefings that a voice assistant will read aloud to an "
    "on-call engineer woken in the middle of the night. "
    "Write 4 to 5 short plain sentences, under 90 words. "
    "No markdown, no lists, no URLs, no IDs spelled out. "
    "Write numbers and versions the way they are spoken "
    "(for example 'version two point fourteen point zero', 'eighteen percent'). "
    "Cover: what is failing, since when, how bad, the likely cause, and the "
    "rollback option if one exists. Use only facts in the payload; do not guess."
)


def load_incident(path: Path = DEFAULT_INCIDENT_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data["incident"]


def should_use_mock(settings: Settings) -> bool:
    return settings.use_mock_summary or not settings.anthropic_api_key


def summarize(incident: dict[str, Any], settings: Settings | None = None) -> str:
    """Return the incident_briefing string, falling back to the mock on any API error."""
    settings = settings or load_settings()
    if should_use_mock(settings):
        return MOCK_BRIEFING

    client = Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(incident, indent=2)}],
        )
    except APIError as exc:
        print(f"Anthropic call failed ({exc}); using mock briefing.", file=sys.stderr)
        return MOCK_BRIEFING

    text = "".join(block.text for block in message.content if block.type == "text").strip()
    return text or MOCK_BRIEFING


if __name__ == "__main__":
    print(summarize(load_incident()))
