from __future__ import annotations

from app.core.context_store import ContextStore
from app.domain.context import ContextBundle


class ContextResolver:
    """Resolve the runtime context graph for a trigger."""

    def __init__(self, store: ContextStore) -> None:
        self.store = store

    def resolve(
        self,
        trigger_id: str,
    ) -> ContextBundle | None:

        trigger = self.store.get(
            "trigger",
            trigger_id,
        )

        if trigger is None:
            return None

        payload = trigger.payload

        merchant_id = payload.get(
            "merchant_id"
        )

        if not merchant_id:
            return None

        merchant = self.store.get(
            "merchant",
            merchant_id,
        )

        if merchant is None:
            return None

        category_slug = merchant.payload.get(
            "category_slug"
        )

        if not category_slug:
            return None

        category = self.store.get(
            "category",
            category_slug,
        )

        if category is None:
            return None

        scope = payload.get("scope")

        if scope == "merchant":
            return ContextBundle(
                trigger=trigger,
                merchant=merchant,
                category=category,
            )

        if scope != "customer":
            return None

        customer_id = payload.get(
            "customer_id"
        )

        if not customer_id:
            return None

        customer = self.store.get(
            "customer",
            customer_id,
        )

        if customer is None:
            return None

        owner = customer.payload.get(
            "merchant_id"
        )

        if owner and owner != merchant_id:
            return None

        return ContextBundle(
            trigger=trigger,
            merchant=merchant,
            category=category,
            customer=customer,
        )
