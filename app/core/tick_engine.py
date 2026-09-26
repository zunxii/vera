from __future__ import annotations

from typing import Any

from app.composers.registry import ComposerRegistry
from app.core.context_store import ContextStore
from app.core.delivery_state import DeliveryState
from app.services.context_resolver import ContextResolver
from app.services.fact_projector import FactProjector
from app.services.suppression_service import SuppressionService
from app.services.trigger_planner import TriggerPlanner
from app.services.validation_service import ValidationService


class TickEngine:
    """
    Orchestrates tick processing:
    1. Plan triggers via TriggerPlanner (filters expired, suppressed, non-proactive)
    2. Project policy-approved facts via FactProjector
    3. Compose action via ComposerRegistry
    4. Validate action via ValidationService
    5. Record suppression state
    """

    def __init__(
        self,
        context_store: ContextStore,
        delivery_state: DeliveryState,
        resolver: ContextResolver | None = None,
        planner: TriggerPlanner | None = None,
        projector: FactProjector | None = None,
        composer_registry: ComposerRegistry | None = None,
        suppression_service: SuppressionService | None = None,
    ) -> None:
        self.context_store = context_store
        self.delivery_state = delivery_state
        self.resolver = resolver or ContextResolver(context_store)
        self.planner = planner or TriggerPlanner(
            resolver=self.resolver,
            delivery_state=delivery_state,
        )
        self.projector = projector or FactProjector()
        self.registry = composer_registry or ComposerRegistry()
        self.suppression_service = (
            suppression_service or SuppressionService(delivery_state)
        )

    def process_tick(
        self,
        now: str,
        available_triggers: list[str],
    ) -> list[dict[str, Any]]:
        planned_triggers = self.planner.plan(
            now=now,
            trigger_ids=available_triggers,
        )

        actions: list[dict[str, Any]] = []

        for item in planned_triggers:
            context = item.context
            policy = item.policy

            facts = self.projector.project(
                context=context,
                specs=policy.facts,
            )

            composed = self.registry.compose(
                context=context,
                policy=policy,
                facts=facts,
            )

            if composed is None:
                continue

            merchant_id = context.merchant.payload.get("merchant_id", "")
            customer_id = (
                context.customer.payload.get("customer_id")
                if context.customer
                else None
            )

            trigger_id = context.trigger.context_id

            if customer_id:
                conversation_id = f"conv_{customer_id}_{trigger_id}"
            else:
                conversation_id = f"conv_{merchant_id}_{trigger_id}"

            action = {
                "conversation_id": conversation_id,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "send_as": composed.send_as,
                "trigger_id": trigger_id,
                "template_name": composed.template_name,
                "template_params": composed.template_params,
                "body": composed.body,
                "cta": composed.cta,
                "suppression_key": composed.suppression_key,
                "rationale": composed.rationale,
            }

            if not ValidationService.validate_action(action):
                continue

            actions.append(action)

            if composed.suppression_key:
                self.suppression_service.mark_sent(composed.suppression_key)

        return actions
