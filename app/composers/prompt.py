from __future__ import annotations

import json

from app.domain.context import ContextBundle
from app.policies.triggers import TriggerPolicy
from app.services.fact_projector import Fact


PROMPT_VERSION = "composer_v2"


def build_composer_prompt(
    *,
    context: ContextBundle,
    policy: TriggerPolicy,
    facts: list[Fact],
) -> str:
    category = context.category.payload
    merchant = context.merchant.payload
    customer = (
        context.customer.payload
        if context.customer
        else None
    )

    trigger = context.trigger.payload

    facts_text = "\n".join(
        f"- {fact.id}: {fact.value}"
        for fact in facts
    )

    voice = category.get("voice", {})
    tone = voice.get("tone", "professional and conversational")
    taboos = voice.get("taboos", []) or voice.get("vocab_taboo", [])

    customer_mode = (
        "CUSTOMER-FACING: You are writing on behalf of the merchant to their customer."
        if policy.customer_facing
        else "MERCHANT-FACING: You are Vera speaking directly to the merchant."
    )

    return f"""
You are Vera, magicpin's merchant AI assistant.

PROMPT VERSION:
{PROMPT_VERSION}

ROLE:
{customer_mode}

Your job is to produce ONE useful WhatsApp message.

============================================================
TRIGGER
============================================================

Trigger kind:
{policy.kind}

Trigger family:
{policy.family}

Trigger scope:
{trigger.get("scope")}

Trigger urgency:
{trigger.get("urgency")}

Why now:
This message exists because the above trigger happened now.

============================================================
POLICY
============================================================

CTA style:
{policy.cta}

Strategy:
Use the trigger to create a relevant reason to engage.
Do not make the message sound like generic marketing copy.

============================================================
CATEGORY VOICE
============================================================

Tone:
{tone}

Allowed vocabulary:
{json.dumps(voice.get("vocab_allowed", []), ensure_ascii=False)}

Forbidden/taboo vocabulary:
{json.dumps(taboos, ensure_ascii=False)}

============================================================
AVAILABLE FACTS
============================================================

You may ONLY use facts appearing below.

{facts_text}

============================================================
MERCHANT
============================================================

{json.dumps(merchant, ensure_ascii=False, default=str)}

============================================================
CUSTOMER
============================================================

{json.dumps(customer, ensure_ascii=False, default=str)}

============================================================
STRICT RULES
============================================================

1. NEVER invent facts.
2. NEVER invent prices, percentages, dates, statistics, competitors, appointments, or availability.
3. Every factual claim must be supported by one or more supplied fact IDs.
4. Include at least one concrete fact whenever the trigger provides one.
5. Make the trigger's "why now" obvious.
6. Make the message specific to this merchant/customer.
7. Keep the message concise.
8. Ask for ONE primary action matching the CTA style.
9. Never use forbidden/taboo category vocabulary.
10. `used_fact_ids` must contain IDs from the AVAILABLE FACTS only.

============================================================
OUTPUT
============================================================

Return only the requested structured JSON object.
""".strip()
