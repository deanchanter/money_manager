from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from database import get_db
from models import Transaction, Category, Budget
from schemas import DashboardStats, SpendingByCategory, MonthlySpending, BudgetResponse
from routers.budgets import calculate_budget_stats

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/all-time-balance")
def get_all_time_balance(
    starting_balance: float = 0.0,
    db: Session = Depends(get_db)
):
    """Get all-time net balance across all transactions"""
    # Keywords that indicate transfers
    transfer_keywords = ['transfer', 'zelle', 'venmo', 'paypal', 'payment to', 'payment from', 
                        'credit card payment', 'card payment', 'payment thank', 'autopay']
    income_keywords = ['salary', 'paycheck', 'direct deposit', 'payroll', 'dividend', 
                      'interest earned', 'deposit from', 'ach deposit', 'tax refund']
    
    # Get transfer category IDs
    transfer_categories = db.query(Category.id).filter(
        Category.name.in_(["Transfer", "Credit Card Payment"])
    ).all()
    transfer_category_ids = [c.id for c in transfer_categories]
    
    all_transactions = db.query(Transaction).all()
    
    total_income = 0.0
    total_expenses = 0.0
    
    for t in all_transactions:
        desc_lower = t.description.lower()
        is_transfer = any(kw in desc_lower for kw in transfer_keywords)
        is_transfer_category = t.category_id in transfer_category_ids
        is_income_keyword = any(kw in desc_lower for kw in income_keywords)
        is_income_category = t.category and t.category.is_income
        is_credit_card = t.source == "credit_card"
        is_inverted = t.sign_convention == "inverted"
        
        if is_transfer or is_transfer_category:
            continue
        
        if is_credit_card:
            if is_inverted:
                if t.amount > 0:
                    total_expenses += t.amount
            else:
                if t.amount < 0:
                    total_expenses += abs(t.amount)
            continue
        
        if t.amount < 0:
            total_expenses += abs(t.amount)
        elif is_income_keyword or is_income_category:
            total_income += t.amount
        else:
            total_income += t.amount
    
    net_balance = starting_balance + total_income - total_expenses
    
    return {
        "starting_balance": round(starting_balance, 2),
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_balance": round(net_balance, 2)
    }

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    # Default to current month if no dates provided
    if not start_date:
        today = datetime.now()
        start_date = date(today.year, today.month, 1)
    if not end_date:
        end_date = date.today()
    
    # Keywords that indicate transfers (should be excluded from both income and expenses)
    transfer_keywords = ['transfer', 'zelle', 'venmo', 'paypal', 'payment to', 'payment from', 
                        'credit card payment', 'card payment', 'payment thank', 'autopay']
    # Keywords that indicate real income
    income_keywords = ['salary', 'paycheck', 'direct deposit', 'payroll', 'dividend', 
                      'interest earned', 'deposit from', 'ach deposit', 'tax refund']
    
    # Get all transactions in date range
    all_transactions = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    total_income = 0.0
    total_expenses = 0.0
    category_totals = {}  # category_id -> total expenses
    
    # Get transfer category IDs
    transfer_categories = db.query(Category.id).filter(
        Category.name.in_(["Transfer", "Credit Card Payment"])
    ).all()
    transfer_category_ids = [c.id for c in transfer_categories]
    
    for t in all_transactions:
        desc_lower = t.description.lower()
        is_transfer = any(kw in desc_lower for kw in transfer_keywords)
        is_transfer_category = t.category_id in transfer_category_ids
        is_income_keyword = any(kw in desc_lower for kw in income_keywords)
        is_income_category = t.category and t.category.is_income
        is_credit_card = t.source == "credit_card"
        is_inverted = t.sign_convention == "inverted"
        
        # Skip transfers entirely (credit card payments, zelle, etc)
        if is_transfer or is_transfer_category:
            continue
        
        # Determine if this transaction is an expense
        # Credit card with inverted (Amex style): positive = expense
        # Credit card with standard (Chase style): negative = expense
        # Bank: negative = expense
        if is_credit_card:
            if is_inverted:
                # Amex style: positive = expense, negative = payment (skip)
                if t.amount > 0:
                    total_expenses += t.amount
                    if t.category_id:
                        category_totals[t.category_id] = category_totals.get(t.category_id, 0) + t.amount
            else:
                # Chase style: negative = expense, positive = payment (skip)
                if t.amount < 0:
                    total_expenses += abs(t.amount)
                    if t.category_id:
                        category_totals[t.category_id] = category_totals.get(t.category_id, 0) + abs(t.amount)
            continue
        
        # Bank/other: negative = expense, positive = income
        if t.amount < 0:
            total_expenses += abs(t.amount)
            if t.category_id:
                category_totals[t.category_id] = category_totals.get(t.category_id, 0) + abs(t.amount)
        elif is_income_keyword or is_income_category:
            total_income += t.amount
        else:
            total_income += t.amount
    
    # Spending by category
    spending_by_category = []
    for category_id, total in category_totals.items():
        category = db.query(Category).filter(Category.id == category_id).first()
        if category and not category.is_income:
            percentage = (total / total_expenses * 100) if total_expenses > 0 else 0
            spending_by_category.append(SpendingByCategory(
                category_id=category.id,
                category_name=category.name,
                category_color=category.color,
                total=round(total, 2),
                percentage=round(percentage, 2)
            ))
    
    # Monthly trend (last 6 months)
    monthly_trend = []
    for i in range(5, -1, -1):
        month_date = datetime.now() - relativedelta(months=i)
        month_start = date(month_date.year, month_date.month, 1)
        month_end = month_start + relativedelta(months=1, days=-1)
        
        month_transactions = db.query(Transaction).filter(
            Transaction.date >= month_start,
            Transaction.date <= month_end
        ).all()
        
        month_income = 0.0
        month_expenses = 0.0
        
        for t in month_transactions:
            desc_lower = t.description.lower()
            is_transfer = any(kw in desc_lower for kw in transfer_keywords)
            is_transfer_category = t.category_id in transfer_category_ids
            is_income_keyword = any(kw in desc_lower for kw in income_keywords)
            is_income_category = t.category and t.category.is_income
            is_credit_card = t.source == "credit_card"
            is_inverted = t.sign_convention == "inverted"
            
            if is_transfer or is_transfer_category:
                continue
            if is_credit_card:
                if is_inverted:
                    if t.amount > 0:
                        month_expenses += t.amount
                else:
                    if t.amount < 0:
                        month_expenses += abs(t.amount)
                continue
            if t.amount < 0:
                month_expenses += abs(t.amount)
            elif is_income_keyword or is_income_category:
                month_income += t.amount
            else:
                month_income += t.amount
        
        monthly_trend.append(MonthlySpending(
            month=month_start.strftime("%Y-%m"),
            income=round(month_income, 2),
            expenses=round(month_expenses, 2),
            net=round(month_income - month_expenses, 2)
        ))
    
    # Budget alerts (current month)
    current_month = datetime.now().strftime("%Y-%m")
    budgets = db.query(Budget).filter(Budget.month == current_month).all()
    
    budget_alerts = []
    for budget in budgets:
        stats = calculate_budget_stats(budget, db)
        if stats["is_alert"]:
            budget_alerts.append(BudgetResponse(
                id=budget.id,
                category_id=budget.category_id,
                amount=budget.amount,
                month=budget.month,
                alert_threshold=budget.alert_threshold,
                category=budget.category,
                **stats
            ))
    
    return DashboardStats(
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        net_balance=round(total_income - total_expenses, 2),
        spending_by_category=spending_by_category,
        monthly_trend=monthly_trend,
        budget_alerts=budget_alerts
    )

@router.get("/spending-by-category")
def get_spending_by_category(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    if not start_date:
        today = datetime.now()
        start_date = date(today.year, today.month, 1)
    if not end_date:
        end_date = date.today()
    
    results = db.query(
        Category.id,
        Category.name,
        Category.color,
        Category.icon,
        func.sum(func.abs(Transaction.amount)).label('total'),
        func.count(Transaction.id).label('count')
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.amount < 0
    ).group_by(Category.id).order_by(func.sum(func.abs(Transaction.amount)).desc()).all()
    
    total = sum(r.total for r in results)
    
    return [{
        "category_id": r.id,
        "category_name": r.name,
        "category_color": r.color,
        "category_icon": r.icon,
        "total": round(r.total, 2),
        "count": r.count,
        "percentage": round(r.total / total * 100, 2) if total > 0 else 0
    } for r in results]
