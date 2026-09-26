from __future__ import annotations

from google import genai
from google.genai import types

from app.llm.base import BaseLLM
from app.llm.schemas import LLMMessageDraft


class GeminiLLM(BaseLLM):
    """
    Gemini-backed LLM provider.

    The model is forced to return the Pydantic schema
    defined by LLMMessageDraft.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
    ) -> None:

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required."
            )

        self.model = model

        self.client = genai.Client(
            api_key=api_key
        )

    def generate(
        self,
        prompt: str,
    ) -> LLMMessageDraft:

        response = (
            self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type=(
                        "application/json"
                    ),
                    response_schema=(
                        LLMMessageDraft
                    ),
                    temperature=0.2,
                ),
            )
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        return LLMMessageDraft.model_validate_json(
            response.text
        )
