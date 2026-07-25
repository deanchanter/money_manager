"""Account balance math.

Lives here rather than in the accounts router so the SimpleFIN sync can anchor
balances using the exact same formula the API reports. Two copies of this
would drift.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Account, Transaction


def transaction_total(account: Account, db: Session) -> float:
    """Sum of transactions counted toward this account's balance."""
    query = db.query(func.sum(Transaction.amount)).filter(
        Transaction.account_id == account.id
    )
    if account.starting_date:
        query = query.filter(Transaction.date >= account.starting_date)
    return query.scalar() or 0.0


def calculate_account_balance(account: Account, db: Session) -> float:
    """Current balance = starting balance +/- transaction activity.

    Credit cards store charges as positive numbers and the balance represents
    debt owed, so activity is subtracted rather than added.
    """
    total_change = transaction_total(account, db)
    if account.account_type == "credit_card":
        return account.starting_balance - total_change
    return account.starting_balance + total_change


def anchor_starting_balance(account: Account, db: Session, reported_balance: float) -> float:
    """Back-solve starting_balance so calculate_account_balance() == reported.

    Sync only ever holds a recent slice of history, so a synced account's
    computed balance is meaningless without this. SimpleFIN's reported balance
    is authoritative, so the starting balance becomes the plug figure.

    Returns the starting balance that was set.
    """
    total_change = transaction_total(account, db)
    if account.account_type == "credit_card":
        account.starting_balance = round(reported_balance + total_change, 2)
    else:
        account.starting_balance = round(reported_balance - total_change, 2)
    return account.starting_balance
