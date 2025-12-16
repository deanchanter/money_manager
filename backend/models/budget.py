from sqlalchemy import Column, Integer, Float, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    amount = Column(Float, nullable=False)  # Monthly budget amount
    month = Column(String, nullable=False)  # Format: "YYYY-MM"
    alert_threshold = Column(Float, default=0.8)  # Alert when 80% spent
    is_recurring = Column(Boolean, default=False)  # Auto-rollover to next month
    auto_adjust = Column(Boolean, default=False)  # Auto-adjust based on trends

    category = relationship("Category", back_populates="budgets")
