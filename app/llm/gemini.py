from __future__ import annotations

import threading
import time
from collections import deque

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
        model: str = "gemini-2.5-flash",
    ) -> None:

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required."
            )

        self.model = model or "gemini-2.5-flash"

        self.client = genai.Client(
            api_key=api_key
        )

    def generate(
        self,
        prompt: str,
    ) -> LLMMessageDraft:

        models_to_try = [
            self.model,
            "gemini-2.5-flash",
        ]
        # De-duplicate preserving order
        seen = set()
        models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

        last_exc = None

        for model_name in models_to_try:
            for attempt in range(2):
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
                    time.sleep(0.3 * (attempt + 1))

        if last_exc:
            raise last_exc

        raise RuntimeError(
            "Gemini returned an empty response."
        )

