from __future__ import annotations

import re
from collections import defaultdict
from threading import RLock


class AutoReplyTracker:
    """
    Merchant-scoped tracker for repeated canned replies.

    The judge may use a different conversation_id for every
    repeated auto-reply, so tracking must not depend solely
    on conversation state.
    """

    MARKERS = (
        "thank you for contacting",
        "thank you for reaching out",
        "our team will respond",
        "we will get back to you",
        "we'll get back to you",
        "automated response",
        "automatic reply",
        "auto-reply",
        "auto reply",
        "business hours",
        "your message has been received",
    )

    def __init__(self) -> None:
        self._counts: defaultdict[
            tuple[str, str],
            int,
        ] = defaultdict(int)

        self._lock = RLock()

    def observe(
        self,
        *,
        merchant_id: str,
        message: str,
    ) -> int:

        if not self._looks_automated(
            message
        ):
            return 0

        fingerprint = self._normalize(
            message
        )

        key = (
            merchant_id,
            fingerprint,
        )

        with self._lock:
            self._counts[key] += 1
            return self._counts[key]

    def clear(self) -> None:
        with self._lock:
            self._counts.clear()

    @classmethod
    def _looks_automated(
        cls,
        message: str,
    ) -> bool:

        normalized = cls._normalize(
            message
        )

        return any(
            marker in normalized
            for marker in cls.MARKERS
        )

    @staticmethod
    def _normalize(
        message: str,
    ) -> str:

        value = message.lower().strip()

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        value = re.sub(
            r"[^\w\s]",
            "",
            value,
        )

        return value
