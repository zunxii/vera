from __future__ import annotations

import time

from fastapi import FastAPI

from app.api.routes import router
from app.composers.llm_composer import LLMComposer
from app.composers.registry import ComposerRegistry
from app.core.config import Settings
from app.core.context_store import ContextStore
from app.core.conversation_store import ConversationStore
from app.core.delivery_state import DeliveryState
from app.core.tick_engine import TickEngine
from app.llm.gemini import GeminiLLM
from app.services.context_resolver import ContextResolver
from app.services.fact_projector import FactProjector
from app.services.reply_service import ReplyService
from app.services.trigger_planner import TriggerPlanner
from app.services.validation_service import ValidationService


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Keeping this as a factory makes the app easy to test.
    """

    settings = Settings()

    app = FastAPI(
        title="Vera — magicpin AI Challenge",
        version=settings.version,
        description=(
            "Stateful 4-context Engagement Engine: context store, planning, policy management, fact projection, and composition."
        ),
    )

    # Shared application state
    app.state.settings = settings

    store = ContextStore()
    delivery_state = DeliveryState()
    conversation_store = ConversationStore()

    context_resolver = ContextResolver(store)
    fact_projector = FactProjector()
    trigger_planner = TriggerPlanner(
        resolver=context_resolver,
        delivery_state=delivery_state,
    )

    app.state.context_store = store
    app.state.delivery_state = delivery_state
    app.state.conversation_store = conversation_store
    app.state.context_resolver = context_resolver
    app.state.fact_projector = fact_projector
    app.state.trigger_planner = trigger_planner

    # ---------------------------------------------------------
    # LLM Initialization
    # ---------------------------------------------------------
    validator = ValidationService()

    if settings.gemini_api_key:
        llm = GeminiLLM(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
        llm_composer = LLMComposer(
            llm=llm,
            validator=validator,
        )
    else:
        llm_composer = None

    composer_registry = ComposerRegistry(llm_composer=llm_composer)
    app.state.composer = composer_registry

    reply_service = ReplyService(
        context_store=store,
        conversation_store=conversation_store,
        resolver=context_resolver,
        projector=fact_projector,
        llm=llm if settings.gemini_api_key else None,
    )

    app.state.tick_engine = TickEngine(
        context_store=store,
        delivery_state=delivery_state,
        composer_registry=composer_registry,
    )
    app.state.reply_service = reply_service

    app.state.started_at = time.monotonic()

    # Register API routes
    app.include_router(router)

    return app


app = create_app()
