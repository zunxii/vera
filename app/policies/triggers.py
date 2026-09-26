from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FactSpec:
    path: str
    priority: int
    limit: int = 6


@dataclass(frozen=True)
class TriggerPolicy:
    kind: str
    family: str
    priority: int

    proactive: bool = True
    customer_facing: bool = False

    cta: str = "open_ended"

    facts: tuple[FactSpec, ...] = ()


COMMON_MERCHANT = (
    FactSpec("trigger.kind", 100),
    FactSpec("trigger.source", 95),
    FactSpec("trigger.urgency", 95),
    FactSpec("trigger.payload.*", 100, 10),
    FactSpec("merchant.merchant_id", 80),
    FactSpec("merchant.category_slug", 80),
    FactSpec("merchant.identity.owner_first_name", 75),
    FactSpec("merchant.identity.name", 75),
    FactSpec("merchant.identity.city", 70),
    FactSpec("merchant.identity.locality", 70),
    FactSpec("category.slug", 65),
    FactSpec("category.voice.tone", 60),
    FactSpec("category.voice.vocab_allowed", 50),
    FactSpec("category.voice.vocab_taboo", 90),
)

COMMON_CUSTOMER = COMMON_MERCHANT + (
    FactSpec("customer.customer_id", 80),
    FactSpec("customer.identity.*", 75, 6),
    FactSpec("customer.relationship.*", 80, 8),
    FactSpec("customer.preferences.*", 70, 6),
    FactSpec("customer.consent.*", 90, 4),
    FactSpec("customer.state", 75),
)


def _merchant(
    kind: str,
    family: str,
    priority: int,
    *,
    cta: str = "open_ended",
    extra: tuple[FactSpec, ...] = (),
) -> TriggerPolicy:
    return TriggerPolicy(
        kind=kind,
        family=family,
        priority=priority,
        cta=cta,
        facts=COMMON_MERCHANT + extra,
    )


def _customer(
    kind: str,
    family: str,
    priority: int,
    *,
    cta: str = "open_ended",
    extra: tuple[FactSpec, ...] = (),
) -> TriggerPolicy:
    return TriggerPolicy(
        kind=kind,
        family=family,
        priority=priority,
        customer_facing=True,
        cta=cta,
        facts=COMMON_CUSTOMER + extra,
    )


POLICIES: dict[str, TriggerPolicy] = {
    # ---------------------------------------------------------
    # Knowledge / external signals
    # ---------------------------------------------------------

    "research_digest": _merchant(
        "research_digest",
        "research",
        60,
        extra=(
            FactSpec(
                "category.digest.*",
                85,
                8,
            ),
            FactSpec(
                "category.peer_stats.*",
                45,
                5,
            ),
        ),
    ),

    "regulation_change": _merchant(
        "regulation_change",
        "compliance",
        90,
        cta="binary_yes_no",
        extra=(
            FactSpec(
                "category.digest.*",
                85,
                8,
            ),
        ),
    ),

    "cde_opportunity": _merchant(
        "cde_opportunity",
        "opportunity",
        70,
        cta="binary_yes_no",
        extra=(
            FactSpec(
                "category.digest.*",
                80,
                6,
            ),
        ),
    ),

    # ---------------------------------------------------------
    # Performance
    # ---------------------------------------------------------

    "perf_dip": _merchant(
        "perf_dip",
        "performance",
        85,
        cta="binary_yes_no",
        extra=(
            FactSpec(
                "merchant.performance.*",
                85,
                8,
            ),
            FactSpec(
                "merchant.signals.*",
                70,
                6,
            ),
        ),
    ),

    "perf_spike": _merchant(
        "perf_spike",
        "performance",
        65,
        extra=(
            FactSpec(
                "merchant.performance.*",
                85,
                8,
            ),
            FactSpec(
                "merchant.signals.*",
                70,
                6,
            ),
        ),
    ),

    "seasonal_perf_dip": _merchant(
        "seasonal_perf_dip",
        "performance",
        65,
        extra=(
            FactSpec(
                "merchant.performance.*",
                85,
                8,
            ),
            FactSpec(
                "category.seasonal_beats.*",
                60,
                5,
            ),
        ),
    ),

    # ---------------------------------------------------------
    # Lifecycle / merchant state
    # ---------------------------------------------------------

    "renewal_due": _merchant(
        "renewal_due",
        "lifecycle",
        85,
        cta="binary_yes_no",
        extra=(
            FactSpec(
                "merchant.subscription.*",
                85,
                6,
            ),
        ),
    ),

    "dormant_with_vera": _merchant(
        "dormant_with_vera",
        "reactivation",
        35,
        extra=(
            FactSpec(
                "merchant.conversation_history.*",
                65,
                4,
            ),
        ),
    ),

    "winback_eligible": _merchant(
        "winback_eligible",
        "reactivation",
        65,
        extra=(
            FactSpec(
                "merchant.subscription.*",
                70,
                4,
            ),
            FactSpec(
                "merchant.customer_aggregate.*",
                70,
                5,
            ),
        ),
    ),

    # ---------------------------------------------------------
    # Seasonal / local
    # ---------------------------------------------------------

    "festival_upcoming": _merchant(
        "festival_upcoming",
        "seasonal",
        55,
        extra=(
            FactSpec(
                "category.seasonal_beats.*",
                65,
                5,
            ),
        ),
    ),

    "category_seasonal": _merchant(
        "category_seasonal",
        "seasonal",
        55,
        extra=(
            FactSpec(
                "category.seasonal_beats.*",
                65,
                5,
            ),
        ),
    ),

    "ipl_match_today": _merchant(
        "ipl_match_today",
        "local_event",
        55,
    ),

    # ---------------------------------------------------------
    # Competitive / reputation
    # ---------------------------------------------------------

    "competitor_opened": _merchant(
        "competitor_opened",
        "competitive",
        80,
        extra=(
            FactSpec(
                "merchant.offers.*",
                65,
                6,
            ),
        ),
    ),

    "review_theme_emerged": _merchant(
        "review_theme_emerged",
        "reputation",
        70,
        cta="binary_yes_no",
        extra=(
            FactSpec(
                "merchant.review_themes.*",
                85,
                8,
            ),
        ),
    ),

    "gbp_unverified": _merchant(
        "gbp_unverified",
        "profile_health",
        75,
        cta="binary_yes_no",
    ),

    # ---------------------------------------------------------
    # Merchant engagement / intent
    # ---------------------------------------------------------

    "curious_ask_due": _merchant(
        "curious_ask_due",
        "merchant_engagement",
        40,
        extra=(
            FactSpec(
                "merchant.conversation_history.*",
                65,
                5,
            ),
        ),
    ),

    "active_planning_intent": _merchant(
        "active_planning_intent",
        "planning",
        90,
        cta="action",
        extra=(
            FactSpec(
                "merchant.conversation_history.*",
                80,
                6,
            ),
        ),
    ),

    "milestone_reached": _merchant(
        "milestone_reached",
        "milestone",
        55,
        extra=(
            FactSpec(
                "merchant.performance.*",
                65,
                6,
            ),
        ),
    ),

    "supply_alert": _merchant(
        "supply_alert",
        "operations",
        95,
        cta="binary_yes_no",
    ),

    # ---------------------------------------------------------
    # Customer
    # ---------------------------------------------------------

    "recall_due": _customer(
        "recall_due",
        "customer_recall",
        85,
        cta="multi_choice_slot",
    ),

    "wedding_package_followup": _customer(
        "wedding_package_followup",
        "customer_followup",
        70,
    ),

    "customer_lapsed_hard": _customer(
        "customer_lapsed_hard",
        "customer_winback",
        60,
    ),

    "trial_followup": _customer(
        "trial_followup",
        "customer_trial",
        70,
        cta="multi_choice_slot",
    ),

    "chronic_refill_due": _customer(
        "chronic_refill_due",
        "customer_refill",
        90,
    ),
}


def get_policy(
    kind: str,
) -> TriggerPolicy | None:
    return POLICIES.get(kind)


def supported_kinds() -> tuple[str, ...]:
    return tuple(
        sorted(POLICIES)
    )
