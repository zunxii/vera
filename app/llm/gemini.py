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

    Rate-limited to 6 requests per minute (shared across
    all threads) to stay under the free-tier quota.
    """

    _RPM = 6
    _WINDOW = 60.0
    _lock = threading.Lock()
    _timestamps: deque[float] = deque()

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

    def _wait_for_slot(self) -> None:
        """Block until a request slot is available."""
        with self._lock:
            now = time.monotonic()

            # Purge timestamps older than the window.
            while (
                self._timestamps
                and self._timestamps[0]
                <= now - self._WINDOW
            ):
                self._timestamps.popleft()

            if len(self._timestamps) >= self._RPM:
                # Wait until the oldest call exits
                # the window.
                wait = (
                    self._timestamps[0]
                    + self._WINDOW
                    - now
                    + 0.5  # small buffer
                )
            else:
                wait = 0.0

            self._timestamps.append(
                now + wait
            )

        if wait > 0:
            time.sleep(wait)

    def generate(
        self,
        prompt: str,
    ) -> LLMMessageDraft:

        models_to_try = [
            self.model,
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.7-flash",
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
                    time.sleep(0.5 * (attempt + 1))

        if last_exc:
            raise last_exc

        raise RuntimeError(
            "Gemini returned an empty response."
        )

