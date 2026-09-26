from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ContextScope = Literal[
    "category",
    "merchant",
    "customer",
    "trigger",
]


class ContextRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    scope: str

    context_id: str = Field(
        min_length=1,
    )

    version: int = Field(
        ge=1,
    )

    payload: dict[str, Any]

    delivered_at: str = Field(
        min_length=1,
    )


class ContextAcceptedResponse(BaseModel):
    accepted: Literal[True]
    ack_id: str
    stored_at: str


class ContextStaleResponse(BaseModel):
    accepted: Literal[False]
    reason: Literal[
        "stale_version"
    ]
    current_version: int


class HealthResponse(BaseModel):
    status: Literal["ok"]

    uptime_seconds: int

    contexts_loaded: dict[str, int]


class MetadataResponse(BaseModel):
    team_name: str
    team_members: list[str]
    model: str
    approach: str
    contact_email: str
    version: str
    submitted_at: str


class TickRequest(BaseModel):
    """
    Request payload sent by the challenge harness during /tick calls.
    """

    now: str = Field(min_length=1)

    available_triggers: list[str] = Field(
        default_factory=list
    )


class TickAction(BaseModel):
    """
    Individual proactive message action returned in /tick response.
    """

    conversation_id: str = Field(min_length=1)

    merchant_id: str = Field(min_length=1)

    customer_id: str | None = None

    send_as: Literal["vera", "merchant_on_behalf"]

    trigger_id: str = Field(min_length=1)

    template_name: str = Field(min_length=1)

    template_params: list[str] = Field(
        default_factory=list
    )

    body: str = Field(min_length=1)

    cta: str = Field(min_length=1)

    suppression_key: str = Field(default="")

    rationale: str = Field(min_length=1)


class TickResponse(BaseModel):
    """
    Response returned by /tick endpoint.
    """

    actions: list[TickAction]


class ReplyRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )

    conversation_id: str = Field(
        min_length=1,
    )

    merchant_id: str = Field(
        min_length=1,
    )

    customer_id: str | None = None

    from_role: Literal[
        "merchant",
        "customer",
    ]

    message: str = Field(
        min_length=1,
        max_length=5000,
    )

    received_at: str = Field(
        min_length=1,
    )

    turn_number: int = Field(
        ge=1,
    )


class ReplyResponse(BaseModel):
    action: Literal[
        "send",
        "wait",
        "end",
    ]

    body: str | None = None

    cta: str | None = None

    wait_seconds: int | None = Field(
        default=None,
        ge=1,
    )

    rationale: str

