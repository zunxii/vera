from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.schemas import LLMMessageDraft


class BaseLLM(ABC):
    """
    Provider-agnostic LLM interface.

    We can later swap Gemini for another model
    without touching the composer or API.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
    ) -> LLMMessageDraft:
        raise NotImplementedError
