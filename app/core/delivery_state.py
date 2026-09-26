from __future__ import annotations

from threading import RLock


class DeliveryState:
    """
    Tracks proactive messages already sent.

    suppression_key is the challenge-provided deduplication key.
    """

    def __init__(self) -> None:
        self._sent_keys: set[str] = set()
        self._lock = RLock()

    def was_sent(
        self,
        suppression_key: str,
    ) -> bool:
        if not suppression_key:
            return False

        with self._lock:
            return (
                suppression_key
                in self._sent_keys
            )

    def mark_sent(
        self,
        suppression_key: str,
    ) -> None:
        if not suppression_key:
            return

        with self._lock:
            self._sent_keys.add(
                suppression_key
            )

    def clear(self) -> None:
        with self._lock:
            self._sent_keys.clear()
