from app.composers.llm_composer import LLMComposer
from app.core.context_store import StoredContext
from app.domain.context import ContextBundle
from app.llm.fallback import FallbackLLM
from app.llm.schemas import LLMMessageDraft
from app.policies.triggers import get_policy
from app.services.fact_projector import Fact, FactProjector
from app.services.validation_service import ValidationService


def test_fact_projector_selection():
    projector = FactProjector()

    trigger = StoredContext(
        scope="trigger",
        context_id="trg_1",
        version=1,
        payload={
            "id": "trg_1",
            "scope": "merchant",
            "kind": "perf_dip",
            "source": "internal",
            "merchant_id": "m_1",
            "urgency": 4,
            "payload": {
                "metric": "calls",
                "delta_pct": -0.4,
            },
            "suppression_key": "supp_1",
        },
    )
    merchant = StoredContext(
        scope="merchant",
        context_id="m_1",
        version=1,
        payload={
            "merchant_id": "m_1",
            "category_slug": "dentists",
            "identity": {
                "name": "Dr. Meera's Dental Clinic",
                "city": "Delhi",
                "owner_first_name": "Meera",
            },
            "performance": {
                "calls": 18,
            },
        },
    )
    category = StoredContext(
        scope="category",
        context_id="dentists",
        version=1,
        payload={
            "slug": "dentists",
            "voice": {
                "tone": "peer_clinical",
                "taboos": ["cure", "guarantee"],
            },
        },
    )

    context = ContextBundle(
        trigger=trigger, merchant=merchant, category=category, customer=None
    )
    policy = get_policy("perf_dip")
    assert policy is not None

    facts = projector.project(context, policy.facts)
    fact_ids = {fact.id for fact in facts}

    assert "trigger.payload.metric" in fact_ids
    assert "merchant.identity.name" in fact_ids
    assert "merchant.identity.owner_first_name" in fact_ids


def test_validator_rejects_unsupported_numbers():
    validator = ValidationService()

    facts = [
        Fact(
            id="trigger.payload.delta_pct",
            value="-0.4",
            priority=100,
        )
    ]

    draft = LLMMessageDraft(
        body="Calls dropped 70%. Want me to investigate?",
        cta="open_ended",
        used_fact_ids=["trigger.payload.delta_pct"],
        template_params=[],
        rationale="test",
    )

    result = validator.validate(
        draft=draft,
        facts=facts,
        taboos=[],
    )

    assert not result.valid
    assert any("unsupported_numbers" in err for err in result.errors)


def test_validator_rejects_taboo_words():
    validator = ValidationService()

    facts = [
        Fact(
            id="merchant.identity.name",
            value="Dr Meera Clinic",
            priority=80,
        )
    ]

    draft = LLMMessageDraft(
        body="We can guarantee a cure for your dental pain.",
        cta="open_ended",
        used_fact_ids=["merchant.identity.name"],
        template_params=[],
        rationale="test",
    )

    result = validator.validate(
        draft=draft,
        facts=facts,
        taboos=["guarantee", "cure"],
    )

    assert not result.valid
    assert any("taboo" in err for err in result.errors)


def test_llm_composer_fallback():
    fallback_llm = FallbackLLM()
    validator = ValidationService()

    composer = LLMComposer(
        llm=fallback_llm,
        validator=validator,
    )

    trigger = StoredContext(
        scope="trigger",
        context_id="trg_1",
        version=1,
        payload={
            "id": "trg_1",
            "scope": "merchant",
            "kind": "research_digest",
            "payload": {"category": "dentists"},
            "suppression_key": "supp_1",
        },
    )
    merchant = StoredContext(
        scope="merchant",
        context_id="m_1",
        version=1,
        payload={
            "merchant_id": "m_1",
            "category_slug": "dentists",
            "identity": {"name": "Test Merchant"},
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
    policy = get_policy("research_digest")
    assert policy is not None

    projector = FactProjector()
    facts = projector.project(context, policy.facts)

    msg = composer.compose(context, policy, facts)
    assert msg is not None
    assert msg.send_as == "vera"
    assert "I spotted an update" in msg.body
