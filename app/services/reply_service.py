from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Any

from app.core.context_store import ContextStore
from app.core.conversation_store import ConversationStore
from app.llm.base import BaseLLM
from app.services.context_resolver import ContextResolver
from app.services.fact_projector import FactProjector
from app.services.validation_service import ValidationService


ReplyAction = Literal["reply", "send", "wait", "end"]


@dataclass(frozen=True)
class ReplyDecision:
    action: ReplyAction
    body: str | None = None
    cta: str | None = None
    wait_seconds: int | None = None
    reason: str | None = None


class ReplyService:
    """
    Handles multi-turn conversation replies (/v1/reply):
    1. Detects hostile opt-outs ("stop", "spam", "not interested") -> action: "end"
    2. Detects auto-reply loops ("thank you for contacting...", "we will get back") -> action: "end"
    3. Detects intent transitions (commitment -> action mode vs qualification)
    4. Generates grounded LLM or fallback reply
    """

    AUTO_REPLY_PATTERNS = [
        r"thank you for contacting",
        r"thank you for reaching out",
        r"our team will respond",
        r"will get back to you",
        r"automated response",
        r"auto-reply",
        r"automatic reply",
        r"busy right now",
    ]

    HOSTILE_PATTERNS = [
        r"\bstop\b",
        r"\bspam\b",
        r"not interested",
        r"leave me alone",
        r"unsubscribe",
        r"useless",
        r"don'?t message me",
        r"stop messaging",
        r"opt-?out",
    ]

    COMMITMENT_PATTERNS = [
        r"\b(ok|okay|yes|yeah|sure)\b.*(do it|proceed|go ahead|let'?s|confirm)",
        r"\b(do it|proceed|go ahead|let'?s do it|sounds good|agree)\b",
        r"what'?s next",
    ]

    def __init__(
        self,
        context_store: ContextStore,
        conversation_store: ConversationStore,
        resolver: ContextResolver | None = None,
        projector: FactProjector | None = None,
        llm: BaseLLM | None = None,
        validator: ValidationService | None = None,
    ) -> None:
        self.context_store = context_store
        self.conversation_store = conversation_store
        self.resolver = resolver or ContextResolver(context_store)
        self.projector = projector or FactProjector()
        self.llm = llm
        self.validator = validator or ValidationService()

    def process_reply(
        self,
        conversation_id: str,
        merchant_id: str,
        customer_id: str | None,
        from_role: str,
        message: str,
        received_at: str,
        turn_number: int,
    ) -> ReplyDecision:

        # Track conversation history in ConversationStore
        state = self.conversation_store.get_or_create(
            conversation_id=conversation_id,
            merchant_id=merchant_id,
            customer_id=customer_id,
            now=received_at,
        )
        self.conversation_store.add_turn(
            conversation_id=conversation_id,
            speaker="user",
            text=message,
            timestamp=received_at,
        )

        message_clean = message.strip()
        message_lower = message_clean.lower()

        # -----------------------------------------------------
        # 1. Hostile / Opt-out check
        # -----------------------------------------------------
        for pattern in self.HOSTILE_PATTERNS:
            if re.search(pattern, message_lower):
                self.conversation_store.set_status(conversation_id, "ended")
                return ReplyDecision(
                    action="end",
                    reason="User opted out or requested to stop.",
                )

        # -----------------------------------------------------
        # 2. Auto-reply detection check
        # -----------------------------------------------------
        for pattern in self.AUTO_REPLY_PATTERNS:
            if re.search(pattern, message_lower):
                self.conversation_store.set_status(conversation_id, "ended")
                return ReplyDecision(
                    action="end",
                    reason="Auto-reply loop detected.",
                )

        # -----------------------------------------------------
        # 3. Commitment / Intent transition check
        # -----------------------------------------------------
        is_commitment = any(
            re.search(pattern, message_lower) for pattern in self.COMMITMENT_PATTERNS
        )

        # Fetch context information
        merchant = self.context_store.get("merchant", merchant_id)
        owner_name = "there"
        business_name = "your business"
        if merchant and isinstance(merchant.payload, dict):
            identity = merchant.payload.get("identity", {})
            owner_name = identity.get("owner_first_name") or identity.get("name") or "there"
            business_name = identity.get("name") or "your business"

        # -----------------------------------------------------
        # 4. LLM Generation (if LLM is configured)
        # -----------------------------------------------------
        if self.llm is not None:
            prompt = self._build_reply_prompt(
                owner_name=owner_name,
                business_name=business_name,
                user_message=message_clean,
                is_commitment=is_commitment,
                history=state.turns,
            )
            try:
                draft = self.llm.generate(prompt)
                body = draft.body.strip()
                if body and not self.validator.URL_REGEX.search(body):
                    self.conversation_store.add_turn(
                        conversation_id=conversation_id,
                        speaker="vera",
                        text=body,
                        timestamp=received_at,
                    )
                    return ReplyDecision(
                        action="reply",
                        body=body,
                        cta=draft.cta or ("action" if is_commitment else "open_ended"),
                        reason="LLM generated conversation reply.",
                    )
            except Exception:
                pass

        # -----------------------------------------------------
        # 5. Deterministic Fallback
        # -----------------------------------------------------
        if is_commitment:
            body = (
                f"Great {owner_name}! Done, proceeding with the next step for {business_name}. "
                f"Here is the draft update ready to confirm."
            )
            self.conversation_store.add_turn(
                conversation_id=conversation_id,
                speaker="vera",
                text=body,
                timestamp=received_at,
            )
            return ReplyDecision(
                action="reply",
                body=body,
                cta="action",
                reason="Merchant committed; transitioned to action mode.",
            )

        body = (
            f"Understood {owner_name}. Regarding {business_name}, "
            f"we can adjust your target parameters or review your current performance. "
            f"Would you like me to proceed with the recommended settings?"
        )
        self.conversation_store.add_turn(
            conversation_id=conversation_id,
            speaker="vera",
            text=body,
            timestamp=received_at,
        )
        return ReplyDecision(
            action="reply",
            body=body,
            cta="open_ended",
            reason="General reply.",
        )

    def _build_reply_prompt(
        self,
        owner_name: str,
        business_name: str,
        user_message: str,
        is_commitment: bool,
        history: list[Any],
    ) -> str:
        history_text = "\n".join(
            f"{t.speaker.upper()}: {t.text}" for t in history[-6:]
        )
        mode = "ACTION MODE: The user has committed. Do NOT ask qualifying questions. Use words like 'done', 'proceeding', 'here is' to confirm action." if is_commitment else "QUALIFICATION / CONVERSATIONAL MODE: Respond directly and ask a single clear question."
        return f"""
You are Vera, magicpin's merchant AI assistant on WhatsApp.

CONTEXT:
Merchant Owner: {owner_name}
Business Name: {business_name}
Mode: {mode}

RECENT CONVERSATION HISTORY:
{history_text}

USER MESSAGE:
{user_message}

RULES:
1. Speak concisely in helpful WhatsApp assistant tone.
2. NEVER invent prices, percentages, dates, or URLs.
3. If Mode is ACTION MODE, confirm action immediately with terms like 'done', 'here is', 'proceeding'.

Return structured JSON.
""".strip()
