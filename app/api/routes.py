from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import JSONResponse

from app.api.models import (
    ContextAcceptedResponse,
    ContextRequest,
    ContextStaleResponse,
    HealthResponse,
    MetadataResponse,
    ReplyRequest,
    ReplyResponse,
    TickRequest,
    TickResponse,
)
from app.core.config import Settings
from app.core.context_store import ContextStore
from app.core.tick_engine import TickEngine
from app.services.reply_service import ReplyService


router = APIRouter(
    prefix="/v1",
)


def utc_now_z() -> str:
    return (
        datetime
        .now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


@router.get(
    "/healthz",
    response_model=HealthResponse,
)
def healthz(
    request: Request,
) -> HealthResponse:

    store: ContextStore = (
        request.app.state.context_store
    )

    started_at: float = (
        request.app.state.started_at
    )

    return HealthResponse(
        status="ok",
        uptime_seconds=max(
            0,
            int(
                time.monotonic()
                - started_at
            ),
        ),
        contexts_loaded=(
            store.counts()
        ),
    )


@router.get(
    "/metadata",
    response_model=MetadataResponse,
)
def metadata(
    request: Request,
) -> MetadataResponse:

    settings: Settings = (
        request.app.state.settings
    )

    return MetadataResponse(
        team_name=settings.team_name,
        team_members=list(
            settings.team_members
        ),
        model=settings.model,
        approach=settings.approach,
        contact_email=settings.contact_email,
        version=settings.version,
        submitted_at=settings.submitted_at,
    )


@router.post(
    "/context",
    response_model=(
        ContextAcceptedResponse
        | ContextStaleResponse
    ),
)
def push_context(
    request: Request,
    body: ContextRequest,
):
    store: ContextStore = (
        request.app.state.context_store
    )

    # ---------------------------------------------------------
    # Validate scope explicitly.
    # ---------------------------------------------------------

    if body.scope not in store.VALID_SCOPES:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "accepted": False,
                "reason": "invalid_scope",
                "details": (
                    "scope must be one of: "
                    + ", ".join(
                        sorted(
                            store.VALID_SCOPES
                        )
                    )
                ),
            },
        )

    result = store.put(
        scope=body.scope,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload,
    )

    # ---------------------------------------------------------
    # Older version -> 409 Conflict.
    # ---------------------------------------------------------

    if not result.accepted:
        assert (
            result.current_version
            is not None
        )

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "accepted": False,
                "reason": "stale_version",
                "current_version": result.current_version,
            },
        )

    # ---------------------------------------------------------
    # First version, update, or exact replay -> 200 OK.
    # ---------------------------------------------------------

    return ContextAcceptedResponse(
        accepted=True,
        ack_id=(
            f"ack_{body.context_id}"
            f"_v{body.version}"
        ),
        stored_at=utc_now_z(),
    )


@router.post(
    "/tick",
    response_model=TickResponse,
    status_code=status.HTTP_200_OK,
)
def tick(
    request: Request,
    body: TickRequest,
) -> TickResponse:
    tick_engine: TickEngine = (
        request.app.state.tick_engine
    )

    actions = tick_engine.process_tick(
        now=body.now,
        available_triggers=body.available_triggers,
    )

    return TickResponse(actions=actions)


@router.post(
    "/reply",
    response_model=ReplyResponse,
    status_code=status.HTTP_200_OK,
)
def reply(
    request: Request,
    body: ReplyRequest,
) -> ReplyResponse:
    reply_service: ReplyService = request.app.state.reply_service

    decision = reply_service.process_reply(
        conversation_id=body.conversation_id,
        merchant_id=body.merchant_id,
        customer_id=body.customer_id,
        from_role=body.from_role,
        message=body.message,
        received_at=body.received_at,
        turn_number=body.turn_number,
    )

    return ReplyResponse(
        action=decision.action,
        body=decision.body,
        cta=decision.cta,
        wait_seconds=decision.wait_seconds,
        rationale=decision.rationale,
    )

