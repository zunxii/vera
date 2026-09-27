from __future__ import annotations

import re

from app.domain.context import ContextBundle
from app.domain.signal import SignalSelection
from app.policies.triggers import TriggerPolicy
from app.services.fact_projector import Fact


STRUCTURAL_FACTS = {
    "trigger.kind",
    "trigger.source",
    "trigger.scope",
    "trigger.merchant_id",
    "trigger.customer_id",
    "trigger.urgency",
    "trigger.payload.top_item_id",
    "trigger.payload.category",
    "trigger.payload.suppression_key",
    "trigger.payload.deadline_iso",
    "trigger.payload.id",
    "trigger.payload.source",
    "trigger.payload.scope",
    "trigger.payload.merchant_id",
    "trigger.payload.customer_id",
    "merchant.merchant_id",
    "merchant.category_slug",
    "category.slug",
    "customer.customer_id",
}


FAMILY_BONUS: dict[str, dict[str, int]] = {
    "performance": {
        "trigger.payload": 30,
        "merchant.performance": 35,
        "merchant.signals": 15,
        "category.peer_stats": 15,
    },
    "research": {
        "trigger.payload": 20,
        "category.digest": 40,
        "merchant.performance": 15,
        "category.peer_stats": 10,
    },
    "compliance": {
        "trigger.payload": 30,
        "category.digest": 40,
        "merchant.signals": 10,
    },
    "opportunity": {
        "trigger.payload": 30,
        "category.digest": 30,
        "merchant.offers": 20,
    },
    "lifecycle": {
        "trigger.payload": 35,
        "merchant.subscription": 35,
        "merchant.performance": 10,
    },
    "reactivation": {
        "trigger.payload": 30,
        "merchant.customer_aggregate": 25,
        "merchant.conversation_history": 20,
    },
    "seasonal": {
        "trigger.payload": 25,
        "category.seasonal_beats": 35,
        "merchant.performance": 15,
    },
    "local_event": {
        "trigger.payload": 35,
        "category.seasonal_beats": 20,
        "merchant.identity": 10,
    },
    "competitive": {
        "trigger.payload": 40,
        "merchant.offers": 25,
        "merchant.performance": 15,
    },
    "reputation": {
        "trigger.payload": 30,
        "merchant.review_themes": 40,
        "merchant.performance": 10,
    },
    "profile_health": {
        "trigger.payload": 35,
        "merchant.performance": 20,
        "merchant.signals": 20,
    },
    "merchant_engagement": {
        "merchant.conversation_history": 40,
        "trigger.payload": 25,
    },
    "planning": {
        "merchant.conversation_history": 45,
        "trigger.payload": 25,
        "merchant.offers": 15,
    },
    "milestone": {
        "trigger.payload": 35,
        "merchant.performance": 25,
    },
    "operations": {
        "trigger.payload": 45,
        "merchant.signals": 20,
    },
    "customer_recall": {
        "trigger.payload": 30,
        "customer.relationship": 35,
        "customer.preferences": 25,
    },
    "customer_followup": {
        "trigger.payload": 30,
        "customer.relationship": 35,
        "customer.preferences": 20,
    },
    "customer_winback": {
        "trigger.payload": 25,
        "customer.relationship": 40,
        "customer.state": 20,
    },
    "customer_trial": {
        "trigger.payload": 30,
        "customer.relationship": 30,
        "customer.preferences": 20,
    },
    "customer_refill": {
        "trigger.payload": 40,
        "customer.relationship": 25,
        "customer.state": 20,
    },
}


ACTIONABLE_CUES = re.compile(
    r"""
    delta|change|drop|down|up|increase|decrease|
    search|views|calls|direction|ctr|rating|
    offer|price|₹|discount|deadline|due|
    days|date|slot|availability|distance|
    competitor|review|theme|trend|milestone|
    trial|refill|renew|renewal|expiry|expires|
    customer|visit|lapsed|booking|conversion|
    intent|demand|opportunity|compliance|
    """,
    re.IGNORECASE | re.VERBOSE,
)


class SignalSelector:
    """
    Choose the strongest contextual signal for one message.

    The selector ranks facts rather than trigger kinds.
    """

    MAX_SUPPORTING_FACTS = 4

    def select(
        self,
        *,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
    ) -> SignalSelection:

        if not facts:
            raise ValueError(
                "SignalSelector requires facts."
            )

        family_weights = FAMILY_BONUS.get(
            policy.family,
            {},
        )

        top_item_id = (
            context.trigger.payload.get(
                "top_item_id"
            )
            if context.trigger
            and isinstance(
                context.trigger.payload,
                dict,
            )
            else None
        )

        scored = [
            (
                self._score(
                    fact,
                    family_weights,
                    top_item_id,
                ),
                fact,
            )
            for fact in facts
            if self._eligible(fact)
        ]

        if not scored:
            # Defensive fallback.
            primary = max(
                facts,
                key=lambda fact: fact.priority,
            )

            return SignalSelection(
                primary_fact_id=primary.id,
                supporting_fact_ids=(),
                reason=(
                    "No strongly actionable fact was found; "
                    "selected the highest-priority grounded fact."
                ),
            )

        scored.sort(
            key=lambda item: (
                -item[0],
                -item[1].priority,
                item[1].id,
            )
        )

        primary_score, primary = scored[0]

        supporting: list[str] = []

        seen_roots: set[str] = {
            self._root(primary.id)
        }

        for score, fact in scored[1:]:

            if len(supporting) >= self.MAX_SUPPORTING_FACTS:
                break

            root = self._root(
                fact.id
            )

            # Prefer evidence from a different context source.
            if root in seen_roots:
                continue

            supporting.append(
                fact.id
            )

            seen_roots.add(root)

        reason = self._reason(
            primary,
            primary_score,
            policy,
        )

        return SignalSelection(
            primary_fact_id=primary.id,
            supporting_fact_ids=tuple(
                supporting
            ),
            reason=reason,
        )

    @staticmethod
    def _eligible(
        fact: Fact,
    ) -> bool:

        if fact.id in STRUCTURAL_FACTS:
            return False

        return bool(
            ACTIONABLE_CUES.search(
                fact.id
            )
            or ACTIONABLE_CUES.search(
                fact.value
            )
        )

    @staticmethod
    def _root(
        fact_id: str,
    ) -> str:
        return fact_id.split(
            ".",
            maxsplit=2,
        )[0]

    def _score(
        self,
        fact: Fact,
        family_weights: dict[str, int],
        top_item_id: str | None = None,
    ) -> int:

        score = fact.priority

        for path, bonus in family_weights.items():

            if fact.id.startswith(path):
                score += bonus
                break

        if top_item_id and top_item_id in fact.value:
            score += 50

        if self._has_actionable_value(
            fact.value
        ):
            score += 15

        if any(
            token in fact.id.lower()
            for token in (
                "delta",
                "deadline",
                "days",
                "due",
                "search",
                "offer",
                "price",
                "trend",
                "lapsed",
                "slot",
            )
        ):
            score += 10

        return score

    @staticmethod
    def _has_actionable_value(
        value: str,
    ) -> bool:

        return bool(
            ACTIONABLE_CUES.search(
                value
            )
        )

    @staticmethod
    def _reason(
        primary: Fact,
        score: int,
        policy: TriggerPolicy,
    ) -> str:

        return (
            f"Selected {primary.id} as the primary "
            f"{policy.family} signal because it provides "
            f"the strongest grounded, actionable evidence "
            f"for the current trigger."
        )
