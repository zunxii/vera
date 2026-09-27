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

        from time import sleep

        models_to_try = [
            self.model,
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
        ]

        last_exc = None

        for model_name in models_to_try:
            for attempt in range(3):
                try:
                    response = (
                        self.client.models.generate_content(
                            model=model_name,
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

                    if response and response.text:
                        return LLMMessageDraft.model_validate_json(
                            response.text
                        )
                except Exception as exc:
                    last_exc = exc
                    sleep(1.0)

        if last_exc:
            raise last_exc

        raise RuntimeError(
            "Gemini returned an empty response."
        )
