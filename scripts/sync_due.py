#!/usr/bin/env python3
"""Decide whether a vendored refresh is due.

GitHub cron cannot express "every two weeks". The first attempt ran weekly and
skipped odd ISO weeks, which looks fortnightly and is not: ISO years with 53 weeks
break the parity, and iterating every Monday from 2026 to 2036 produces two
21-day gaps (2026-12-21 to 2027-01-11, and 2032-12-20 to 2033-01-10).

This decides from data instead of from the calendar. The manifest records
`pinned_at` per source, written by every sync. If the oldest of those is at least
`--interval-days` old, a refresh is due. No parity, no drift, and it self-heals: a
missed week is caught by the next run rather than waiting another fortnight.

    scripts/sync_due.py                     # exit 0 if due, 1 if not
    scripts/sync_due.py --interval-days 14
    scripts/sync_due.py --output json
    scripts/sync_due.py --self-test         # show the parity bug this replaced

Exit codes
    0  a refresh is due
    1  not due yet
    2  usage or environment error
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "skills" / "vendor.manifest.json"

# One day of slack. A scheduled run fires at a fixed UTC time, so "14 days since"
# can land a few minutes short and defer a whole week for no reason.
GRACE_DAYS = 1


def due(interval_days: int, today: dt.date) -> dict:
    if not MANIFEST_PATH.exists():
        print(f"error: missing {MANIFEST_PATH}", file=sys.stderr)
        raise SystemExit(2)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    sources = []
    for src in manifest.get("sources", []):
        raw = src.get("pinned_at")
        if not raw:
            sources.append({"id": src.get("id"), "pinned_at": None, "age_days": None})
            continue
        try:
            pinned = dt.date.fromisoformat(raw)
        except ValueError:
            print(
                f"error: [{src.get('id')}] pinned_at `{raw}` is not an ISO date", file=sys.stderr
            )
            raise SystemExit(2)
        sources.append(
            {"id": src.get("id"), "pinned_at": raw, "age_days": (today - pinned).days}
        )

    never_synced = [s for s in sources if s["age_days"] is None]
    ages = [s["age_days"] for s in sources if s["age_days"] is not None]
    oldest = max(ages) if ages else None

    if never_synced:
        verdict, reason = True, (
            f"{len(never_synced)} source(s) have never been synced: "
            + ", ".join(str(s["id"]) for s in never_synced)
        )
    elif oldest is None:
        verdict, reason = True, "the manifest declares no sources with a pin date"
    elif oldest >= interval_days - GRACE_DAYS:
        verdict, reason = True, (
            f"the oldest source was pinned {oldest} days ago, at or past the "
            f"{interval_days}-day interval"
        )
    else:
        verdict, reason = False, (
            f"the oldest source was pinned {oldest} days ago; next refresh in about "
            f"{interval_days - oldest} day(s)"
        )

    return {
        "due": verdict,
        "reason": reason,
        "today": today.isoformat(),
        "interval_days": interval_days,
        "oldest_age_days": oldest,
        "sources": sources,
    }


def self_test(interval_days: int) -> int:
    """Compare the replaced parity gate with this one over eleven years."""
    print("Even-ISO-week parity, every Monday 2026 through 2036:")
    day = dt.date(2026, 1, 5)
    runs = []
    while day.year <= 2036:
        if int(day.strftime("%V")) % 2 == 0:
            runs.append(day)
        day += dt.timedelta(days=7)
    gaps = {}
    anomalies = []
    for a, b in zip(runs, runs[1:]):
        delta = (b - a).days
        gaps[delta] = gaps.get(delta, 0) + 1
        if delta != 14:
            anomalies.append((a, b, delta))
    print(f"  runs={len(runs)} gap distribution={dict(sorted(gaps.items()))}")
    for a, b, delta in anomalies:
        print(f"  ANOMALY {a} (week {a.strftime('%V')}) -> {b} (week {b.strftime('%V')}): {delta} days")
    print()
    print("This gate instead measures elapsed days from manifest pinned_at, so the")
    print(f"interval can never exceed {interval_days} days plus one scheduler tick.")
    print()
    result = due(interval_days, dt.date.today())
    print(f"today: due={result['due']} because {result['reason']}")
    return 0 if anomalies else 1


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="Decide whether a vendored refresh is due.")
    ap.add_argument("--interval-days", type=int, default=14)
    ap.add_argument("--output", choices=("text", "json"), default="text")
    ap.add_argument("--today", help="override today's date (ISO) for testing")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.interval_days < 1:
        print("error: --interval-days must be at least 1", file=sys.stderr)
        return 2
    if args.self_test:
        return self_test(args.interval_days)

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    result = due(args.interval_days, today)

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"due={str(result['due']).lower()}")
        print(result["reason"])

    return 0 if result["due"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
