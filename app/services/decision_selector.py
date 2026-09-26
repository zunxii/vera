from __future__ import annotations

from typing import Iterable

from app.services.trigger_planner import PlannedTrigger


class DecisionSelector:
    """
    Selects the strongest proactive signal per recipient.

    Merchant-facing:
        one winning signal per merchant per tick.

    Customer-facing:
        one winning signal per customer per tick.

    This prevents multiple competing proactive messages from
    the same merchant in one tick while preserving independent
    customer outreach.
    """

    def select(
        self,
        candidates: Iterable[PlannedTrigger],
    ) -> list[PlannedTrigger]:

        winners: dict[
            tuple[str, str],
            PlannedTrigger,
        ] = {}

        for candidate in candidates:

            context = candidate.context

            merchant_id = (
                context.merchant.payload.get(
                    "merchant_id"
                )
            )

            if not merchant_id:
                continue

            if context.customer is not None:

                recipient_id = (
                    context.customer.payload.get(
                        "customer_id"
                    )
                )

                if not recipient_id:
                    continue

                key = (
                    "customer",
                    str(recipient_id),
                )

            else:

                key = (
                    "merchant",
                    str(merchant_id),
                )

            current = winners.get(key)

            if current is None:
                winners[key] = candidate
                continue

            if self._better(
                candidate,
                current,
            ):
                winners[key] = candidate

        selected = list(
            winners.values()
        )

        selected.sort(
            key=lambda item: (
                -item.policy.priority,
                item.context.trigger.context_id,
            )
        )

        return selected

    @staticmethod
    def _better(
        candidate: PlannedTrigger,
        current: PlannedTrigger,
    ) -> bool:

        candidate_priority = (
            candidate.policy.priority
        )

        current_priority = (
            current.policy.priority
        )

        if candidate_priority != current_priority:
            return candidate_priority > current_priority

        candidate_urgency = candidate.context.trigger.payload.get(
            "urgency",
            0,
        )

        current_urgency = current.context.trigger.payload.get(
            "urgency",
            0,
        )

        if candidate_urgency != current_urgency:
            return candidate_urgency > current_urgency

        return (
            candidate.context.trigger.context_id
            < current.context.trigger.context_id
        )
