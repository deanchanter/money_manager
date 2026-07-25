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
from services.classification import build_classifier

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/all-time-balance")
def get_all_time_balance(
    starting_balance: float = 0.0,
    db: Session = Depends(get_db)
):
    """Get all-time net balance across all transactions"""
    classifier = build_classifier(db)

    total_income = 0.0
    total_expenses = 0.0

    for t in db.query(Transaction).all():
        total_expenses += classifier.expense_amount(t)
        total_income += classifier.income_amount(t)

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
    
    classifier = build_classifier(db)

    all_transactions = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()

    total_income = 0.0
    total_expenses = 0.0
    category_totals = {}  # category_id -> total expenses

    for t in all_transactions:
        expense = classifier.expense_amount(t)
        if expense:
            total_expenses += expense
            if t.category_id:
                category_totals[t.category_id] = category_totals.get(t.category_id, 0) + expense
        total_income += classifier.income_amount(t)

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
            month_expenses += classifier.expense_amount(t)
            month_income += classifier.income_amount(t)

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
        Transaction.amount < 0,
        Transaction.is_transfer.is_(False),
        Category.is_transfer.is_(False)
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
