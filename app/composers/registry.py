from __future__ import annotations

from app.composers.base import BaseComposer
from app.composers.models import ComposedMessage
from app.domain.context import ContextBundle
from app.policies.triggers import TriggerPolicy
from app.services.fact_projector import Fact


class FallbackComposer(BaseComposer):
    """
    Fallback composer producing deterministic messages from facts when LLM is unavailable.
    """

    def compose(
        self,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
    ) -> ComposedMessage | None:
        trigger = context.trigger.payload
        merchant = context.merchant.payload
        suppression_key = trigger.get("suppression_key", "")

        if policy.customer_facing:
            if context.customer is None:
                return None
            customer = context.customer.payload
            customer_name = (
                customer.get("identity", {}).get("name")
                or customer.get("identity", {}).get("first_name")
                or "there"
            )
            merchant_name = (
                merchant.get("identity", {}).get("name", "our clinic")
            )
            body = (
                f"Hi {customer_name}, {merchant_name} here. "
                f"Checking in regarding your recent visit."
            )
            return ComposedMessage(
                body=body,
                cta=policy.cta,
                send_as="merchant_on_behalf",
                template_name=policy.kind,
                template_params=[customer_name, merchant_name],
                suppression_key=suppression_key,
                rationale=f"Fallback composer for customer trigger kind '{policy.kind}'.",
            )

        owner_name = (
            merchant.get("identity", {}).get("owner_first_name")
            or merchant.get("identity", {}).get("name")
            or "there"
        )
        business = merchant.get("identity", {}).get("name", "your business")

        body = (
            f"Hi {owner_name}, there is an update regarding {business} ({policy.kind}). "
            f"Would you like me to unpack what it means for you?"
        )
        return ComposedMessage(
            body=body,
            cta=policy.cta,
            send_as="vera",
            template_name=policy.kind,
            template_params=[owner_name, business],
            suppression_key=suppression_key,
            rationale=f"Fallback composer for merchant trigger kind '{policy.kind}'.",
        )


class ComposerRegistry:
    """
    Registry that dispatches composition to LLMComposer first (if available),
    and falls back to FallbackComposer.
    """

    def __init__(self, llm_composer: BaseComposer | None = None) -> None:
        self.llm_composer = llm_composer
        self.fallback = FallbackComposer()

    def compose(
        self,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
    ) -> ComposedMessage | None:
        if self.llm_composer is not None:
            try:
                result = self.llm_composer.compose(context, policy, facts)
                if result is not None:
                    return result
            except Exception:
                pass

        return self.fallback.compose(context, policy, facts)
