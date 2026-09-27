from __future__ import annotations

import json
import logging
import time
from groq import Groq

from app.llm.base import BaseLLM
from app.llm.schemas import LLMMessageDraft

logger = logging.getLogger(__name__)


class GroqLLM(BaseLLM):
    """
    Groq-backed LLM provider.
    Uses high-throughput models (openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b)
    with structured JSON schema enforcement.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-oss-120b",
    ) -> None:

        if not api_key:
            raise ValueError("GROQ_API_KEY is required.")

        self.model = model or "openai/gpt-oss-120b"
        self.client = Groq(api_key=api_key, timeout=15.0)

    def generate(
        self,
        prompt: str,
    ) -> LLMMessageDraft:

        models_to_try = [
            self.model,
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
        ]
        # De-duplicate while preserving order
        seen = set()
        models = [m for m in models_to_try if not (m in seen or seen.add(m))]

        system_prompt = (
            "You are Vera, magicpin's merchant growth assistant on WhatsApp. "
            "You MUST respond ONLY with a valid JSON object matching this exact schema strictly:\n"
            "{\n"
            '  "body": "string (the natural, concise WhatsApp message text)",\n'
            '  "cta": "string (MUST be one of: open_ended, binary_yes_no, multi_choice_slot, action)",\n'
            '  "send_as": "string (vera or merchant_on_behalf)",\n'
            '  "template_name": "string",\n'
            '  "template_params": ["string"],\n'
            '  "used_fact_ids": ["string"],\n'
            '  "rationale": "string"\n'
            "}\n"
            "Do not output markdown codeblocks. Output only the JSON object."
        )

        last_exc = None

        for model_name in models:
            for attempt in range(2):
                try:
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.2,
                        max_tokens=1024,
                    )

                    content = response.choices[0].message.content
                    if content:
                        return LLMMessageDraft.model_validate_json(content)
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Groq model %s attempt %d failed: %s", model_name, attempt + 1, exc)
                    time.sleep(0.5 * (attempt + 1))

        if last_exc:
            logger.error("All Groq model attempts exhausted: %s", last_exc)
            raise last_exc

        raise RuntimeError("Groq returned an empty response.")
