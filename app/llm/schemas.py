from __future__ import annotations

from pydantic import BaseModel, Field


class LLMMessageDraft(BaseModel):
    """
    Structured response expected from the LLM.

    Everything else, such as send_as, suppression_key,
    trigger_id, etc. is controlled by our application.
    """

    body: str = Field(
        min_length=1,
        max_length=1000,
        description="The WhatsApp message body.",
    )

    cta: str = Field(
        min_length=1,
        max_length=100,
        description="One clear call to action.",
    )

    used_fact_ids: list[str] = Field(
        default_factory=list,
        description=(
            "IDs of supplied facts actually used "
            "in the message."
        ),
    )

    template_params: list[str] = Field(
        default_factory=list,
        description=(
            "Template parameters needed by the message."
        ),
    )

    rationale: str = Field(
        min_length=1,
        max_length=500,
        description=(
            "Brief explanation of why this message "
            "is relevant now."
        ),
    )
