from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime
from database import Base

class AutoCategoryRule(Base):
    __tablename__ = "auto_category_rules"

    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String, nullable=False)  # The description pattern to match
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    match_type = Column(String, default="contains")  # contains, exact, starts_with
    priority = Column(Integer, default=0)  # Higher priority rules are checked first
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
