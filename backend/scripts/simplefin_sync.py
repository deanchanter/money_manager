"""Run a SimpleFIN sync from the command line.

    cd backend && uv run python scripts/simplefin_sync.py --days 30

Same operation as the Sync page's button, but talks to the database directly,
so it works without the API server running. Exits non-zero on failure.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bootstrap import init_db  # noqa: E402
from database import SessionLocal  # noqa: E402
from models import SimpleFinConnection  # noqa: E402
from services import simplefin  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30, help="days of history to pull")
    parser.add_argument("--no-pending", action="store_true", help="skip unsettled transactions")
    parser.add_argument("--no-anchor", action="store_true",
                        help="do not rewrite starting balances from SimpleFIN's reported balance")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        # Resolve the same way the API does: .env first, then the database.
        # Checking only the database missed connections claimed against a
        # different database file.
        access_url = simplefin.resolve_access_url(db)
        if not access_url:
            print(
                "No SimpleFIN connection. Run scripts/simplefin_setup.py first.",
                file=sys.stderr,
            )
            return 1

        result = simplefin.sync(
            db,
            access_url,
            days=args.days,
            pending=not args.no_pending,
            anchor_balances=not args.no_anchor,
        )
        connection = simplefin.get_connection(db)
        if not connection:
            connection = SimpleFinConnection(access_url=access_url)
            db.add(connection)
        connection.last_synced_at = datetime.utcnow()
        db.commit()
    except simplefin.SimpleFinError as exc:
        print(f"Sync failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(f"[{datetime.now():%Y-%m-%d %H:%M}] {result.as_dict()['message']}")
    for balance in result.balances:
        print(f"  {balance['account']}: {balance['reported_balance']} as of {balance['as_of']}")
    for warning in result.warnings:
        print(f"  warning: {warning}")
    for unlinked in result.unlinked_accounts:
        print(f"  unlinked: {unlinked['simplefin_account_id']} ({unlinked['name']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
