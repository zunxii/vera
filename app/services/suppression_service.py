from __future__ import annotations

from app.core.delivery_state import DeliveryState


class SuppressionService:
    """
    Manages deduplication and suppression rules across tick cycles.
    """

    def __init__(self, delivery_state: DeliveryState) -> None:
        self.delivery_state = delivery_state

    def is_suppressed(self, suppression_key: str) -> bool:
        if not suppression_key:
            return False
        return self.delivery_state.was_sent(suppression_key)

    def mark_sent(self, suppression_key: str) -> None:
        if not suppression_key:
            return
        self.delivery_state.mark_sent(suppression_key)

    def clear(self) -> None:
        self.delivery_state.clear()
