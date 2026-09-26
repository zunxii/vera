from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


SpeakerRole = Literal["user", "vera"]
ConversationStatus = Literal["active", "waiting", "ended"]


@dataclass(frozen=True)
class ConversationTurn:
    """Single turn in a multi-turn conversation."""

    speaker: SpeakerRole
    text: str
    timestamp: str


@dataclass
class ConversationState:
    """In-memory state of an ongoing multi-turn conversation."""

    conversation_id: str
    merchant_id: str
    customer_id: str | None = None
    trigger_id: str | None = None
    status: ConversationStatus = "active"
    turns: list[ConversationTurn] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def add_turn(
        self,
        speaker: SpeakerRole,
        text: str,
        timestamp: str,
    ) -> None:
        self.turns.append(
            ConversationTurn(
                speaker=speaker,
                text=text,
                timestamp=timestamp,
            )
        )
        self.updated_at = timestamp

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def user_turn_count(self) -> int:
        return sum(1 for turn in self.turns if turn.speaker == "user")

    @property
    def last_user_turn(self) -> ConversationTurn | None:
        for turn in reversed(self.turns):
            if turn.speaker == "user":
                return turn
        return None
