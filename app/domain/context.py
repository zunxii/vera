from __future__ import annotations

from dataclasses import dataclass

from app.core.context_store import StoredContext


@dataclass(frozen=True)
class ContextBundle:
    """Resolved runtime context for one trigger."""

    trigger: StoredContext
    merchant: StoredContext
    category: StoredContext
    customer: StoredContext | None = None

    @property
    def customer_flow(self) -> bool:
        return self.customer is not None
