"""Turn a PagerDuty-style incident payload into a short, voice-friendly briefing."""

import json
import re
import sys
from pathlib import Path
from typing import Any

from anthropic import Anthropic, APIError

from src.config import PROJECT_ROOT, Settings, load_settings

DEFAULT_INCIDENT_PATH = PROJECT_ROOT / "data" / "incident.json"

MOCK_BRIEFING = (
    "The payments API in production triggered an alert at three twelve AM. "
    "The error rate rose from point two percent to eighteen percent "
    "after version two point fourteen point zero was deployed. "
    "Datadog fired the alert, and charges and refunds are failing, "
    "roughly twelve percent of checkouts. "
    "Logs suggest the card gateway connection pool is exhausted, "
    "so the new version may be the cause. "
    "The previous version, two point thirteen point four, is available for rollback."
)

SUMMARY_SYSTEM_PROMPT = (
    "You write incident briefings that a voice assistant will read aloud to an "
    "on-call engineer woken in the middle of the night.\n"
    "Output exactly 4 short sentences and at most 60 words, in this order:\n"
    "1. What is failing, and where.\n"
    "2. When the alert triggered, and how bad it is.\n"
    "3. A possible cause, framed as a hypothesis.\n"
    "4. The rollback option, if the payload has one.\n"
    "Rules:\n"
    "- Plain spoken text only: no markdown, lists, URLs or incident IDs.\n"
    "- Write every number, version and time in words, the way it is spoken: "
    "'three twelve AM', 'eighteen percent', 'severity one', 'version two point "
    "fourteen point zero'. Never use digits.\n"
    "- Start time: use the time the alert triggered (the incident's created_at). "
    "Do not use the deployment time or other timeline entries as the start, and "
    "do not say the date.\n"
    "- Cause: always a hypothesis, such as 'logs suggest' or 'this may be related "
    "to'. Never state a cause as established fact.\n"
    "- Timezone: do not add one. Name a timezone only if the payload names it "
    "explicitly; never infer a zone name from a UTC offset.\n"
    "- Use only facts in the payload; do not guess."
)


def load_incident(path: Path = DEFAULT_INCIDENT_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return data["incident"]


UTC_OFFSET = re.compile(r"(\d{2}:\d{2}:\d{2})[+-]\d{2}:\d{2}")


def incident_for_prompt(incident: dict[str, Any]) -> str:
    """Serialize the incident for the model with numeric UTC offsets removed.

    The model otherwise infers a zone name (for example "Eastern") from
    "-04:00". Timestamps keep their clock time exactly as written.
    """
    return UTC_OFFSET.sub(r"\1", json.dumps(incident, indent=2))


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
            # A short summary needs no reasoning; with adaptive thinking on, the
            # thinking alone can use up max_tokens and leave no text block.
            # Models that reject "disabled" raise an APIError and use the mock.
            thinking={"type": "disabled"},
            system=SUMMARY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": incident_for_prompt(incident)}],
        )
    except APIError as exc:
        print(f"Anthropic call failed ({exc}); using mock briefing.", file=sys.stderr)
        return MOCK_BRIEFING

    text = "".join(block.text for block in message.content if block.type == "text").strip()
    if not text:
        print(
            f"Anthropic returned no text (stop_reason={message.stop_reason}); "
            "using mock briefing.",
            file=sys.stderr,
        )
        return MOCK_BRIEFING
    return text


if __name__ == "__main__":
    print(summarize(load_incident()))
