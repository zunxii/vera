from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.context_store import ContextStore
from app.core.delivery_state import DeliveryState
from app.llm.fallback import FallbackLLM
from app.services.context_resolver import ContextResolver
from app.services.decision_selector import DecisionSelector
from app.services.engagement_service import EngagementService
from app.services.fact_projector import FactProjector
from app.services.message_validator import MessageValidator
from app.services.signal_selector import SignalSelector
from app.services.suppression_service import SuppressionService
from app.services.trigger_planner import TriggerPlanner
from app.services.validation_service import ValidationService


class TickEngine:
    """
    Orchestrates one proactive tick.

    Flow:

        available trigger IDs
            ↓
        TriggerPlanner
            ↓
        DecisionSelector
            ↓
        FactProjector
            ↓
        SignalSelector
            ↓
        EngagementService
            ↓
        Action validation
            ↓
        suppression state
    """

    def __init__(
        self,
        context_store: ContextStore,
        delivery_state: DeliveryState,
        resolver: ContextResolver | None = None,
        planner: TriggerPlanner | None = None,
        projector: FactProjector | None = None,
        engagement_service: EngagementService | None = None,
        suppression_service: SuppressionService | None = None,
        decision_selector: DecisionSelector | None = None,
        signal_selector: SignalSelector | None = None,
    ) -> None:

        self.context_store = context_store

        self.delivery_state = (
            delivery_state
        )

        self.resolver = (
            resolver
            or ContextResolver(
                context_store
            )
        )

        self.planner = (
            planner
            or TriggerPlanner(
                resolver=self.resolver,
                delivery_state=delivery_state,
            )
        )

        self.projector = (
            projector
            or FactProjector()
        )

        self.engagement_service = (
            engagement_service
            or EngagementService(
                llm=FallbackLLM(),
                validator=MessageValidator(),
            )
        )

        self.suppression_service = (
            suppression_service
            or SuppressionService(
                delivery_state
            )
        )

        self.decision_selector = (
            decision_selector
            or DecisionSelector()
        )

        self.signal_selector = (
            signal_selector
            or SignalSelector()
        )

    def process_tick(
        self,
        now: str,
        available_triggers: list[str],
    ) -> list[dict[str, Any]]:

        planned = self.planner.plan(
            now=now,
            trigger_ids=available_triggers,
            limit=20,
        )

        # -----------------------------------------------------
        # Decision quality:
        # choose one strongest signal per recipient.
        # -----------------------------------------------------

        selected = (
            self.decision_selector.select(
                planned
            )
        )

        def _compose_item(item):
            context = item.context
            policy = item.policy

            facts = self.projector.project(
                context=context,
                specs=policy.facts,
            )

            selection = self.signal_selector.select(
                context=context,
                policy=policy,
                facts=facts,
            )

            focused_facts = selection.focus(
                facts
            )

            composed = (
                self.engagement_service.compose(
                    context=context,
                    policy=policy,
                    facts=focused_facts,
                    signal=selection,
                )
            )

            return (item, composed)

        if len(selected) > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(len(selected), 8)) as executor:
                results = list(executor.map(_compose_item, selected))
        else:
            results = [_compose_item(item) for item in selected]

        actions: list[
            dict[str, Any]
        ] = []

        for item, composed in results:

            if composed is None:
                continue

            context = item.context

            merchant_id = (
                context.merchant.payload.get(
                    "merchant_id"
                )
            )

            if not merchant_id:
                continue

            customer_id = None

            if context.customer is not None:
                customer_id = (
                    context.customer.payload.get(
                        "customer_id"
                    )
                )

                if not customer_id:
                    continue

            trigger_id = (
                context.trigger.context_id
            )

            # Every proactive initiation gets
            # a fresh conversation ID.
            conversation_id = (
                f"conv_{uuid4().hex}"
            )

            action = {
                "conversation_id": conversation_id,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "send_as": composed.send_as,
                "trigger_id": trigger_id,
                "template_name": composed.template_name,
                "template_params": (
                    composed.template_params
                ),
                "body": composed.body,
                "cta": composed.cta,
                "suppression_key": (
                    composed.suppression_key
                ),
                "rationale": composed.rationale,
            }

            if not ValidationService.validate_action(
                action
            ):
                continue

            actions.append(action)

            if composed.suppression_key:
                self.suppression_service.mark_sent(
                    composed.suppression_key
                )

            # Keep hard protocol cap.
            if len(actions) >= 20:
                break

        return actions
