"""SimpleFIN Bridge client and sync.

Protocol notes that drove the shape of this module (verified against the demo
server, see scripts/simplefin_probe.py):

* A transaction `id` is only unique *within an account* -- the demo server
  returns the same id in two different accounts. Idempotency key is therefore
  (account_id, external_id), never external_id alone.
* Requesting a range longer than 90 days does NOT fail. The server silently
  caps the range and mentions it in `errlist`. Backfill must page. The server
  separately warns that anything over 45 days "may be capped" in future, so
  windows are 45 days.
* With no `start-date` the server only returns transactions since yesterday.
* Amounts are strings ("-05.50"), timestamps are unix ints.
* Bad credentials return 403, not 401.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional
from urllib.parse import urlsplit, urlunsplit

import httpx
from sqlalchemy.orm import Session

import config
from models import Account, SimpleFinConnection, Transaction
from services.balances import anchor_starting_balance
from services.categorization import build_categorizer
from services.transfers import detect_internal_transfers

# The hard cap is 90 days, but the server warns above 45 and says that may
# become a cap, so stay under the soft limit.
MAX_WINDOW_DAYS = 45
REQUEST_TIMEOUT = 60.0


class SimpleFinError(RuntimeError):
    """Raised for transport or protocol failures worth surfacing to the user."""


# --------------------------------------------------------------------------
# Access URL handling
# --------------------------------------------------------------------------

def claim_setup_token(setup_token: str) -> str:
    """Exchange a one-time setup token for a long-lived access URL.

    The token is base64 of a claim URL. The exchange is single-use: once
    claimed, the token is dead, so the caller must persist the result.
    """
    setup_token = setup_token.strip()
    try:
        claim_url = base64.b64decode(setup_token).decode("utf-8").strip()
    except Exception as exc:
        raise SimpleFinError(f"Setup token is not valid base64: {exc}") from exc

    if not claim_url.startswith("https://"):
        raise SimpleFinError(f"Decoded claim URL is not https: {claim_url[:60]!r}")

    try:
        response = httpx.post(
            claim_url,
            headers={"Content-Length": "0"},
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise SimpleFinError(f"Could not reach SimpleFIN to claim token: {exc}") from exc

    if response.status_code != 200:
        raise SimpleFinError(
            f"Claim failed with HTTP {response.status_code}. "
            "Setup tokens are single-use and expire -- generate a new one."
        )

    access_url = response.text.strip()
    if not access_url.startswith("https://"):
        raise SimpleFinError(f"Claim returned something that is not a URL: {access_url[:60]!r}")
    return access_url


def split_access_url(access_url: str) -> tuple[str, tuple[str, str]]:
    """Split `https://user:pass@host/path` into (base_url, (user, pass)).

    Credentials are carried in the URL userinfo. They are pulled out here so
    they can be passed as explicit basic auth and never end up in a logged URL.
    """
    parts = urlsplit(access_url.strip())
    if not parts.hostname:
        raise SimpleFinError("Access URL has no host")
    if parts.username is None or parts.password is None:
        raise SimpleFinError("Access URL is missing embedded credentials")

    netloc = parts.hostname + (f":{parts.port}" if parts.port else "")
    base_url = urlunsplit((parts.scheme, netloc, parts.path.rstrip("/"), "", ""))
    return base_url, (parts.username, parts.password)


def redact(access_url: str) -> str:
    """Access URL with credentials stripped, safe for logs and API responses."""
    try:
        base_url, _ = split_access_url(access_url)
        return base_url
    except SimpleFinError:
        return "<unparseable access url>"


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch_accounts(
    access_url: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    pending: bool = True,
    balances_only: bool = False,
) -> dict:
    """GET /accounts for a single window. Does not page -- see fetch_window()."""
    base_url, auth = split_access_url(access_url)

    params: dict[str, str | int] = {"version": 2}
    if start_date:
        params["start-date"] = int(datetime.combine(start_date, datetime.min.time(), timezone.utc).timestamp())
    if end_date:
        params["end-date"] = int(datetime.combine(end_date, datetime.min.time(), timezone.utc).timestamp())
    if pending:
        params["pending"] = 1
    if balances_only:
        params["balances-only"] = 1

    try:
        response = httpx.get(
            f"{base_url}/accounts",
            params=params,
            auth=auth,
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise SimpleFinError(f"SimpleFIN request failed: {exc}") from exc

    if response.status_code == 403:
        raise SimpleFinError(
            "SimpleFIN rejected the credentials (HTTP 403). The access URL may have "
            "been revoked -- re-claim a new setup token."
        )
    if response.status_code == 429:
        raise SimpleFinError(
            "SimpleFIN rate limit hit (HTTP 429). The Bridge expects <=24 requests/day."
        )
    if response.status_code != 200:
        raise SimpleFinError(f"SimpleFIN returned HTTP {response.status_code}: {response.text[:200]}")

    try:
        return response.json()
    except ValueError as exc:
        raise SimpleFinError(f"SimpleFIN returned non-JSON: {response.text[:200]}") from exc


def _windows(start_date: date, end_date: date) -> Iterable[tuple[date, date]]:
    """Split a range into <=90 day chunks, since longer ranges get capped."""
    cursor = start_date
    while cursor < end_date:
        window_end = min(cursor + timedelta(days=MAX_WINDOW_DAYS), end_date)
        yield cursor, window_end
        cursor = window_end


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

def parse_amount(raw: object) -> float:
    """SimpleFIN amounts are numeric strings, sometimes zero-padded."""
    try:
        return float(Decimal(str(raw).strip()))
    except (InvalidOperation, ValueError, ArithmeticError) as exc:
        raise SimpleFinError(f"Unparseable amount {raw!r}") from exc


def parse_timestamp(raw: object) -> date:
    """Unix timestamp -> date, pinned to UTC.

    Deliberately UTC rather than server-local: these timestamps are usually
    midnight UTC, so interpreting them in a negative-offset local timezone
    shifts every transaction back a day.
    """
    return datetime.fromtimestamp(int(raw), tz=timezone.utc).date()


def transaction_date(txn: dict) -> date:
    """`posted` is 0 while a transaction is pending; fall back to transacted_at."""
    posted = int(txn.get("posted") or 0)
    if posted > 0:
        return parse_timestamp(posted)
    transacted_at = txn.get("transacted_at")
    if transacted_at:
        return parse_timestamp(transacted_at)
    return datetime.now(timezone.utc).date()


def signed_amount(raw_amount: float, account_type: str) -> float:
    """SimpleFIN's transaction sign convention already matches this app's.

    Both use negative for money out, on every account type -- verified against
    existing credit card rows, which store purchases negative (a charge of
    -53.70, not +53.70). calculate_account_balance() then does
    `starting_balance - sum(amount)` for cards, which turns that negative
    activity into a positive amount owed.

    Note this is the opposite of the CSV importer's "Amex style / inverted"
    option, which flips positive-expense statements into the same negative
    convention on the way in. By the time a row is stored, everything is
    negative-is-money-out.
    """
    return raw_amount


# --------------------------------------------------------------------------
# Sync
# --------------------------------------------------------------------------

@dataclass
class SyncResult:
    imported: int = 0
    updated: int = 0
    unchanged: int = 0
    adopted: int = 0          # pre-existing CSV rows back-filled with an external_id
    skipped_unlinked: int = 0
    transfers_detected: int = 0
    accounts_synced: list[str] = field(default_factory=list)
    balances: list[dict] = field(default_factory=list)
    unlinked_accounts: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "imported": self.imported,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "adopted": self.adopted,
            "skipped_unlinked": self.skipped_unlinked,
            "transfers_detected": self.transfers_detected,
            "accounts_synced": self.accounts_synced,
            "balances": self.balances,
            "unlinked_accounts": self.unlinked_accounts,
            "warnings": self.warnings,
            "message": (
                f"Synced {len(self.accounts_synced)} account(s): "
                f"{self.imported} new, {self.updated} updated, {self.adopted} matched to "
                f"existing rows, {self.unchanged} unchanged."
            ),
        }


def get_connection(db: Session) -> Optional[SimpleFinConnection]:
    return db.query(SimpleFinConnection).order_by(SimpleFinConnection.id.desc()).first()


def resolve_access_url(db: Session) -> Optional[str]:
    """Access URL from the environment, falling back to the database.

    .env wins because it survives a database reset -- and since setup tokens
    are single-use, losing the access URL costs a new token.
    """
    from_env = config.get_access_url()
    if from_env:
        return from_env
    connection = get_connection(db)
    return connection.access_url if connection else None


def store_access_url(db: Session, access_url: str, org_name: str = "") -> None:
    """Persist a claimed access URL to .env first, then the database."""
    config.save_access_url(access_url)
    db.query(SimpleFinConnection).delete()
    db.add(SimpleFinConnection(access_url=access_url, org_name=org_name))
    db.commit()


def sync(
    db: Session,
    access_url: str,
    days: int = 30,
    pending: bool = True,
    anchor_balances: bool = True,
) -> SyncResult:
    """Pull `days` of history and upsert into the transactions table.

    With `anchor_balances`, each linked account's starting_balance is rewritten
    so its computed balance matches the balance SimpleFIN reports. Without it,
    balances reflect only the synced window and are meaningless.
    """
    result = SyncResult()
    end_date = datetime.now(timezone.utc).date() + timedelta(days=1)
    start_date = end_date - timedelta(days=days)

    linked = {
        account.simplefin_account_id: account
        for account in db.query(Account).filter(Account.simplefin_account_id.isnot(None)).all()
    }

    categorize = build_categorizer(db)
    seen_remote: dict[str, dict] = {}

    for window_start, window_end in _windows(start_date, end_date):
        payload = fetch_accounts(access_url, window_start, window_end, pending=pending)

        for err in payload.get("errlist") or []:
            message = err.get("msg") if isinstance(err, dict) else str(err)
            if message and message not in result.warnings:
                result.warnings.append(message)
        for message in payload.get("x-api-message") or []:
            if message not in result.warnings:
                result.warnings.append(message)

        for remote in payload.get("accounts", []):
            remote_id = remote.get("id")
            if not remote_id:
                continue
            # Overwrite rather than setdefault: each window echoes a
            # balance-date pinned to that window, so the last (most recent)
            # window is the one to anchor balances against.
            seen_remote[remote_id] = remote

            account = linked.get(remote_id)
            if account is None:
                continue

            _sync_account(db, account, remote, categorize, result)

    for remote_id, remote in seen_remote.items():
        account = linked.get(remote_id)
        if account is None:
            result.skipped_unlinked += len(remote.get("transactions") or [])
            result.unlinked_accounts.append({
                "simplefin_account_id": remote_id,
                "name": remote.get("name"),
                "balance": remote.get("balance"),
                "currency": remote.get("currency"),
            })
            continue

        if remote.get("currency") not in (None, "USD"):
            result.warnings.append(
                f"{account.name}: account is denominated in {remote['currency']}; "
                "this app assumes a single currency and does not convert."
            )

        if not anchor_balances:
            continue

        # Flush pending inserts so the anchor sums include this run's rows.
        db.flush()
        try:
            reported = parse_amount(remote.get("balance"))
        except SimpleFinError as exc:
            result.warnings.append(f"{account.name}: could not read reported balance ({exc})")
            continue

        # Balances, unlike transactions, DO need flipping: SimpleFIN reports
        # card debt as a negative balance (-8587.84 owed), while this app
        # treats a card balance as a positive amount owed so that
        # get_total_balance() can add it straight into total_liabilities.
        if account.account_type == "credit_card":
            reported = -reported

        starting = anchor_starting_balance(account, db, reported)
        result.balances.append({
            "account": account.name,
            "reported_balance": reported,
            "starting_balance_set_to": starting,
            "as_of": str(parse_timestamp(remote["balance-date"])) if remote.get("balance-date") else None,
        })

    db.flush()
    # Both legs of a card payment are usually pulled in the same sync, so
    # match them now rather than leaving the funding side looking like a
    # several-thousand-dollar expense.
    result.transfers_detected = len(detect_internal_transfers(db, commit=False))

    db.commit()
    return result


def _sync_account(db: Session, account: Account, remote: dict, categorize, result: SyncResult) -> None:
    if account.name not in result.accounts_synced:
        result.accounts_synced.append(account.name)

    for txn in remote.get("transactions") or []:
        external_id = str(txn.get("id") or "").strip()
        if not external_id:
            result.warnings.append(f"{account.name}: transaction without an id was skipped")
            continue

        try:
            raw_amount = parse_amount(txn.get("amount"))
            txn_date = transaction_date(txn)
        except SimpleFinError as exc:
            result.warnings.append(f"{account.name}: {exc}")
            continue

        amount = signed_amount(raw_amount, account.account_type)
        payee = (txn.get("payee") or "").strip()
        raw_description = (txn.get("description") or "").strip()
        memo = (txn.get("memo") or "").strip()

        # Store the raw bank description, not the cleaned `payee`.
        #
        # SimpleFIN sends both: description is the raw statement text
        # ("WOODLAKE COMMUNITY AMidlothian VA") and payee is a tidied name
        # ("Woodlake Community"). The tidied one reads better, but every
        # existing transaction and every learned categorization rule in this
        # database was built from raw CSV statement text. Measured against a
        # live feed, learned rules matched 1/151 transactions on payee versus
        # 21/151 on the raw description. Storing raw keeps those rules working
        # and keeps new rules consistent with the old ones.
        description = raw_description or payee or memo or "(no description)"
        is_pending = bool(txn.get("pending")) or int(txn.get("posted") or 0) == 0

        existing = db.query(Transaction).filter(
            Transaction.account_id == account.id,
            Transaction.external_id == external_id,
        ).first()

        if existing is None:
            # A row may already exist from a CSV import of the same statement.
            # Adopt it instead of creating a duplicate. Match on description
            # first: two different merchants can share a date and amount, and
            # date+amount alone would stamp the id onto the wrong row.
            candidates = db.query(Transaction).filter(
                Transaction.account_id == account.id,
                Transaction.external_id.is_(None),
                Transaction.date == txn_date,
                Transaction.amount == amount,
            ).all()
            existing = next(
                (c for c in candidates if c.description.strip().lower() == description.lower()),
                candidates[0] if len(candidates) == 1 else None,
            )
            if existing is not None:
                # Claim the row, then fall through to the update path so its
                # fields settle to SimpleFIN's values in this same pass rather
                # than churning on the next sync.
                existing.external_id = external_id
                result.adopted += 1
                existing.date = txn_date
                existing.amount = amount
                existing.description = description
                existing.pending = is_pending
                continue

        if existing is not None:
            changed = False
            # A pending transaction's amount and description both change when it
            # posts, so re-write them rather than trusting the first version.
            for attr, value in (
                ("date", txn_date),
                ("amount", amount),
                ("description", description),
                ("pending", is_pending),
            ):
                if getattr(existing, attr) != value:
                    setattr(existing, attr, value)
                    changed = True
            if changed:
                result.updated += 1
            else:
                result.unchanged += 1
            continue

        db.add(Transaction(
            date=txn_date,
            description=description,
            amount=amount,
            # Match against every name the bank gave us: learned rules were
            # trained on raw statement text, but keywords tend to match the
            # tidied payee.
            category_id=categorize(raw_description, payee, memo, mcc=txn.get("mcc")),
            account_id=account.id,
            source=account.account_type,
            sign_convention="standard",
            # Keep the tidied payee (and memo, when an institution sends one)
            # rather than discarding them.
            notes=" | ".join(p for p in (payee, memo) if p and p != description),
            external_id=external_id,
            pending=is_pending,
        ))
        result.imported += 1

    account.last_synced_at = datetime.utcnow()
