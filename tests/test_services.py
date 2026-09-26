from app.core.context_store import ContextStore, StoredContext
from app.core.delivery_state import DeliveryState
from app.domain.context import ContextBundle
from app.policies.triggers import get_policy
from app.services.context_resolver import ContextResolver
from app.services.fact_projector import FactProjector
from app.services.suppression_service import SuppressionService
from app.services.validation_service import ValidationService


def test_fact_projector_service():
    projector = FactProjector()

    trigger = StoredContext(
        scope="trigger",
        context_id="t1",
        version=1,
        payload={
            "id": "t1",
            "scope": "merchant",
            "kind": "perf_dip",
            "merchant_id": "m1",
            "urgency": 4,
            "payload": {
                "metric": "calls",
                "delta_pct": -0.4,
            },
        },
    )
    merchant = StoredContext(
        scope="merchant",
        context_id="m1",
        version=1,
        payload={
            "merchant_id": "m1",
            "identity": {"name": "Dental Clinic", "owner_first_name": "Meera"},
            "subscription": {"plan": "Pro", "days_remaining": 30},
            "offers": [{"title": "Offer 1", "status": "active"}],
        },
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

    facts = projector.project(context, policy.facts)
    fact_ids = {f.id for f in facts}

    assert "merchant.identity.owner_first_name" in fact_ids
    assert "trigger.payload.metric" in fact_ids


def test_suppression_service():
    state = DeliveryState()
    service = SuppressionService(state)

    assert not service.is_suppressed("key_1")
    service.mark_sent("key_1")
    assert service.is_suppressed("key_1")


def test_validation_service_url_rejection():
    valid_action = {
        "conversation_id": "conv_1",
        "merchant_id": "m_1",
        "customer_id": None,
        "send_as": "vera",
        "trigger_id": "trg_1",
        "template_name": "tmpl_1",
        "template_params": ["a"],
        "body": "Hello there, check this out.",
        "cta": "open_ended",
        "suppression_key": "supp_1",
        "rationale": "valid",
    }
    assert ValidationService.validate_action(valid_action) is True

    url_action = {**valid_action, "body": "Visit https://magicpin.com for details"}
    assert ValidationService.validate_action(url_action) is False
