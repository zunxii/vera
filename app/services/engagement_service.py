from __future__ import annotations

from app.domain.context import ContextBundle
from app.domain.message import (
    ComposedMessage,
    MessageBrief,
)
from app.domain.signal import SignalSelection
from app.llm.base import BaseLLM
from app.policies.triggers import TriggerPolicy
from app.prompts.engagement import build_prompt
from app.services.fact_projector import Fact
from app.services.message_validator import (
    MessageValidator,
)


class EngagementService:
    """
    The single message composition service used by both
    proactive /tick and reactive /reply flows.
    """

    TEMPLATE_NAME = "vera_engagement_v1"

    def __init__(
        self,
        *,
        llm: BaseLLM,
        validator: MessageValidator,
    ) -> None:

        self.llm = llm
        self.validator = validator

    def compose(
        self,
        *,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
        signal: SignalSelection,
    ) -> ComposedMessage | None:

        brief = self._build_brief(
            context=context,
            policy=policy,
            facts=facts,
            signal=signal,
        )

        prompt = build_prompt(
            context=context,
            brief=brief,
            facts=facts,
        )

        try:
            draft = self.llm.generate(
                prompt
            )
        except Exception:
            return self._fallback(
                context=context,
                policy=policy,
                facts=facts,
                signal=signal,
                brief=brief,
            )

        voice = context.category.payload.get(
            "voice",
            {},
        )

        taboo = voice.get(
            "vocab_taboo",
            voice.get(
                "taboos",
                [],
            ),
        )

        valid, _errors = (
            self.validator.validate(
                draft=draft,
                brief=brief,
                facts=facts,
                taboos=taboo,
            )
        )

        if not valid:
            return self._fallback(
                context=context,
                policy=policy,
                facts=facts,
                signal=signal,
                brief=brief,
            )

        return ComposedMessage(
            body=draft.body.strip(),
            cta=draft.cta,
            send_as=(
                "merchant_on_behalf"
                if context.customer
                else "vera"
            ),
            template_name=self.TEMPLATE_NAME,
            template_params=list(
                draft.template_params
            ),
            suppression_key=(
                context.trigger.payload.get(
                    "suppression_key",
                    "",
                )
            ),
            rationale=draft.rationale,
        )

    def _build_brief(
        self,
        *,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
        signal: SignalSelection,
    ) -> MessageBrief:

        merchant_identity = (
            context.merchant.payload.get(
                "identity",
                {},
            )
        )

        merchant_name = (
            merchant_identity.get(
                "owner_first_name"
            )
            or merchant_identity.get(
                "name"
            )
            or "there"
        )

        customer_name = None

        if context.customer:

            customer_identity = (
                context.customer.payload.get(
                    "identity",
                    {},
                )
            )

            customer_name = (
                customer_identity.get(
                    "name"
                )
                or "there"
            )

        by_id = {
            fact.id: fact
            for fact in facts
        }

        primary = by_id.get(
            signal.primary_fact_id
        )

        if primary is None:
            raise ValueError(
                "Primary signal fact disappeared."
            )

        supporting = tuple(
            by_id[fact_id].value
            for fact_id in (
                signal.supporting_fact_ids
            )
            if fact_id in by_id
        )

        instruction = self._instruction(
            policy.family
        )

        language_pref = self._language_pref(
            context
        )

        primary_fact_text = (
            f"{signal.candidate.event}. ({signal.candidate.implication})"
            if signal.candidate
            else primary.value
        )

        return MessageBrief(
            audience=(
                "customer"
                if context.customer
                else "merchant"
            ),
            merchant_name=merchant_name,
            customer_name=customer_name,
            trigger_kind=(
                context.trigger.payload.get(
                    "kind",
                    "unknown",
                )
            ),
            trigger_family=policy.family,
            primary_fact_id=primary.id,
            primary_fact=primary_fact_text,
            supporting_facts=supporting,
            cta=policy.cta,
            engagement_levers=(
                policy.engagement_levers
                if hasattr(
                    policy,
                    "engagement_levers",
                )
                else ()
            ),
            instruction=instruction,
            language_pref=language_pref,
        )

    @staticmethod
    def _language_pref(
        context: ContextBundle,
    ) -> str:
        if context.customer:
            cust_pref = (
                context.customer.payload.get(
                    "identity", {}
                ).get("language_pref")
            )
            if cust_pref:
                return str(cust_pref)

        merchant_identity = (
            context.merchant.payload.get(
                "identity", {}
            )
        )
        languages = merchant_identity.get(
            "languages", []
        )
        if isinstance(languages, list):
            if "hi" in languages and "en" in languages:
                return "hi-en mix"
            elif "hi" in languages:
                return "hi"

        return "en"

    @staticmethod
    def _instruction(
        family: str,
    ) -> str:

        instructions = {
            "performance": (
                "Explain the meaningful performance movement "
                "and turn it into one practical next action."
            ),
            "research": (
                "Surface the useful research implication "
                "without turning the message into a lecture."
            ),
            "compliance": (
                "Make the requirement and its practical "
                "implication immediately understandable."
            ),
            "opportunity": (
                "Explain why this opportunity matters now "
                "and make the next step easy."
            ),
            "lifecycle": (
                "Make the time-sensitive lifecycle event "
                "clear and remove friction from acting."
            ),
            "reactivation": (
                "Reconnect to the merchant's existing context "
                "without sounding like generic outreach."
            ),
            "seasonal": (
                "Connect the timely event to a concrete "
                "business opportunity."
            ),
            "local_event": (
                "Connect the local event to a relevant "
                "merchant action."
            ),
            "competitive": (
                "Make the competitive signal concrete "
                "without using fear-based exaggeration."
            ),
            "reputation": (
                "Surface the recurring reputation signal "
                "and suggest one useful response."
            ),
            "profile_health": (
                "Explain the profile issue and the simplest "
                "useful corrective action."
            ),
            "merchant_engagement": (
                "Ask a genuinely useful question that moves "
                "the merchant's current work forward."
            ),
            "planning": (
                "Treat the merchant as action-ready and "
                "move directly toward execution."
            ),
            "milestone": (
                "Acknowledge the meaningful milestone and "
                "connect it to a useful next move."
            ),
            "operations": (
                "Make the operational issue precise and "
                "surface the immediate action."
            ),
            "customer_recall": (
                "Make the reminder personal, concrete, and "
                "easy to act on."
            ),
            "customer_followup": (
                "Continue the customer's existing journey "
                "without restarting qualification."
            ),
            "customer_winback": (
                "Reconnect using real relationship history "
                "with minimal friction."
            ),
            "customer_trial": (
                "Move naturally from trial to the next "
                "specific step."
            ),
            "customer_refill": (
                "Make the refill timing and action clear "
                "without inventing medical advice."
            ),
        }

        return instructions.get(
            family,
            (
                "Focus on the strongest signal and "
                "make the next step clear."
            ),
        )

    def _fallback(
        self,
        *,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
        signal: SignalSelection,
        brief: MessageBrief,
    ) -> ComposedMessage:

        by_id = {fact.id: fact for fact in facts}
        cand = signal.candidate
        if cand:
            event_text = cand.event
            action_text = cand.action
        else:
            primary = by_id.get(signal.primary_fact_id)
            event_text = primary.value if primary else "a business update"
            action_text = "review next steps"

        if context.customer:
            customer_identity = (
                context.customer.payload.get("identity", {})
            )
            customer_name = (
                customer_identity.get("name") or "there"
            )
            merchant_identity = (
                context.merchant.payload.get("identity", {})
            )
            merchant_name = (
                merchant_identity.get("name") or "our clinic"
            )

            body = (
                f"Hi {customer_name}, this is {merchant_name}. "
                f"{event_text}. Would you like to check available slots for your visit?"
            )
        else:
            identity = (
                context.merchant.payload.get("identity", {})
            )
            name = (
                identity.get("owner_first_name")
                or identity.get("name")
                or "there"
            )

            if policy.family == "performance":
                body = (
                    f"{name}, {event_text}. "
                    f"Should we {action_text}?"
                )
            elif policy.family == "lifecycle":
                body = (
                    f"{name}, {event_text}. "
                    f"Should we {action_text} today?"
                )
            elif policy.family == "operations":
                body = (
                    f"{name}, operational alert: {event_text}. "
                    f"Would you like me to help {action_text}?"
                )
            else:
                body = (
                    f"{name}, {event_text}. "
                    f"Should we {action_text}?"
                )

        return ComposedMessage(
            body=body,
            cta=policy.cta,
            send_as=(
                "merchant_on_behalf"
                if context.customer
                else "vera"
            ),
            template_name=self.TEMPLATE_NAME,
            template_params=[
                signal.primary_fact_id,
            ],
            suppression_key=(
                context.trigger.payload.get(
                    "suppression_key",
                    "",
                )
            ),
            rationale=(
                "Deterministic grounded fallback used "
                "because LLM composition was unavailable "
                "or failed validation."
            ),
        )
