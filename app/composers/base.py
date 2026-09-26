from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.composers.models import ComposedMessage
from app.domain.context import ContextBundle
from app.policies.triggers import TriggerPolicy
from app.services.fact_projector import Fact


class BaseComposer(ABC):
    """
    Interface implemented by message composers.
    """

    @abstractmethod
    def compose(
        self,
        context: ContextBundle,
        policy: TriggerPolicy,
        facts: list[Fact],
    ) -> ComposedMessage | None:
        """
        Produce a ComposedMessage or None if trigger is not handled by this composer.
        """
        raise NotImplementedError

    def _pct(self, value: Any) -> str:
        """
        Convert decimal percentage values into readable percentages.
        """
        if not isinstance(value, (int, float)):
            return str(value)
        return f"{value * 100:+.0f}%"

    def _merchant_name(self, merchant: dict[str, Any]) -> str:
        identity = merchant.get("identity", {})
        return (
            identity.get("owner_first_name")
            or identity.get("name")
            or "there"
        )

    def _business_name(self, merchant: dict[str, Any]) -> str:
        return (
            merchant.get("identity", {}).get("name", "your business")
        )
