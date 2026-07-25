"""Detect money moving between accounts the user owns.

A credit card payment is not spending, but it looks like a large expense on
the account it left. Descriptions are an unreliable way to spot these -- real
ones read "AMEX EPAYMENT", "Withdrawal from CHASE CREDIT CRD EPAY",
"ONLINE PAYMENT - THANK YOU" -- and no keyword list survives a bank changing
its wording.

The structural signal is reliable instead: a payment always has two legs, one
on each account, equal and opposite, a day or two apart.

    CapOne   2026-07-16   -9975.97   AMEX EPAYMENT
    Amex     2026-07-15   +9975.97   ONLINE PAYMENT - THANK YOU
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from models import Account, Transaction

# Legs rarely post the same day; a card payment usually clears the card first.
MAX_LEG_GAP_DAYS = 5

# Below this, coincidental equal-and-opposite amounts across two accounts are
# more likely than a real transfer.
MIN_TRANSFER_AMOUNT = 1.00

# A positive amount on a card is either a payment or a refund, and matching
# refunds to unrelated outflows produced real false positives: a $10 "Withdrawal
# from VENMO PAYMENT" got paired with a "$120 Disney Streaming Credit" of the
# same amount. Requiring the card leg to be described as a payment removes them.
#
# These are matched only against issuer-generated text on the card side, where
# "payment" is unambiguous -- unlike the funding side, where a merchant called
# "... Payment ..." would be a real expense.
CARD_PAYMENT_HINTS = ("payment", "autopay", "thank you", "thank", "pymt")

# Tokens shorter than this match too much ("ira", "sec", "the").
MIN_NAME_TOKEN = 4

# Words that appear in account names but say nothing about which account.
GENERIC_NAME_TOKENS = frozenset({
    "account", "accounts", "bank", "card", "cash", "checking", "credit",
    "reserve", "retirement", "savings", "portfolio", "traditional", "roth",
    "plan", "tax", "coordinated", "investment", "brokerage", "joint",
})


def looks_like_card_payment(description: str) -> bool:
    text = (description or "").lower()
    return any(hint in text for hint in CARD_PAYMENT_HINTS)


def words(text: str) -> set[str]:
    """Lowercased alphanumeric words.

    Whole words, not substrings: an account named "Chase" must not match the
    word "PURCHASE", which appears in ordinary card descriptions.
    """
    return set("".join(ch if ch.isalnum() else " " for ch in (text or "")).lower().split())


def name_tokens(account: Account) -> set[str]:
    """Distinctive words identifying an account, for matching descriptions.

    A transfer between two asset accounts carries no "payment" wording, but the
    moving side almost always names the other account -- "BETTERMENT SEC",
    "Withdrawal from BETTERMENT SEC TRANSFER", "Transfer from CapOne".
    """
    return {
        token for token in words(account.name)
        if len(token) >= MIN_NAME_TOKEN
        and not token.isdigit()
        and token not in GENERIC_NAME_TOKENS
    }


def names_the_other_account(description: str, other: Account) -> bool:
    return bool(words(description) & name_tokens(other))


def detect_internal_transfers(db: Session, commit: bool = True) -> list[dict]:
    """Flag both legs of money moved between the user's own accounts.

    Pairs an inflow on one account against an equal outflow on another within
    a few days. An equal-and-opposite coincidence is possible, so a pair is
    only accepted with corroborating evidence:

      * the inflow is on a credit card and reads like a payment
        ("ONLINE PAYMENT - THANK YOU"), or
      * one leg names the other account ("BETTERMENT SEC").

    Without that check, a $10 "Withdrawal from VENMO PAYMENT" was matched to a
    coincidental "$120 Disney Streaming Credit" of the same amount.
    """
    accounts = {a.id: a for a in db.query(Account).all()}
    if len(accounts) < 2:
        return []

    candidates = db.query(Transaction).filter(
        Transaction.account_id.isnot(None),
        Transaction.is_transfer.is_(False),
    ).all()

    inflows = [t for t in candidates if t.amount >= MIN_TRANSFER_AMOUNT]
    outflows = [t for t in candidates if t.amount <= -MIN_TRANSFER_AMOUNT]

    # Bucket the outflow side by amount so matching is not O(n*m).
    by_amount: dict[int, list[Transaction]] = {}
    for outflow in outflows:
        by_amount.setdefault(cents(-outflow.amount), []).append(outflow)

    matched: list[dict] = []
    used: set[int] = set()

    for inflow in sorted(inflows, key=lambda t: t.date):
        into = accounts.get(inflow.account_id)
        if into is None:
            continue

        best = None
        for outflow in by_amount.get(cents(inflow.amount), []):
            if outflow.id in used or outflow.account_id == inflow.account_id:
                continue
            gap = abs((outflow.date - inflow.date).days)
            if gap > MAX_LEG_GAP_DAYS:
                continue

            out_of = accounts.get(outflow.account_id)
            if out_of is None:
                continue
            corroborated = (
                (into.account_type == "credit_card" and looks_like_card_payment(inflow.description))
                or names_the_other_account(outflow.description, into)
                or names_the_other_account(inflow.description, out_of)
            )
            if not corroborated:
                continue

            # Closest in time wins when an account receives two equal amounts.
            if best is None or gap < abs((best.date - inflow.date).days):
                best = outflow

        if best is None:
            continue

        used.add(best.id)
        inflow.is_transfer = True
        best.is_transfer = True
        matched.append({
            "amount": round(inflow.amount, 2),
            "into": into.name,
            "into_date": str(inflow.date),
            "funded_from": accounts[best.account_id].name,
            "funding_date": str(best.date),
            "description": best.description[:60],
            "matched_by": "paired legs",
        })

    matched.extend(_flag_unpaired_named_transfers(db, accounts))

    if commit:
        db.commit()
    return matched


def _flag_unpaired_named_transfers(db: Session, accounts: dict[int, Account]) -> list[dict]:
    """Flag transfers whose other leg never arrives.

    Not every institution reports the receiving transaction. Betterment, for
    instance, reports balances but almost no transaction history, so a $14,000
    "BETTERMENT SEC" leaving checking has nothing to pair with and would
    otherwise read as the largest expense of the month.

    A transaction that names another account the user owns is money moving
    between their own accounts either way. Caveat: this keys off account names,
    so naming an account after a place you also shop there ("Target") would
    misfire.
    """
    matched: list[dict] = []
    # The session runs with autoflush off, so without this the query would not
    # see rows the pairing pass just flagged and would report them twice.
    db.flush()
    remaining = db.query(Transaction).filter(
        Transaction.account_id.isnot(None),
        Transaction.is_transfer.is_(False),
    ).all()

    for txn in remaining:
        if txn.is_transfer or abs(txn.amount) < MIN_TRANSFER_AMOUNT:
            continue
        description_words = words(txn.description)
        for other in accounts.values():
            if other.id == txn.account_id:
                continue
            if description_words & name_tokens(other):
                txn.is_transfer = True
                matched.append({
                    "amount": round(txn.amount, 2),
                    "into": other.name if txn.amount < 0 else accounts[txn.account_id].name,
                    "into_date": str(txn.date),
                    "funded_from": accounts[txn.account_id].name if txn.amount < 0 else other.name,
                    "funding_date": str(txn.date),
                    "description": txn.description[:60],
                    "matched_by": f"names '{other.name}' (no opposite leg reported)",
                })
                break
    return matched


# Previous name, kept so existing callers and any saved scripts keep working.
detect_card_payments = detect_internal_transfers


def cents(amount: float) -> int:
    """Bucket key -- avoids float equality between the two legs."""
    return int(round(amount * 100))
