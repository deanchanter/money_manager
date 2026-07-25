"""Claim the SimpleFIN setup token from .env, once.

    cd backend && uv run python scripts/simplefin_setup.py

Reads the setup token from .env (SIMPLEFIN_SETUP_TOKEN, or simpleFIN), exchanges
it for a permanent access URL, and writes SIMPLEFIN_ACCESS_URL back to the same
.env before doing anything else.

Setup tokens are SINGLE USE. If the exchange succeeds but the result is lost,
a new token must be generated in the SimpleFIN Bridge UI. That is why the
access URL is persisted to .env immediately, ahead of any database work.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from bootstrap import init_db  # noqa: E402
from database import SessionLocal  # noqa: E402
from services import simplefin  # noqa: E402


def main() -> int:
    print(f"Using env file: {config.ENV_FILE}")

    existing = config.get_access_url()
    if existing:
        print(f"Already connected: {simplefin.redact(existing)}")
        print("Delete SIMPLEFIN_ACCESS_URL from .env to re-connect with a new token.")
        return 0

    setup_token = config.get_setup_token()
    if not setup_token:
        print(
            "No setup token found. Add one to .env as:\n"
            "  SIMPLEFIN_SETUP_TOKEN=<token from https://beta-bridge.simplefin.org/>",
            file=sys.stderr,
        )
        return 1

    print("Claiming setup token (single use)...")
    try:
        access_url = simplefin.claim_setup_token(setup_token)
    except simplefin.SimpleFinError as exc:
        print(f"Claim failed: {exc}", file=sys.stderr)
        return 1

    # Persist before anything else can fail.
    env_file = config.save_access_url(access_url)
    print(f"Access URL saved to {env_file} as SIMPLEFIN_ACCESS_URL")
    print(f"Endpoint: {simplefin.redact(access_url)}")

    try:
        payload = simplefin.fetch_accounts(access_url, balances_only=True)
    except simplefin.SimpleFinError as exc:
        print(f"\nSaved, but the first request failed: {exc}", file=sys.stderr)
        return 1

    connections = payload.get("connections") or []
    org_name = connections[0].get("org_name", "") if connections else ""

    init_db()
    db = SessionLocal()
    try:
        simplefin.store_access_url(db, access_url, org_name)
    finally:
        db.close()

    accounts = payload.get("accounts", [])
    print(f"\nConnected to {org_name or 'SimpleFIN'} -- {len(accounts)} account(s) visible:\n")
    for account in accounts:
        print(f"  id={account.get('id')}")
        print(f"     {account.get('name')}  |  balance {account.get('balance')} {account.get('currency')}")
    for err in payload.get("errlist") or []:
        print(f"  error: {err.get('msg') if isinstance(err, dict) else err}")

    print(
        "\nNext: link each of these to a local account on the Sync page "
        "(http://localhost:3000/sync), then run a sync."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
