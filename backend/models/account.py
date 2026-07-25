from sqlalchemy import Column, Integer, String, Float, DateTime, Date
from datetime import datetime, date
from database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    account_type = Column(String, nullable=False)  # checking, savings, credit_card, investment, cash
    starting_balance = Column(Float, default=0.0)
    starting_date = Column(Date, nullable=True)  # Date of starting balance
    icon = Column(String, default="🏦")
    color = Column(String, default="#3B82F6")
    simplefin_account_id = Column(String, nullable=True, unique=True)  # links to a remote SimpleFIN account
    last_synced_at = Column(DateTime, nullable=True)
    # How this account is grouped on the dashboard:
    #   everyday    -- spending accounts, counted in net worth
    #   short_term  -- liquid savings (emergency fund); counted, shown apart
    #   long_term   -- retirement and similar; tracked but NOT counted, since
    #                  it swamps a figure meant to reflect day-to-day finances
    net_worth_group = Column(String, default="everyday")
    created_at = Column(DateTime, default=datetime.utcnow)
