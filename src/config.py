"""Settings loaded from environment variables / a .env file."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-5-5"


@dataclass(frozen=True)
class Settings:
    elevenlabs_api_key: str | None
    elevenlabs_agent_id: str | None
    anthropic_api_key: str | None
    anthropic_model: str
    use_mock_summary: bool


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY") or None,
        elevenlabs_agent_id=os.getenv("ELEVENLABS_AGENT_ID") or None,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        anthropic_model=os.getenv("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL,
        use_mock_summary=os.getenv("USE_MOCK_SUMMARY", "").strip().lower() == "true",
    )
