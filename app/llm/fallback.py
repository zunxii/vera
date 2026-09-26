from __future__ import annotations

from app.llm.base import BaseLLM
from app.llm.schemas import LLMMessageDraft


class FallbackLLM(BaseLLM):
    """
    Deterministic fallback used when no LLM is configured
    or the provider fails.

    This is NOT the final intelligence layer.
    It only guarantees graceful degradation.
    """

    def generate(
        self,
        prompt: str,
    ) -> LLMMessageDraft:

        return LLMMessageDraft(
            body=(
                "I spotted an update relevant to your business. "
                "Want me to unpack what it means and suggest "
                "the next step?"
            ),
            cta="open_ended",
            used_fact_ids=[],
            template_params=[],
            rationale=(
                "Fallback response used because the LLM "
                "provider was unavailable."
            ),
        )
