from sqlalchemy import Boolean, Column, Integer, String, Float, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    # SimpleFIN transaction ids are unique per account, NOT globally, so the
    # idempotency key has to include account_id.
    __table_args__ = (
        UniqueConstraint("account_id", "external_id", name="uq_transaction_account_external_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  # Negative for expenses, positive for income
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    source = Column(String, default="bank")  # bank, credit_card, cash, investment (legacy, use account_id)
    sign_convention = Column(String, default="standard")  # standard, inverted
    notes = Column(String, default="")
    external_id = Column(String, nullable=True, index=True)  # SimpleFIN transaction id
    pending = Column(Boolean, default=False)  # unsettled; amount/description may still change
    # Set when this row was matched to an opposite leg on another of the
    # user's accounts (e.g. a credit card payment). Excluded from totals.
    is_transfer = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="transactions")
    account = relationship("Account", backref="transactions")
