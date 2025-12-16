from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from datetime import datetime
from database import Base

class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    target_date = Column(Date, nullable=True)
    icon = Column(String, default="🎯")
    color = Column(String, default="#10B981")
    created_at = Column(DateTime, default=datetime.utcnow)
