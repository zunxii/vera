from __future__ import annotations

from dataclasses import dataclass

from app.services.fact_projector import Fact


@dataclass(frozen=True)
class SignalSelection:
    """
    The single signal chosen to drive a message,
    plus a small set of supporting facts.
    """

    primary_fact_id: str
    supporting_fact_ids: tuple[str, ...]
    reason: str

    @property
    def fact_ids(self) -> tuple[str, ...]:
        return (
            self.primary_fact_id,
            *self.supporting_fact_ids,
        )

    def focus(
        self,
        facts: list[Fact],
    ) -> list[Fact]:

        by_id = {
            fact.id: fact
            for fact in facts
        }

        return [
            by_id[fact_id]
            for fact_id in self.fact_ids
            if fact_id in by_id
        ]
