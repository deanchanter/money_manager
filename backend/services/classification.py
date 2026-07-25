"""Decide whether a transaction counts as income, expense, or neither.

This lived inline in analytics.py, copy-pasted across the dashboard totals,
the monthly trend, and the all-time balance -- three copies that had to agree
and could silently drift. One implementation now serves all three.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Category, Transaction

# Fallback only. Structural detection (services/transfers.py) and the
# is_transfer category flag are the primary signals; these catch older rows
# that predate both. Kept deliberately specific -- a bare "payment" would
# swallow real spending.
TRANSFER_KEYWORDS = (
    "transfer", "zelle", "venmo", "paypal",
    "payment to", "payment from", "credit card payment", "card payment",
    "payment thank", "autopay",
    # Real statement wording seen in practice for card payments:
    "epayment", "credit crd", "ach pmt", "online payment",
)

INCOME_KEYWORDS = (
    "salary", "paycheck", "direct deposit", "payroll", "dividend",
    "interest earned", "deposit from", "ach deposit", "tax refund",
)


@dataclass
class Classifier:
    """Precomputed lookups so per-transaction classification stays cheap."""
    transfer_category_ids: set[int]
    income_category_ids: set[int]

    def is_transfer(self, txn: Transaction) -> bool:
        if txn.is_transfer:
            return True
        if txn.category_id in self.transfer_category_ids:
            return True
        description = (txn.description or "").lower()
        return any(keyword in description for keyword in TRANSFER_KEYWORDS)

    def expense_amount(self, txn: Transaction) -> float:
        """Positive expense amount, or 0.0 if this is not an expense."""
        if self.is_transfer(txn):
            return 0.0
        if txn.source == "credit_card":
            # Inverted (Amex-style CSV) stores charges positive; standard
            # stores them negative. Either way the other sign is a payment.
            if txn.sign_convention == "inverted":
                return txn.amount if txn.amount > 0 else 0.0
            return abs(txn.amount) if txn.amount < 0 else 0.0
        return abs(txn.amount) if txn.amount < 0 else 0.0

    def income_amount(self, txn: Transaction) -> float:
        """Positive income amount, or 0.0 if this is not income."""
        if self.is_transfer(txn):
            return 0.0
        if txn.source == "credit_card":
            return 0.0  # a credit on a card is a refund or payment, not income
        return txn.amount if txn.amount > 0 else 0.0


def build_classifier(db: Session) -> Classifier:
    categories = db.query(Category).all()
    return Classifier(
        transfer_category_ids={
            c.id for c in categories
            if c.is_transfer or c.name in ("Transfer", "Credit Card Payment")
        },
        income_category_ids={c.id for c in categories if c.is_income},
    )
