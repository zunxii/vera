from app.core.context_store import (
    ContextStore,
)
from app.core.delivery_state import (
    DeliveryState,
)
from app.domain.context import (
    ContextBundle,
)
from app.policies.triggers import (
    get_policy,
)
from app.services.context_resolver import (
    ContextResolver,
)
from app.services.decision_selector import (
    DecisionSelector,
)
from app.services.trigger_planner import (
    PlannedTrigger,
)


def _planned(
    trigger_id: str,
    merchant_id: str,
    kind: str,
    priority: int,
    customer_id: str | None = None,
) -> PlannedTrigger:

    from app.core.context_store import (
        StoredContext,
    )
    from app.domain.context import (
        ContextBundle,
    )
    from app.policies.triggers import (
        TriggerPolicy,
    )

    trigger = StoredContext(
        scope="trigger",
        context_id=trigger_id,
        version=1,
        payload={
            "id": trigger_id,
            "scope": (
                "customer"
                if customer_id
                else "merchant"
            ),
            "kind": kind,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "urgency": priority,
            "payload": {},
        },
    )

    merchant = StoredContext(
        scope="merchant",
        context_id=merchant_id,
        version=1,
        payload={
            "merchant_id": merchant_id,
            "category_slug": "dentists",
        },
    )

    category = StoredContext(
        scope="category",
        context_id="dentists",
        version=1,
        payload={
            "slug": "dentists",
        },
    )

    customer = None

    if customer_id:
        customer = StoredContext(
            scope="customer",
            context_id=customer_id,
            version=1,
            payload={
                "customer_id": customer_id,
                "merchant_id": merchant_id,
            },
        )

    context = ContextBundle(
        trigger=trigger,
        merchant=merchant,
        category=category,
        customer=customer,
    )

    policy = TriggerPolicy(
        kind=kind,
        family="test",
        priority=priority,
    )

    return PlannedTrigger(
        context=context,
        policy=policy,
    )


def test_selector_keeps_one_merchant_signal():

    selector = DecisionSelector()

    candidates = [
        _planned(
            "t_low",
            "m1",
            "perf_dip",
            50,
        ),
        _planned(
            "t_high",
            "m1",
            "renewal_due",
            90,
        ),
    ]

    selected = selector.select(
        candidates
    )

    assert [
        x.context.trigger.context_id
        for x in selected
    ] == ["t_high"]


def test_selector_keeps_customer_signal_separate():

    selector = DecisionSelector()

    candidates = [
        _planned(
            "merchant",
            "m1",
            "perf_dip",
            50,
        ),
        _planned(
            "customer",
            "m1",
            "recall_due",
            50,
            customer_id="c1",
        ),
    ]

    selected = selector.select(
        candidates
    )

    assert len(selected) == 2


def test_context_version_replay_is_success():

    store = ContextStore()

    first = store.put(
        scope="merchant",
        context_id="m1",
        version=1,
        payload={"value": "x"},
    )

    replay = store.put(
        scope="merchant",
        context_id="m1",
        version=1,
        payload={"value": "x"},
    )

    assert first.accepted
    assert replay.accepted
    assert replay.replay


def test_lower_context_version_is_rejected():

    store = ContextStore()

    store.put(
        scope="merchant",
        context_id="m1",
        version=2,
        payload={"value": "new"},
    )

    result = store.put(
        scope="merchant",
        context_id="m1",
        version=1,
        payload={"value": "old"},
    )

    assert not result.accepted
    assert (
        result.current_version
        == 2
    )
