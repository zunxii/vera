from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _val = _line.split("=", 1)
            _key = _key.strip()
            _val = _val.strip().strip('"').strip("'")
            if _key and _key not in os.environ:
                os.environ[_key] = _val



@dataclass(frozen=True)
class Settings:
    """
    Application configuration.

    Environment variables can override the defaults.
    """

    app_name: str = "Vera"

    team_name: str = os.getenv(
        "VERA_TEAM_NAME",
        "Junaid",
    )

    team_members: tuple[str, ...] = tuple(
        member.strip()
        for member in os.getenv(
            "VERA_TEAM_MEMBERS",
            "Junaid",
        ).split(",")
        if member.strip()
    )

    groq_api_key: str = os.getenv(
        "GROQ_API_KEY",
        "",
    )

    groq_model: str = os.getenv(
        "GROQ_MODEL",
        "qwen/qwen3.8-27b",
    )

    model: str = os.getenv(
        "VERA_MODEL",
        "qwen/qwen3.8-27b",
    )

    gemini_api_key: str = os.getenv(
        "GEMINI_API_KEY",
        "",
    )

    gemini_model: str = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash",
    )

    approach: str = os.getenv(
        "VERA_APPROACH",
        "4-context architecture with fact selection and Groq high-speed structured-output composition",
    )

    contact_email: str = os.getenv(
        "VERA_CONTACT_EMAIL",
        "",
    )

    version: str = os.getenv(
        "VERA_VERSION",
        "0.3.0",
    )

    submitted_at: str = os.getenv(
        "VERA_SUBMITTED_AT",
        "",
    )
