from __future__ import annotations

from app.composers.base import BaseComposer
from app.composers.models import ComposedMessage
from app.composers.prompt import build_composer_prompt
from app.domain.context import ContextBundle
from app.policies.triggers import TriggerPolicy
from app.llm.base import BaseLLM
from app.services.fact_projector import Fact
from app.services.validation_service import ValidationService


class LLMComposer(BaseComposer):
    """
    LLM-backed message composer consuming resolved context graph and projected facts.
    """

    def __init__(
        self,
        *,
        llm: BaseLLM,
        validator: ValidationService | None = None,
    ) -> None:
        self.llm = llm
        self.validator = validator or ValidationService()

    def compose(
        self,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
    ) -> ComposedMessage | None:

        voice = context.category.payload.get("voice", {})
        taboos = voice.get("taboos", []) or voice.get("vocab_taboo", [])

        prompt = build_composer_prompt(
            context=context,
            policy=policy,
            facts=facts,
        )

        try:
            draft = self.llm.generate(prompt)
        except Exception:
            return None

        validation = self.validator.validate(
            draft=draft,
            facts=facts,
            taboos=taboos,
        )

        if not validation.valid:
            return None

        trigger = context.trigger.payload
        suppression_key = trigger.get("suppression_key", "")
        send_as = "merchant_on_behalf" if policy.customer_facing else "vera"

        return ComposedMessage(
            body=draft.body.strip(),
            cta=draft.cta,
            send_as=send_as,
            template_name=policy.kind,
            template_params=draft.template_params,
            suppression_key=suppression_key,
            rationale=draft.rationale,
        )
