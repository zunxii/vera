from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComposedMessage:
    body: str
    cta: str
    send_as: str
    template_name: str
    template_params: list[str]
    suppression_key: str
    rationale: str
