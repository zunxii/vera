from types import SimpleNamespace

from app.domain.context import ContextBundle
from app.domain.signal import SignalSelection
from app.policies.triggers import TriggerPolicy
from app.services.engagement_service import (
    EngagementService,
)
from app.services.fact_projector import Fact
from app.services.message_validator import (
    MessageValidator,
)


class FakeLLM:

    def generate(self, prompt: str):

        from app.llm.schemas import (
            LLMMessageDraft,
        )

        return LLMMessageDraft(
            body=(
                "Meera, calls are down 50% this week. "
                "Want me to look at the likely cause?"
            ),
            cta="open_ended",
            used_fact_ids=[
                "trigger.payload.delta_pct",
            ],
            template_params=[],
            rationale=(
                "The strongest current signal is "
                "the calls decline."
            ),
        )


class FailingLLM:

    def generate(self, prompt: str):
        raise RuntimeError(
            "provider unavailable"
        )


def build_context():

    return ContextBundle(
        trigger=SimpleNamespace(
            payload={
                "kind": "perf_dip",
                "scope": "merchant",
                "merchant_id": "m1",
                "suppression_key": "x",
            }
        ),
        merchant=SimpleNamespace(
            payload={
                "merchant_id": "m1",
                "identity": {
                    "owner_first_name": "Meera",
                    "name": "Meera Dental",
                },
            }
        ),
        category=SimpleNamespace(
            payload={
                "slug": "dentists",
                "voice": {
                    "tone": "peer_clinical",
                    "vocab_taboo": [],
                },
            }
        ),
        customer=None,
    )


def test_composer_uses_selected_signal():

    context = build_context()

    policy = TriggerPolicy(
        kind="perf_dip",
        family="performance",
        priority=85,
        cta="open_ended",
        facts=(),
    )

    facts = [
        Fact(
            id="trigger.payload.delta_pct",
            value="-50%",
            priority=100,
        ),
    ]

    signal = SignalSelection(
        primary_fact_id=(
            "trigger.payload.delta_pct"
        ),
        supporting_fact_ids=(),
        reason="strongest signal",
    )

    service = EngagementService(
        llm=FakeLLM(),
        validator=MessageValidator(),
    )

    result = service.compose(
        context=context,
        policy=policy,
        facts=facts,
        signal=signal,
    )

    assert result is not None

    assert "50%" in result.body

    assert result.send_as == "vera"

    assert result.cta == "open_ended"


def test_llm_failure_returns_grounded_fallback():

    context = build_context()

    policy = TriggerPolicy(
        kind="perf_dip",
        family="performance",
        priority=85,
        cta="open_ended",
        facts=(),
    )

    facts = [
        Fact(
            id="merchant.performance.calls",
            value="18",
            priority=100,
        ),
    ]

    signal = SignalSelection(
        primary_fact_id=(
            "merchant.performance.calls"
        ),
        supporting_fact_ids=(),
        reason="strongest signal",
    )

    service = EngagementService(
        llm=FailingLLM(),
        validator=MessageValidator(),
    )

    result = service.compose(
        context=context,
        policy=policy,
        facts=facts,
        signal=signal,
    )

    assert result is not None

    assert "18" in result.body

    assert result.send_as == "vera"
