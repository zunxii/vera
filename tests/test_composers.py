from app.composers.registry import ComposerRegistry, FallbackComposer
from app.core.context_store import StoredContext
from app.domain.context import ContextBundle
from app.policies.triggers import get_policy
from app.services.fact_projector import FactProjector


def test_fallback_composer():
    composer = FallbackComposer()

    trigger = StoredContext(
        scope="trigger",
        context_id="trg_perf",
        version=1,
        payload={
            "kind": "perf_dip",
            "suppression_key": "supp_perf_1",
            "payload": {"metric": "views", "delta_pct": -0.25, "window": "7d"},
        },
    )
    merchant = StoredContext(
        scope="merchant",
        context_id="m_001",
        version=1,
        payload={"identity": {"owner_first_name": "Meera", "name": "Meera Dental"}},
    )
    category = StoredContext(
        scope="category",
        context_id="dentists",
        version=1,
        payload={"slug": "dentists"},
    )

    context = ContextBundle(
        trigger=trigger, merchant=merchant, category=category, customer=None
    )
    policy = get_policy("perf_dip")
    assert policy is not None

    projector = FactProjector()
    facts = projector.project(context, policy.facts)

    msg = composer.compose(context, policy, facts)
    assert msg is not None
    assert "Meera" in msg.body
    assert msg.cta == "binary_yes_no"


def test_composer_registry_dispatch():
    registry = ComposerRegistry()

    trigger = StoredContext(
        scope="trigger",
        context_id="trg_res",
        version=1,
        payload={
            "kind": "research_digest",
            "suppression_key": "supp_res_1",
            "payload": {"category": "dentists", "top_item_id": "d_123"},
        },
    )
    merchant = StoredContext(
        scope="merchant",
        context_id="m_001",
        version=1,
        payload={"identity": {"owner_first_name": "Meera"}},
    )
    category = StoredContext(
        scope="category",
        context_id="dentists",
        version=1,
        payload={"slug": "dentists"},
    )

    context = ContextBundle(
        trigger=trigger, merchant=merchant, category=category, customer=None
    )
    policy = get_policy("research_digest")
    assert policy is not None

    projector = FactProjector()
    facts = projector.project(context, policy.facts)

    msg = registry.compose(context, policy, facts)
    assert msg is not None
    assert "Meera" in msg.body
