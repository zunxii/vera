from __future__ import annotations

import json
import time
from groq import Groq

from app.llm.base import BaseLLM
from app.llm.schemas import LLMMessageDraft


class GroqLLM(BaseLLM):
    """
    Groq-backed LLM provider.

    Uses high-throughput models (qwen/qwen3.8-27b, openai/gpt-oss-120b, etc.)
    with structured JSON schema enforcement and zero artificial rate limiting.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "qwen/qwen3.8-27b",
    ) -> None:

        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")

        self.model = model or "qwen/qwen3.8-27b"
        self.client = Groq(api_key=api_key, timeout=15.0)

    def generate(
        self,
        prompt: str,
    ) -> LLMMessageDraft:

        models_to_try = [
            self.model,
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ]
        # De-duplicate while preserving order
        seen = set()
        models = [m for m in models_to_try if not (m in seen or seen.add(m))]

        system_prompt = (
            "You are Vera, magicpin's merchant growth assistant on WhatsApp. "
            "You MUST respond ONLY with a valid JSON object matching the required schema strictly. "
            "Do not include any markdown formatting, backticks, or explanatory text outside the JSON object."
        )

        last_exc = None

        for model_name in models:
            for attempt in range(3):
                try:
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.2,
                        max_tokens=500,
                    )

                    content = response.choices[0].message.content
                    if content:
                        return LLMMessageDraft.model_validate_json(content)
                except Exception as exc:
                    last_exc = exc
                    time.sleep(0.5 * (attempt + 1))

        if last_exc:
            raise last_exc

        raise RuntimeError("Groq returned an empty response.")
