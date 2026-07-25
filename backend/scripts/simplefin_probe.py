"""Probe a SimpleFIN Bridge account and report anything that would break sync.

Runs against the public demo server by default, so it needs no credentials:

    uv run python scripts/simplefin_probe.py
    uv run python scripts/simplefin_probe.py --access-url "https://user:pass@host/simplefin"
    uv run python scripts/simplefin_probe.py --setup-token "<base64 token>"

Read-only. Touches no database.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import simplefin  # noqa: E402

DEMO_ACCESS_URL = "https://demo:demo@beta-bridge.simplefin.org/simplefin"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--access-url", default=os.getenv("SIMPLEFIN_ACCESS_URL"))
    parser.add_argument("--setup-token", help="claim this token first (single use)")
    parser.add_argument("--days", type=int, default=120, help="history to request (default 120, > the 90d cap)")
    args = parser.parse_args()

    if args.setup_token:
        access_url = simplefin.claim_setup_token(args.setup_token)
        print(f"Claimed access URL: {simplefin.redact(access_url)}")
    elif args.access_url:
        access_url = args.access_url
    else:
        access_url = DEMO_ACCESS_URL
        print("No --access-url given; using the public demo server.\n")

    end_date = datetime.now(timezone.utc).date() + timedelta(days=1)
    start_date = end_date - timedelta(days=args.days)

    print(f"Endpoint: {simplefin.redact(access_url)}")
    print(f"Window:   {start_date} .. {end_date} ({args.days} days, unsplit)\n")

    payload = simplefin.fetch_accounts(access_url, start_date, end_date, pending=True)

    problems: list[str] = []

    for err in payload.get("errlist") or []:
        msg = err.get("msg") if isinstance(err, dict) else str(err)
        print(f"  errlist: {msg}")
        # "was capped" is an actual truncation; "may be capped" is only a
        # warning that the window exceeds the recommended 45 days.
        if "was capped" in str(msg).lower():
            problems.append("Date range was silently capped -- backfill must page.")
        elif "exceeds recommended range" in str(msg).lower():
            problems.append(f"Window exceeds the recommended size: {msg}")
    for msg in payload.get("x-api-message") or []:
        print(f"  x-api-message: {msg}")

    accounts = payload.get("accounts", [])
    print(f"\n{len(accounts)} account(s)\n")

    global_ids: Counter[str] = Counter()
    field_usage: Counter[str] = Counter()
    total_txns = 0
    unparseable = 0
    pending_count = 0

    for account in accounts:
        txns = account.get("transactions") or []
        total_txns += len(txns)
        dates = []
        local_ids = Counter()

        for txn in txns:
            # Count non-null values, not key presence: real institutions send
            # keys like "mcc" with a null value, which is not the same as
            # actually providing the data.
            for key, value in txn.items():
                if value is not None and value != "":
                    field_usage[key] += 1
            txn_id = str(txn.get("id", ""))
            local_ids[txn_id] += 1
            global_ids[txn_id] += 1
            try:
                simplefin.parse_amount(txn.get("amount"))
                dates.append(simplefin.transaction_date(txn))
            except simplefin.SimpleFinError as exc:
                unparseable += 1
                problems.append(f"Unparseable transaction in {account.get('id')}: {exc}")
            if txn.get("pending") or int(txn.get("posted") or 0) == 0:
                pending_count += 1

        span = f"{min(dates)} .. {max(dates)}" if dates else "no transactions"
        print(f"  {account.get('id')!r} -- {account.get('name')}")
        print(f"     balance {account.get('balance')} {account.get('currency')} "
              f"as of {simplefin.parse_timestamp(account['balance-date'])}")
        print(f"     {len(txns)} txns, {span}")
        if account.get("holdings"):
            print(f"     {len(account['holdings'])} investment holding(s)")

        dupes = [i for i, n in local_ids.items() if n > 1]
        if dupes:
            problems.append(
                f"Account {account.get('id')} returned repeated ids {dupes[:3]} -- "
                "ids are not unique even within the account."
            )

    cross_account = [i for i, n in global_ids.items() if n > 1]
    if cross_account:
        problems.append(
            f"{len(cross_account)} transaction id(s) appear in more than one account "
            f"(e.g. {cross_account[:3]}) -- external_id alone is NOT a valid unique key."
        )

    print(f"\nTotals: {total_txns} transactions, {pending_count} pending, {unparseable} unparseable")
    print("\nField frequency across all transactions:")
    for key, count in field_usage.most_common():
        coverage = 100 * count / total_txns if total_txns else 0
        print(f"  {key:<16} {count:>5}  ({coverage:.0f}%)")

    for required in ("id", "posted", "amount", "description"):
        if total_txns and field_usage[required] < total_txns:
            problems.append(f"Required field {required!r} missing on some transactions.")
    if total_txns and field_usage["pending"] == 0:
        print("\nNote: no transaction carried a 'pending' field -- it is optional and "
              "absent here, so treat missing as posted.")

    print("\n" + "=" * 70)
    if problems:
        print("ISSUES FOUND:")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("No issues found in this payload.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
