from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Any

from app.core.context_store import ContextStore
from app.core.conversation_store import ConversationStore
from app.llm.base import BaseLLM
from app.services.auto_reply_tracker import (
    AutoReplyTracker,
)
from app.services.context_resolver import ContextResolver
from app.services.fact_projector import FactProjector
from app.services.reply_policy import (
    is_commitment,
    is_hostile,
    is_opt_out,
    is_wait_request,
)
from app.services.validation_service import (
    ValidationService,
)


ReplyAction = Literal[
    "send",
    "wait",
    "end",
]


@dataclass(frozen=True)
class ReplyDecision:
    action: ReplyAction
    body: str | None = None
    cta: str | None = None
    wait_seconds: int | None = None
    rationale: str = ""


class ReplyService:
    """
    Handles one incoming merchant/customer reply.

    P0 responsibilities:
        - enforce valid action vocabulary
        - detect boundaries
        - detect repeated auto-replies
        - detect explicit wait requests
        - detect commitment
        - preserve conversation state
        - optionally use the existing LLM
    """

    AUTO_WAIT_SECONDS = 300

    def __init__(
        self,
        context_store: ContextStore,
        conversation_store: ConversationStore,
        resolver: ContextResolver | None = None,
        projector: FactProjector | None = None,
        llm: BaseLLM | None = None,
        validator: ValidationService | None = None,
        auto_reply_tracker: AutoReplyTracker | None = None,
    ) -> None:

        self.context_store = (
            context_store
        )

        self.conversation_store = (
            conversation_store
        )

        self.resolver = (
            resolver
            or ContextResolver(
                context_store
            )
        )

        self.projector = (
            projector
            or FactProjector()
        )

        self.llm = llm

        self.validator = (
            validator
            or ValidationService()
        )

        self.auto_reply_tracker = (
            auto_reply_tracker
            or AutoReplyTracker()
        )

    def process_reply(
        self,
        *,
        conversation_id: str,
        merchant_id: str,
        customer_id: str | None,
        from_role: str,
        message: str,
        received_at: str,
        turn_number: int,
    ) -> ReplyDecision:

        message_clean = (
            message.strip()
        )

        state = (
            self.conversation_store.get_or_create(
                conversation_id=conversation_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                now=received_at,
            )
        )

        self.conversation_store.add_turn(
            conversation_id=conversation_id,
            speaker="user",
            text=message_clean,
            timestamp=received_at,
        )

        # -----------------------------------------------------
        # Existing ended conversation
        # -----------------------------------------------------

        if state.status == "ended":
            return ReplyDecision(
                action="end",
                rationale=(
                    "Conversation is already closed."
                ),
            )

        # -----------------------------------------------------
        # 1. Opt-out
        # -----------------------------------------------------

        if is_opt_out(
            message_clean
        ):

            self.conversation_store.set_status(
                conversation_id,
                "ended",
            )

            return ReplyDecision(
                action="end",
                rationale=(
                    "The user explicitly requested "
                    "no further outreach."
                ),
            )

        # -----------------------------------------------------
        # 2. Hostility
        # -----------------------------------------------------

        if is_hostile(
            message_clean
        ):

            self.conversation_store.set_status(
                conversation_id,
                "ended",
            )

            return ReplyDecision(
                action="end",
                rationale=(
                    "Hostile or abusive response detected; "
                    "Vera exits instead of escalating."
                ),
            )

        # -----------------------------------------------------
        # 3. Repeated automated reply
        # -----------------------------------------------------

        auto_count = (
            self.auto_reply_tracker.observe(
                merchant_id=merchant_id,
                message=message_clean,
            )
        )

        if auto_count >= 3:

            self.conversation_store.set_status(
                conversation_id,
                "ended",
            )

            return ReplyDecision(
                action="end",
                rationale=(
                    "Repeated automated replies detected; "
                    "Vera exits the loop."
                ),
            )

        if auto_count == 2:

            self.conversation_store.set_status(
                conversation_id,
                "waiting",
            )

            return ReplyDecision(
                action="wait",
                wait_seconds=(
                    self.AUTO_WAIT_SECONDS
                    * 2
                ),
                rationale=(
                    "Repeated canned auto-reply detected; "
                    "Vera backs off instead of continuing."
                ),
            )

        if auto_count == 1:

            self.conversation_store.set_status(
                conversation_id,
                "waiting",
            )

            return ReplyDecision(
                action="wait",
                wait_seconds=(
                    self.AUTO_WAIT_SECONDS
                ),
                rationale=(
                    "Automated reply detected; "
                    "Vera waits rather than immediately "
                    "sending another message."
                ),
            )

        # -----------------------------------------------------
        # 4. Explicit wait request
        # -----------------------------------------------------

        if is_wait_request(
            message_clean
        ):

            self.conversation_store.set_status(
                conversation_id,
                "waiting",
            )

            return ReplyDecision(
                action="wait",
                wait_seconds=1800,
                rationale=(
                    "User asked for time or a later follow-up; "
                    "Vera backs off for 30 minutes."
                ),
            )

        # -----------------------------------------------------
        # 5. Commitment / action transition
        # -----------------------------------------------------

        committed = is_commitment(
            message_clean
        )

        self._set_intent(
            conversation_id,
            "committed"
            if committed
            else "conversation",
            received_at,
        )

        # -----------------------------------------------------
        # Context for fallback / prompt
        # -----------------------------------------------------

        merchant = (
            self.context_store.get(
                "merchant",
                merchant_id,
            )
        )

        owner_name = "there"
        business_name = "your business"

        if (
            merchant is not None
            and isinstance(
                merchant.payload,
                dict,
            )
        ):

            identity = merchant.payload.get(
                "identity",
                {},
            )

            if isinstance(
                identity,
                dict,
            ):
                owner_name = (
                    identity.get(
                        "owner_first_name"
                    )
                    or identity.get(
                        "name"
                    )
                    or "there"
                )

                business_name = (
                    identity.get(
                        "name"
                    )
                    or "your business"
                )

        # -----------------------------------------------------
        # 6. LLM
        # -----------------------------------------------------

        if self.llm is not None:

            prompt = (
                self._build_reply_prompt(
                    owner_name=owner_name,
                    business_name=business_name,
                    user_message=message_clean,
                    is_commitment=committed,
                    history=state.turns,
                )
            )

            try:

                draft = self.llm.generate(
                    prompt
                )

                body = draft.body.strip()

                if (
                    body
                    and not self.validator.URL_REGEX.search(
                        body
                    )
                ):

                    self.conversation_store.add_turn(
                        conversation_id=conversation_id,
                        speaker="vera",
                        text=body,
                        timestamp=received_at,
                    )

                    return ReplyDecision(
                        action="send",
                        body=body,
                        cta=(
                            draft.cta
                            or (
                                "action"
                                if committed
                                else "open_ended"
                            )
                        ),
                        rationale=(
                            draft.rationale
                            or (
                                "Responded using the "
                                "current conversation state."
                            )
                        ),
                    )

            except Exception:
                # Never break /reply because the LLM failed.
                pass

        # -----------------------------------------------------
        # 7. Deterministic fallback
        # -----------------------------------------------------

        if committed:

            body = (
                f"Done, {owner_name}. "
                f"I'm moving ahead with the next step "
                f"for {business_name}."
            )

            rationale = (
                "The merchant committed; Vera moved "
                "directly into action mode."
            )

            cta = "action"

        else:

            body = (
                f"Got it, {owner_name}. "
                f"I'll use the details we already have "
                f"for {business_name} and keep the next "
                f"step focused."
            )

            rationale = (
                "Acknowledged the message without inventing "
                "new business facts."
            )

            cta = "open_ended"

        self.conversation_store.add_turn(
            conversation_id=conversation_id,
            speaker="vera",
            text=body,
            timestamp=received_at,
        )

        self.conversation_store.set_status(
            conversation_id,
            "active",
        )

        return ReplyDecision(
            action="send",
            body=body,
            cta=cta,
            rationale=rationale,
        )

    def _set_intent(
        self,
        conversation_id: str,
        intent: str,
        now: str,
    ) -> None:

        _ = (
            conversation_id,
            intent,
            now,
        )

    def _build_reply_prompt(
        self,
        *,
        owner_name: str,
        business_name: str,
        user_message: str,
        is_commitment: bool,
        history: list[Any],
    ) -> str:

        history_text = "\n".join(
            (
                f"{turn.speaker.upper()}: "
                f"{turn.text}"
            )
            for turn in history[-6:]
        )

        if is_commitment:

            mode = (
                "ACTION MODE: the user has committed. "
                "Do not ask another qualification question. "
                "Confirm the next action."
            )

        else:

            mode = (
                "CONVERSATION MODE: respond to the user's "
                "message directly and keep the next step "
                "low-friction."
            )

        return f"""
You are Vera, magicpin's merchant AI assistant.

Merchant:
{owner_name}
{business_name}

Mode:
{mode}

Recent conversation:
{history_text}

Latest user message:
{user_message}

Rules:
1. Return one concise WhatsApp response.
2. Never invent prices, dates, metrics, offers, or URLs.
3. Use only facts actually present in the conversation.
4. In action mode, immediately acknowledge the commitment.
5. Do not ask multiple questions.
6. Return one clear CTA.
""".strip()
