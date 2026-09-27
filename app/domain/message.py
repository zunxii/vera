from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MessageBrief:
    """
    Small, deterministic representation of what the message
    should communicate.
    """

    audience: str
    merchant_name: str
    customer_name: str | None

    trigger_kind: str
    trigger_family: str

    primary_fact_id: str
    primary_fact: str

    supporting_facts: tuple[str, ...]

    cta: str
    engagement_levers: tuple[str, ...]

    instruction: str
    language_pref: str = "en"


@dataclass(frozen=True)
class ComposedMessage:
    body: str
    cta: str
    send_as: str
    template_name: str
    template_params: list[str]
    suppression_key: str
    rationale: str
