from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)  # Negative for expenses, positive for income
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    source = Column(String, default="bank")  # bank, credit_card, cash, investment (legacy, use account_id)
    sign_convention = Column(String, default="standard")  # standard, inverted
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="transactions")
    account = relationship("Account", backref="transactions")
