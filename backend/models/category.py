from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    icon = Column(String, default="📁")
    color = Column(String, default="#6B7280")
    is_income = Column(Boolean, default=False)
    # Money moving between accounts the user owns -- excluded from income and
    # expense totals so a credit card payment does not read as spending.
    is_transfer = Column(Boolean, default=False)
    keywords = Column(String, default="")  # Comma-separated keywords for auto-categorization

    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")
