from types import SimpleNamespace

from app.domain.context import ContextBundle
from app.domain.signal import SignalSelection
from app.policies.triggers import TriggerPolicy
from app.services.fact_projector import Fact
from app.services.signal_selector import (
    SignalSelector,
)


def context() -> ContextBundle:

    return SimpleNamespace(
        trigger=SimpleNamespace(
            payload={
                "kind": "perf_dip",
                "merchant_id": "m1",
            }
        ),
        merchant=SimpleNamespace(
            payload={
                "merchant_id": "m1",
            }
        ),
        category=SimpleNamespace(
            payload={
                "slug": "dentists",
            }
        ),
        customer=None,
    )


def test_performance_signal_prefers_metric_change():

    facts = [
        Fact(
            id="trigger.kind",
            value="perf_dip",
            priority=100,
        ),
        Fact(
            id="trigger.payload.metric",
            value="calls",
            priority=95,
        ),
        Fact(
            id="trigger.payload.delta_pct",
            value="-50%",
            priority=95,
        ),
        Fact(
            id="merchant.performance.calls",
            value="18",
            priority=85,
        ),
        Fact(
            id="merchant.identity.name",
            value="Meera Dental",
            priority=75,
        ),
    ]

    policy = TriggerPolicy(
        kind="perf_dip",
        family="performance",
        priority=85,
        facts=(),
    )

    selection = SignalSelector().select(
        context=context(),
        policy=policy,
        facts=facts,
    )

    assert (
        selection.primary_fact_id
        == "trigger.payload.delta_pct"
    )

    assert (
        "merchant.performance.calls"
        in selection.supporting_fact_ids
    )


def test_structural_facts_are_not_selected():

    facts = [
        Fact(
            id="trigger.kind",
            value="perf_dip",
            priority=100,
        ),
        Fact(
            id="merchant.merchant_id",
            value="m1",
            priority=100,
        ),
        Fact(
            id="merchant.performance.calls",
            value="18",
            priority=80,
        ),
    ]

    policy = TriggerPolicy(
        kind="perf_dip",
        family="performance",
        priority=85,
        facts=(),
    )

    selection = SignalSelector().select(
        context=context(),
        policy=policy,
        facts=facts,
    )

    assert (
        selection.primary_fact_id
        == "merchant.performance.calls"
    )


def test_focus_keeps_only_selected_facts():

    selection = SignalSelection(
        primary_fact_id="a",
        supporting_fact_ids=("b",),
        reason="test",
    )

    facts = [
        Fact(
            id="a",
            value="A",
            priority=10,
        ),
        Fact(
            id="b",
            value="B",
            priority=10,
        ),
        Fact(
            id="c",
            value="C",
            priority=10,
        ),
    ]

    focused = selection.focus(
        facts
    )

    assert [
        fact.id
        for fact in focused
    ] == ["a", "b"]
