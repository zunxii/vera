from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.delivery_state import DeliveryState
from app.domain.context import ContextBundle
from app.policies.triggers import (
    TriggerPolicy,
    get_policy,
)
from app.services.context_resolver import ContextResolver


@dataclass(frozen=True)
class PlannedTrigger:
    context: ContextBundle
    policy: TriggerPolicy


class TriggerPlanner:
    """Prepare valid proactive trigger candidates."""

    def __init__(
        self,
        resolver: ContextResolver,
        delivery_state: DeliveryState,
    ) -> None:

        self.resolver = resolver
        self.delivery_state = delivery_state

    def plan(
        self,
        *,
        now: str,
        trigger_ids: list[str],
        limit: int = 20,
    ) -> list[PlannedTrigger]:

        now_dt = self._parse(
            now
        )

        candidates: list[
            PlannedTrigger
        ] = []

        for trigger_id in trigger_ids:

            context = self.resolver.resolve(
                trigger_id
            )

            if context is None:
                continue

            trigger = context.trigger.payload

            if self._expired(
                trigger.get("expires_at"),
                now_dt,
            ):
                continue

            suppression_key = (
                trigger.get(
                    "suppression_key",
                    "",
                )
            )

            if (
                suppression_key
                and self.delivery_state.was_sent(
                    suppression_key
                )
            ):
                continue

            policy = get_policy(
                trigger.get(
                    "kind",
                    "",
                )
            )

            if policy is None:
                continue

            if not policy.proactive:
                continue

            if (
                policy.customer_facing
                and context.customer is None
            ):
                continue

            candidates.append(
                PlannedTrigger(
                    context=context,
                    policy=policy,
                )
            )

        candidates.sort(
            key=lambda item: (
                -item.policy.priority,
                item.context.trigger.context_id,
            )
        )

        return candidates[:limit]

    @staticmethod
    def _parse(
        value: str,
    ) -> datetime:

        normalized = value.strip()

        if normalized.endswith("Z"):
            normalized = (
                normalized[:-1]
                + "+00:00"
            )

        result = datetime.fromisoformat(
            normalized
        )

        if result.tzinfo is None:
            result = result.replace(
                tzinfo=timezone.utc
            )

        return result

    @classmethod
    def _expired(
        cls,
        value: str | None,
        now: datetime,
    ) -> bool:

        if not value:
            return False

        try:
            expiry = cls._parse(
                value
            )
        except ValueError:
            return True

        return now >= expiry
