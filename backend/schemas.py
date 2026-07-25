from pydantic import BaseModel
from datetime import date
from typing import Optional, List, Union

# Account schemas
class AccountBase(BaseModel):
    name: str
    account_type: str  # checking, savings, credit_card, investment, cash
    starting_balance: float = 0.0
    starting_date: Optional[date] = None
    icon: str = "🏦"
    color: str = "#3B82F6"
    net_worth_group: str = "everyday"  # everyday | short_term | long_term

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    account_type: Optional[str] = None
    starting_balance: Optional[float] = None
    starting_date: Optional[date] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    net_worth_group: Optional[str] = None

class AccountResponse(AccountBase):
    id: int
    current_balance: float = 0.0

    class Config:
        from_attributes = True

# Category schemas
class CategoryBase(BaseModel):
    name: str
    icon: str = "📁"
    color: str = "#6B7280"
    is_income: bool = False
    is_transfer: bool = False  # excluded from income and expense totals
    keywords: str = ""

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True

# Transaction schemas
class TransactionBase(BaseModel):
    date: date
    description: str
    amount: float
    category_id: Optional[int] = None
    source: str = "bank"  # bank, credit_card, cash, investment
    sign_convention: str = "standard"  # standard, inverted
    notes: str = ""

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    date: Union[date, None] = None
    description: Union[str, None] = None
    amount: Union[float, None] = None
    category_id: Union[int, None] = None
    source: Union[str, None] = None
    sign_convention: Union[str, None] = None
    notes: Union[str, None] = None

class AccountBrief(BaseModel):
    id: int
    name: str
    icon: str

    class Config:
        from_attributes = True

class TransactionResponse(TransactionBase):
    id: int
    account_id: Optional[int] = None
    category: Optional[CategoryResponse] = None
    account: Optional[AccountBrief] = None

    class Config:
        from_attributes = True

# Budget schemas
class BudgetBase(BaseModel):
    category_id: int
    amount: float
    month: str
    alert_threshold: float = 0.8
    is_recurring: bool = False
    auto_adjust: bool = False

class BudgetCreate(BudgetBase):
    pass

class BudgetResponse(BudgetBase):
    id: int
    category: Optional[CategoryResponse] = None
    spent: float = 0.0
    remaining: float = 0.0
    percentage: float = 0.0
    is_over_budget: bool = False
    is_alert: bool = False
    is_income: bool = False

    class Config:
        from_attributes = True

# Savings Goal schemas
class SavingsGoalBase(BaseModel):
    name: str
    target_amount: float
    current_amount: float = 0.0
    target_date: Optional[date] = None
    icon: str = "🎯"
    color: str = "#10B981"
    category_id: Optional[int] = None

class SavingsGoalCreate(SavingsGoalBase):
    pass

class SavingsGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    target_date: Optional[date] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    category_id: Optional[int] = None

class SavingsGoalResponse(SavingsGoalBase):
    id: int
    percentage: float = 0.0
    remaining: float = 0.0
    category: Optional[CategoryResponse] = None

    class Config:
        from_attributes = True

# Analytics schemas
class SpendingByCategory(BaseModel):
    category_id: int
    category_name: str
    category_color: str
    total: float
    percentage: float

class MonthlySpending(BaseModel):
    month: str
    income: float
    expenses: float
    net: float

class DashboardStats(BaseModel):
    total_income: float
    total_expenses: float
    net_balance: float
    spending_by_category: List[SpendingByCategory]
    monthly_trend: List[MonthlySpending]
    budget_alerts: List[BudgetResponse]
