from __future__ import annotations

from threading import RLock

from app.domain.conversation import ConversationState, ConversationStatus, ConversationTurn, SpeakerRole


class ConversationStore:
    """
    Thread-safe in-memory store for tracking multi-turn conversation states.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._conversations: dict[str, ConversationState] = {}

    def get_or_create(
        self,
        conversation_id: str,
        merchant_id: str = "",
        customer_id: str | None = None,
        trigger_id: str | None = None,
        now: str = "",
    ) -> ConversationState:
        with self._lock:
            state = self._conversations.get(conversation_id)
            if state is None:
                state = ConversationState(
                    conversation_id=conversation_id,
                    merchant_id=merchant_id,
                    customer_id=customer_id,
                    trigger_id=trigger_id,
                    created_at=now,
                    updated_at=now,
                )
                self._conversations[conversation_id] = state
            else:
                if merchant_id and not state.merchant_id:
                    state.merchant_id = merchant_id
                if customer_id and not state.customer_id:
                    state.customer_id = customer_id
                if trigger_id and not state.trigger_id:
                    state.trigger_id = trigger_id
            return state

    def get(self, conversation_id: str) -> ConversationState | None:
        with self._lock:
            return self._conversations.get(conversation_id)

    def add_turn(
        self,
        conversation_id: str,
        speaker: SpeakerRole,
        text: str,
        timestamp: str,
    ) -> ConversationTurn:
        with self._lock:
            state = self._conversations.get(conversation_id)
            if state is None:
                state = ConversationState(
                    conversation_id=conversation_id,
                    merchant_id="",
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                self._conversations[conversation_id] = state
            state.add_turn(speaker, text, timestamp)
            return state.turns[-1]

    def set_status(
        self,
        conversation_id: str,
        status: ConversationStatus,
    ) -> None:
        with self._lock:
            state = self._conversations.get(conversation_id)
            if state is not None:
                state.status = status

    def clear(self) -> None:
        with self._lock:
            self._conversations.clear()
