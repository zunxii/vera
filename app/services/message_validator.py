from __future__ import annotations

import re

from app.domain.message import MessageBrief
from app.llm.schemas import LLMMessageDraft
from app.services.fact_projector import Fact


class MessageValidator:
    """
    Validate generated text against the deterministic brief.
    """

    ALLOWED_CTAS = {
        "open_ended",
        "binary_yes_no",
        "multi_choice_slot",
        "action",
    }

    URL_RE = re.compile(
        r"https?://|www\.",
        re.IGNORECASE,
    )

    NUMBER_RE = re.compile(
        r"\d+(?:\.\d+)?%?|₹\s?\d+(?:,\d{3})*",
    )

    def validate(
        self,
        *,
        draft: LLMMessageDraft,
        brief: MessageBrief,
        facts: list[Fact],
        taboos: list[str],
    ) -> tuple[bool, list[str]]:

        errors: list[str] = []

        body = draft.body.strip()

        if not body:
            errors.append("empty_body")

        if draft.cta not in self.ALLOWED_CTAS:
            if brief.cta in self.ALLOWED_CTAS:
                # Graceful normalization if model put free-form text in cta field
                object.__setattr__(draft, "cta", brief.cta)
            else:
                errors.append("invalid_cta")

        if self.URL_RE.search(body):
            errors.append("url_not_allowed")

        # The LLM must identify the fact it used.
        fact_ids = {
            fact.id
            for fact in facts
        }

        if (
            brief.primary_fact_id
            not in draft.used_fact_ids
        ):
            if brief.primary_fact_id in fact_ids:
                draft.used_fact_ids.append(brief.primary_fact_id)
            else:
                errors.append(
                    "primary_fact_not_declared"
                )

        unknown_ids = (
            set(draft.used_fact_ids)
            - fact_ids
        )

        if unknown_ids:
            errors.append(
                "unknown_fact_ids"
            )

        body_lower = body.lower()

        for taboo in taboos:

            taboo = str(taboo).strip().lower()

            if taboo and taboo in body_lower:
                errors.append(
                    f"taboo:{taboo}"
                )

        # Ground numerical claims against supplied facts.
        body_numbers = set(
            self.NUMBER_RE.findall(body)
        )

        grounded_numbers = set()

        for fact in facts:
            val_str = fact.value
            matches = self.NUMBER_RE.findall(val_str)
            for m in matches:
                grounded_numbers.add(m)
                grounded_numbers.add(m.replace(" ", ""))
                try:
                    num = float(m.replace("₹", "").replace("%", "").strip())
                    if 0.0 < abs(num) <= 1.0:
                        pct = int(round(abs(num) * 100))
                        grounded_numbers.add(f"{pct}%")
                        grounded_numbers.add(f"{pct}")
                    if num > 0:
                        grounded_numbers.add(f"₹{int(num)}")
                        grounded_numbers.add(f"₹ {int(num)}")
                except ValueError:
                    pass

            date_matches = re.findall(r"\d{4}-\d{2}-\d{2}", val_str)
            for d in date_matches:
                grounded_numbers.add(d)

        unsupported = (
            body_numbers - grounded_numbers
        )

        if unsupported:
            errors.append(
                "unsupported_numbers"
            )

        return (
            not errors,
            errors,
        )
