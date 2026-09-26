from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.llm.schemas import LLMMessageDraft
from app.services.fact_projector import Fact


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]


class ValidationService:
    """
    Validates generated messages before they leave the system.
    """

    MAX_LENGTH = 900
    URL_REGEX = re.compile(r"https?://|www\.", re.IGNORECASE)

    VALID_CTAS = {
        "open_ended",
        "binary_yes_no",
        "multi_choice_slot",
        "action",
        "binary_confirm_cancel",
        "none",
    }

    def validate(
        self,
        draft: LLMMessageDraft,
        facts: list[Fact],
        taboos: list[str],
    ) -> ValidationResult:

        errors: list[str] = []

        body = draft.body.strip()

        # -----------------------------------------------------
        # Basic checks
        # -----------------------------------------------------

        if not body:
            errors.append("empty_body")

        if len(body) > self.MAX_LENGTH:
            errors.append("body_too_long")

        if self.URL_REGEX.search(body):
            errors.append("contains_url")

        if not draft.cta.strip():
            errors.append("empty_cta")

        # -----------------------------------------------------
        # Fact IDs check
        # -----------------------------------------------------

        fact_ids = {fact.id for fact in facts}

        if draft.used_fact_ids:
            unknown_fact_ids = set(draft.used_fact_ids) - fact_ids
            if unknown_fact_ids:
                errors.append(
                    "unknown_fact_ids:" + ",".join(sorted(unknown_fact_ids))
                )

        # -----------------------------------------------------
        # Taboos check
        # -----------------------------------------------------

        body_lower = body.lower()

        for taboo in taboos:
            taboo_str = str(taboo).strip().lower()
            if not taboo_str:
                continue
            if taboo_str in body_lower:
                errors.append(f"taboo:{taboo_str}")

        # -----------------------------------------------------
        # Number grounding
        # -----------------------------------------------------

        body_numbers = set(re.findall(r"\d+(?:\.\d+)?", body))
        fact_numbers: set[str] = set()

        for fact in facts:
            fact_numbers.update(re.findall(r"\d+(?:\.\d+)?", fact.value))

        unsupported_numbers = body_numbers - fact_numbers

        if unsupported_numbers:
            errors.append(
                "unsupported_numbers:" + ",".join(sorted(unsupported_numbers))
            )

        # -----------------------------------------------------
        # Length check
        # -----------------------------------------------------

        if len(body.split()) < 5:
            errors.append("message_too_short")

        return ValidationResult(
            valid=not errors,
            errors=errors,
        )

    @classmethod
    def validate_action(cls, action: dict[str, Any]) -> bool:
        body = action.get("body", "")
        if not body or not body.strip():
            return False

        if cls.URL_REGEX.search(body):
            return False

        required_keys = [
            "conversation_id",
            "merchant_id",
            "send_as",
            "trigger_id",
            "template_name",
            "template_params",
            "cta",
            "rationale",
        ]
        for key in required_keys:
            if key not in action or action[key] is None:
                return False

        return True
