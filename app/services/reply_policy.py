from __future__ import annotations

import re


OPT_OUT_PATTERNS = (
    r"\bstop messaging\b",
    r"\bstop contacting\b",
    r"\bdon'?t message me\b",
    r"\bdon'?t contact me\b",
    r"\bunsubscribe\b",
    r"\bopt[- ]?out\b",
    r"\bremove me\b",
    r"\bleave me alone\b",
)

HOSTILITY_PATTERNS = (
    r"\bspam\b",
    r"\buseless\b",
    r"\bstupid bot\b",
    r"\bfuck off\b",
    r"\bshut up\b",
)

WAIT_PATTERNS = (
    r"\blet me think\b",
    r"\bneed some time\b",
    r"\bgive me some time\b",
    r"\bi'?ll think about it\b",
    r"\bnot right now\b",
    r"\bmaybe later\b",
    r"\bcall me later\b",
    r"\bmessage me later\b",
    r"\bget back to you\b",
)

COMMITMENT_PATTERNS = (
    r"\bgo ahead\b",
    r"\blet'?s do it\b",
    r"\bdo it\b",
    r"\bproceed\b",
    r"\blet'?s start\b",
    r"\bstart it\b",
    r"\bbook it\b",
    r"\bwhat'?s next\b",
    r"^\s*(yes|yeah|yep|sure|okay|ok)\s*$",
    r"\bconfirm\b",
)


def matches_any(
    text: str,
    patterns: tuple[str, ...],
) -> bool:

    normalized = text.strip().lower()

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in patterns
    )


def is_opt_out(
    text: str,
) -> bool:

    return matches_any(
        text,
        OPT_OUT_PATTERNS,
    )


def is_hostile(
    text: str,
) -> bool:

    return matches_any(
        text,
        HOSTILITY_PATTERNS,
    )


def is_wait_request(
    text: str,
) -> bool:

    return matches_any(
        text,
        WAIT_PATTERNS,
    )


def is_commitment(
    text: str,
) -> bool:

    return matches_any(
        text,
        COMMITMENT_PATTERNS,
    )
