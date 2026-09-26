from app.core.context_store import ContextStore
from app.core.delivery_state import DeliveryState
from app.domain.context import ContextBundle
from app.policies.triggers import get_policy
from app.services.context_resolver import ContextResolver
from app.services.fact_projector import FactProjector
from app.services.trigger_planner import TriggerPlanner


def seed_store() -> ContextStore:
    store = ContextStore()

    store.put(
        scope="category",
        context_id="dentists",
        version=1,
        payload={
            "slug": "dentists",
            "voice": {
                "tone": "peer_clinical",
                "vocab_taboo": [
                    "guaranteed",
                    "cure",
                ],
            },
            "peer_stats": {
                "avg_ctr": 0.03,
            },
        },
    )

    store.put(
        scope="merchant",
        context_id="m1",
        version=1,
        payload={
            "merchant_id": "m1",
            "category_slug": "dentists",
            "identity": {
                "owner_first_name": "Meera",
                "name": "Meera Dental",
            },
            "performance": {
                "calls": 18,
                "views": 2410,
            },
            "signals": [
                "perf_dip_severe",
            ],
        },
    )

    store.put(
        scope="trigger",
        context_id="t1",
        version=1,
        payload={
            "id": "t1",
            "scope": "merchant",
            "kind": "perf_dip",
            "source": "internal",
            "merchant_id": "m1",
            "urgency": 4,
            "payload": {
                "metric": "calls",
                "delta_pct": -0.5,
                "window": "7d",
            },
            "suppression_key": "perf:m1:calls",
        },
    )

    return store


def test_policy_exists():

    policy = get_policy(
        "perf_dip"
    )

    assert policy is not None
    assert policy.family == "performance"
    assert policy.priority == 85


def test_context_resolver():

    store = seed_store()

    resolver = ContextResolver(
        store
    )

    context = resolver.resolve(
        "t1"
    )

    assert context is not None

    assert (
        context.merchant.payload[
            "merchant_id"
        ]
        == "m1"
    )

    assert (
        context.category.payload[
            "slug"
        ]
        == "dentists"
    )

    assert context.customer is None


def test_fact_projector():

    store = seed_store()

    resolver = ContextResolver(
        store
    )

    context = resolver.resolve(
        "t1"
    )

    policy = get_policy(
        "perf_dip"
    )

    projector = FactProjector()

    facts = projector.project(
        context,
        policy.facts,
    )

    ids = {
        fact.id
        for fact in facts
    }

    assert (
        "trigger.payload.metric"
        in ids
    )

    assert (
        "trigger.payload.delta_pct"
        in ids
    )

    assert (
        "merchant.performance.calls"
        in ids
    )

    assert (
        "merchant.identity.owner_first_name"
        in ids
    )


def test_trigger_planner_filters_suppressed():

    store = seed_store()

    delivery_state = DeliveryState()

    resolver = ContextResolver(
        store
    )

    planner = TriggerPlanner(
        resolver,
        delivery_state,
    )

    first = planner.plan(
        now="2026-04-26T10:00:00Z",
        trigger_ids=["t1"],
    )

    assert len(first) == 1

    delivery_state.mark_sent(
        "perf:m1:calls"
    )

    second = planner.plan(
        now="2026-04-26T10:01:00Z",
        trigger_ids=["t1"],
    )

    assert second == []


def test_trigger_planner_uses_latest_context():

    store = seed_store()

    resolver = ContextResolver(
        store
    )

    store.put(
        scope="merchant",
        context_id="m1",
        version=2,
        payload={
            "merchant_id": "m1",
            "category_slug": "dentists",
            "identity": {
                "owner_first_name": "Updated",
                "name": "Updated Dental",
            },
        },
    )

    context = resolver.resolve(
        "t1"
    )

    assert (
        context.merchant.payload[
            "identity"
        ]["owner_first_name"]
        == "Updated"
    )
