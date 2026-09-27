from __future__ import annotations

import re
from typing import Any

from app.domain.context import ContextBundle
from app.domain.signal import SignalCandidate, SignalSelection
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
    Ranks facts and derives a clean SignalCandidate to guide composition.
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
            raise ValueError("SignalSelector requires facts.")

        family_weights = FAMILY_BONUS.get(policy.family, {})
        top_item_id = (
            context.trigger.payload.get("top_item_id")
            if context.trigger and isinstance(context.trigger.payload, dict)
            else None
        )

        scored = [
            (self._score(fact, family_weights, top_item_id), fact)
            for fact in facts
            if self._eligible(fact)
        ]

        if not scored:
            primary = max(facts, key=lambda fact: fact.priority)
            candidate = self._derive_candidate(primary, context, policy, facts)
            return SignalSelection(
                primary_fact_id=primary.id,
                supporting_fact_ids=(),
                reason="Selected highest-priority grounded fact.",
                candidate=candidate,
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
        seen_roots: set[str] = {self._root(primary.id)}

        for score, fact in scored[1:]:
            if len(supporting) >= self.MAX_SUPPORTING_FACTS:
                break

            root = self._root(fact.id)
            if root in seen_roots:
                continue

            supporting.append(fact.id)
            seen_roots.add(root)

        candidate = self._derive_candidate(primary, context, policy, facts)
        reason = self._reason(primary, primary_score, policy)

        return SignalSelection(
            primary_fact_id=primary.id,
            supporting_fact_ids=tuple(supporting),
            reason=reason,
            candidate=candidate,
        )

    @staticmethod
    def _eligible(fact: Fact) -> bool:
        if fact.id in STRUCTURAL_FACTS:
            return False
        return bool(
            ACTIONABLE_CUES.search(fact.id)
            or ACTIONABLE_CUES.search(fact.value)
        )

    @staticmethod
    def _root(fact_id: str) -> str:
        return fact_id.split(".", maxsplit=2)[0]

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

        if self._has_actionable_value(fact.value):
            score += 15

        if any(
            token in fact.id.lower()
            for token in (
                "delta", "deadline", "days", "due", "search",
                "offer", "price", "trend", "lapsed", "slot", "digest",
            )
        ):
            score += 10

        return score

    @staticmethod
    def _has_actionable_value(value: str) -> bool:
        return bool(ACTIONABLE_CUES.search(value))

    @staticmethod
    def _reason(primary: Fact, score: int, policy: TriggerPolicy) -> str:
        return (
            f"Selected {primary.id} as primary {policy.family} signal because "
            f"it provides the strongest grounded evidence."
        )

    def _derive_candidate(
        self,
        primary: Fact,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
    ) -> SignalCandidate:
        """
        Derive a rich, contextual SignalCandidate from trigger payload and context
        to eliminate raw scalar/JSON leaks into composed messages.
        """
        kind = context.trigger.payload.get("kind", policy.kind) if context.trigger else policy.kind
        payload = context.trigger.payload if context.trigger else {}
        evidence_list: list[str] = [primary.value]

        # Gather supporting facts for evidence
        for f in facts:
            if f.id != primary.id and f.value not in evidence_list:
                evidence_list.append(f.value)

        evidence = tuple(evidence_list[:3])

        # 1. Performance Dip / Metric Drops
        if kind in ("perf_dip", "seasonal_perf_dip") or "delta_pct" in primary.id:
            val_str = primary.value
            pct_text = "30%"
            try:
                val_num = float(primary.value)
                pct_text = f"{int(abs(val_num) * 100)}%"
            except ValueError:
                if "%" in primary.value:
                    pct_text = primary.value

            event = f"Merchant profile views and call leads dropped by {pct_text}"
            implication = "fewer prospective customers are discovering or reaching out to the merchant listing"
            action = "review listing performance and consider running a featured promo boost"
            return SignalCandidate(
                id=f"signal:{kind}",
                event=event,
                evidence=evidence,
                implication=implication,
                action=action,
            )

        # 2. Customer Lapsed / Recall / Winback
        if kind in ("customer_lapsed_soft", "customer_lapsed_hard", "recall_due") or "days_since" in primary.id:
            days = payload.get("days_since", payload.get("days_lapsed", "30"))
            event = f"It has been {days} days since the customer's last service visit"
            implication = "customer engagement is fading and requires a warm personalized check-in"
            action = "offer a convenience slot or special follow-up incentive"
            return SignalCandidate(
                id=f"signal:{kind}",
                event=event,
                evidence=evidence,
                implication=implication,
                action=action,
            )

        # 3. Research Digest / Regulations / Compliance
        if kind in ("research_digest", "regulation_change", "cde_opportunity") or "digest" in primary.id:
            topic = payload.get("topic", payload.get("title", primary.value))
            event = f"Recent industry research digest update regarding {topic}"
            implication = "presents a relevant professional practice update for merchant service quality"
            action = "review the guidance and inform patients/customers of updated standards"
            return SignalCandidate(
                id=f"signal:{kind}",
                event=event,
                evidence=evidence,
                implication=implication,
                action=action,
            )

        # 4. Renewal Due / Subscription
        if kind == "renewal_due" or "subscription" in primary.id or "renewal" in primary.id:
            days = payload.get("days_to_expiry", payload.get("days_left", "15"))
            event = f"Merchant subscription renewal is due in {days} days"
            implication = "uninterrupted listing visibility and direct customer lead routing require timely renewal"
            action = "confirm renewal plan to lock in uninterrupted active status"
            return SignalCandidate(
                id=f"signal:{kind}",
                event=event,
                evidence=evidence,
                implication=implication,
                action=action,
            )

        # 5. Wedding Followup
        if kind == "wedding_package_followup" or "wedding" in primary.id:
            days = payload.get("days_to_wedding", "196")
            event = f"Customer's wedding date is approaching in {days} days"
            implication = "ideal timeline for scheduling pre-wedding packages and grooming sessions"
            action = "recommend a consultation for bridal/grooming packages"
            return SignalCandidate(
                id=f"signal:{kind}",
                event=event,
                evidence=evidence,
                implication=implication,
                action=action,
            )

        # 6. Festival / Seasonal
        if kind in ("festival_upcoming", "category_seasonal") or "festival" in primary.id:
            fest_name = payload.get("festival_name", payload.get("event", "upcoming festival season"))
            event = f"Preparation for {fest_name} in the local market"
            implication = "customer spending and demand for festive packages will surge"
            action = "create a dedicated festival package or promotional offer"
            return SignalCandidate(
                id=f"signal:{kind}",
                event=event,
                evidence=evidence,
                implication=implication,
                action=action,
            )

        # 7. IPL Match / Local Event
        if kind == "ipl_match_today" or "match" in primary.id:
            event = "IPL match taking place locally today"
            implication = "heightened sports excitement and high demand for group meals/combos"
            action = "run a match-day combo special offer"
            return SignalCandidate(
                id=f"signal:{kind}",
                event=event,
                evidence=evidence,
                implication=implication,
                action=action,
            )

        # 8. Generic contextualized fallback for raw scalars
        clean_value = primary.value
        # If value is raw float like "0.3"
        try:
            val_num = float(primary.value)
            if 0 < val_num < 1:
                clean_value = f"{int(val_num * 100)}% shift in {primary.id.split('.')[-1].replace('_', ' ')}"
        except ValueError:
            pass

        return SignalCandidate(
            id=f"signal:{kind}",
            event=f"{kind.replace('_', ' ').title()} signal: {clean_value}",
            evidence=evidence,
            implication="business decision or customer outreach opportunity",
            action="review relevant details and take recommended action",
        )
