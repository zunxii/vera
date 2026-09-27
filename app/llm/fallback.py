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
        raise RuntimeError("LLM provider unavailable")
