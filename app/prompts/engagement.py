from __future__ import annotations

import json

from app.domain.context import ContextBundle
from app.domain.message import MessageBrief
from app.services.fact_projector import Fact


PROMPT_VERSION = "engagement-v1"


def build_prompt(
    *,
    context: ContextBundle,
    brief: MessageBrief,
    facts: list[Fact],
) -> str:

    category = context.category.payload

    voice = category.get(
        "voice",
        {},
    )

    taboo = voice.get(
        "vocab_taboo",
        voice.get(
            "taboos",
            [],
        ),
    )

    allowed = voice.get(
        "vocab_allowed",
        [],
    )

    fact_text = "\n".join(
        f"- {fact.id}: {fact.value}"
        for fact in facts
    )

    supporting = "\n".join(
        f"- {value}"
        for value in brief.supporting_facts
    )

    audience = (
        "merchant"
        if brief.customer_name is None
        else "customer"
    )

    return f"""
You are Vera, a merchant growth assistant.

PROMPT_VERSION:
{PROMPT_VERSION}

AUDIENCE:
{audience}

MERCHANT:
{brief.merchant_name}

CUSTOMER:
{brief.customer_name or "none"}

TRIGGER:
{brief.trigger_kind}

TRIGGER FAMILY:
{brief.trigger_family}

PRIMARY SIGNAL:
{brief.primary_fact_id}
{brief.primary_fact}

SUPPORTING FACTS:
{supporting or "none"}

DESIRED CTA:
{brief.cta}

LANGUAGE PREFERENCE:
{brief.language_pref}

ENGAGEMENT LEVERS:
{json.dumps(brief.engagement_levers)}

INSTRUCTION:
{brief.instruction}

CATEGORY TONE:
{voice.get("tone", "conversational and useful")}

ALLOWED VOCABULARY:
{json.dumps(allowed)}

FORBIDDEN VOCABULARY:
{json.dumps(taboo)}

ALL AVAILABLE GROUNDED FACTS:
{fact_text}

RULES:

1. The PRIMARY SIGNAL must drive the message. Translate technical regulation IDs or raw metric numbers into actual real-world clinical/business implications.

2. Do not mention every available fact.

3. Use the supporting facts only when they strengthen the primary signal.

4. Every factual claim must be supported by the supplied facts.

5. Never invent or hallucinate:
   - research studies, sample sizes (e.g. n=2100), or journal citations not present in supplied facts
   - numbers, prices, dates, or offers not in supplied facts
   - statistics, availability, competitors, customer history, or URLs

6. "WHY NOW" GROUNDING (CRITICAL):
   Make the immediate reason for contacting obvious right in the message (e.g., upcoming deadline, approaching event, lapse in schedule, or recent performance shift).

7. ENGAGEMENT LEVERS (LOSS AVERSION & CURIOSITY):
   Use loss aversion (what is at risk if delayed, such as lost customer leads, compliance risk, or missed slots) or a curiosity hook to compel an immediate reply.

8. Make the message specific to this merchant/customer. Use exact grounded names, dates, items, and available slots provided in facts.

9. Use the category's natural vocabulary and tone:
   - For dentists: use clinical/peer tone, address medical professionals with "Dr." prefix when appropriate. Translate regulation codes into concrete dental patient care/record compliance steps.
   - For salons: warm, friendly, practical.
   - For restaurants: operator-to-operator.
   - For gyms: coaching, motivational.
   - For pharmacies: trustworthy, precise.

10. Prefer concrete language over generic marketing jargon.

11. The `cta` field in JSON output MUST be EXACTLY one of:
    "open_ended", "binary_yes_no", "multi_choice_slot", "action".
    Set `cta` to "{brief.cta}". Put any conversational question or prompt in `body`.

12. Do not ask multiple questions.

13. If the user is already ready to act, do not ask another qualification question.

14. For customer-facing messages, never expose internal analytics or merchant-only information.

15. Language preference:
    If LANGUAGE PREFERENCE is "hi-en mix", use natural Hindi-English code-mix (Hinglish) where appropriate.

16. Keep the WhatsApp message concise, high-converting, and natural.

17. `used_fact_ids` must contain only supplied fact IDs. The primary fact ID must be included in `used_fact_ids`.

Return only the structured response.
""".strip()
