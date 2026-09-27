#!/usr/bin/env python3
"""
One-off local-testing fix: dataset/triggers_seed.json was authored around
late April 2026, so every trigger's `expires_at` is already in the past by
the time you actually run judge_simulator.py months later.  TriggerPlanner
correctly drops expired triggers (that's per-spec, not a bug) — but it means
almost nothing survives to be composed in a local self-test.

This does NOT affect the real magicpin evaluation (the real judge generates
triggers with expires_at relative to the actual test's `now`).  It only
matters for testing judge_simulator.py against your own machine's clock.

Shifts every `expires_at` in dataset/triggers_seed.json forward by a fixed
number of days (default 200) so they're valid again, preserving relative
ordering/urgency semantics between triggers.  Run it once before local
testing:

    python scripts/refresh_seed_expiry.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "dataset" / "triggers_seed.json"


def parse(value: str) -> datetime:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--days",
        type=int,
        default=200,
        help="How many days to shift expires_at forward.",
    )
    args = parser.parse_args()

    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    items = data.get("triggers", [])

    delta = timedelta(days=args.days)
    shifted = 0

    for item in items:
        exp = item.get("expires_at")
        if not exp:
            continue
        try:
            new_dt = parse(exp) + delta
        except ValueError:
            continue
        item["expires_at"] = new_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        shifted += 1

    SEED_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Shifted expires_at forward by {args.days} days on {shifted} triggers.")
    print(f"Wrote {SEED_PATH}")


if __name__ == "__main__":
    main()
