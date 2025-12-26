from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta
from database import get_db
from models import Budget, Transaction, Category
from schemas import BudgetCreate, BudgetResponse

router = APIRouter(prefix="/api/budgets", tags=["budgets"])

def calculate_budget_stats(budget: Budget, db: Session) -> dict:
    """Calculate spent amount and other stats for a budget"""
    year, month = map(int, budget.month.split("-"))
    
    # Get all transactions for this category/month
    # Note: We don't exclude by description keywords since categorized PayPal/Venmo 
    # transactions are real expenses. Only Transfer/Credit Card Payment categories are excluded.
    transactions = db.query(Transaction).filter(
        Transaction.category_id == budget.category_id,
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).all()
    
    spent = 0.0
    for t in transactions:
        is_credit_card = t.source == 'credit_card'
        is_inverted = t.sign_convention == 'inverted'
        
        if is_credit_card:
            if is_inverted and t.amount > 0:
                spent += t.amount
            elif not is_inverted and t.amount < 0:
                spent += abs(t.amount)
        elif t.amount < 0:
            spent += abs(t.amount)
    
    remaining = budget.amount - spent
    percentage = (spent / budget.amount * 100) if budget.amount > 0 else 0
    
    return {
        "spent": round(spent, 2),
        "remaining": round(remaining, 2),
        "percentage": round(percentage, 2),
        "is_over_budget": spent > budget.amount,
        "is_alert": percentage >= (budget.alert_threshold * 100)
    }

@router.get("/", response_model=List[BudgetResponse])
def get_budgets(month: str = None, db: Session = Depends(get_db)):
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    budgets = db.query(Budget).filter(Budget.month == month).all()
    
    result = []
    for budget in budgets:
        stats = calculate_budget_stats(budget, db)
        budget_dict = {
            "id": budget.id,
            "category_id": budget.category_id,
            "amount": budget.amount,
            "month": budget.month,
            "alert_threshold": budget.alert_threshold,
            "category": budget.category,
            **stats
        }
        result.append(BudgetResponse(**budget_dict))
    
    return result

@router.post("/", response_model=BudgetResponse)
def create_budget(budget: BudgetCreate, db: Session = Depends(get_db)):
    # Check if budget already exists for this category/month
    existing = db.query(Budget).filter(
        Budget.category_id == budget.category_id,
        Budget.month == budget.month
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Budget already exists for this category and month")
    
    db_budget = Budget(**budget.model_dump())
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    
    stats = calculate_budget_stats(db_budget, db)
    return BudgetResponse(
        id=db_budget.id,
        category_id=db_budget.category_id,
        amount=db_budget.amount,
        month=db_budget.month,
        alert_threshold=db_budget.alert_threshold,
        category=db_budget.category,
        **stats
    )

@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(budget_id: int, budget: BudgetCreate, db: Session = Depends(get_db)):
    db_budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    for key, value in budget.model_dump().items():
        setattr(db_budget, key, value)
    
    db.commit()
    db.refresh(db_budget)
    
    stats = calculate_budget_stats(db_budget, db)
    return BudgetResponse(
        id=db_budget.id,
        category_id=db_budget.category_id,
        amount=db_budget.amount,
        month=db_budget.month,
        alert_threshold=db_budget.alert_threshold,
        category=db_budget.category,
        **stats
    )

@router.delete("/{budget_id}")
def delete_budget(budget_id: int, db: Session = Depends(get_db)):
    db_budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not db_budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    db.delete(db_budget)
    db.commit()
    return {"message": "Budget deleted"}


# Auto Budget Features

def get_category_spending_history(category_id: int, months: int, db: Session) -> List[float]:
    """Get spending history for a category over past N months"""
    spending = []
    today = datetime.now()
    
    for i in range(months):
        target_date = today - relativedelta(months=i+1)
        year, month = target_date.year, target_date.month
        
        transactions = db.query(Transaction).filter(
            Transaction.category_id == category_id,
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).all()
        
        month_spent = 0.0
        for t in transactions:
            is_credit_card = t.source == 'credit_card'
            is_inverted = t.sign_convention == 'inverted'
            
            if is_credit_card:
                if is_inverted and t.amount > 0:
                    month_spent += t.amount
                elif not is_inverted and t.amount < 0:
                    month_spent += abs(t.amount)
            elif t.amount < 0:
                month_spent += abs(t.amount)
        
        spending.append(month_spent)
    
    return spending


@router.get("/suggestions")
def get_budget_suggestions(months: int = 3, db: Session = Depends(get_db)):
    """Suggest budget amounts based on past spending averages"""
    categories = db.query(Category).filter(
        Category.is_income == False,
        ~Category.name.ilike('%transfer%'),
        ~Category.name.ilike('%payment%')
    ).all()
    suggestions = []
    
    for category in categories:
        history = get_category_spending_history(category.id, months, db)
        if any(h > 0 for h in history):
            avg_spending = sum(history) / len([h for h in history if h > 0]) if any(h > 0 for h in history) else 0
            max_spending = max(history) if history else 0
            min_spending = min([h for h in history if h > 0]) if any(h > 0 for h in history) else 0
            
            # Suggest slightly above average to give buffer
            suggested = round(avg_spending * 1.1, 2)
            
            suggestions.append({
                "category_id": category.id,
                "category_name": category.name,
                "category_icon": category.icon,
                "average_spending": round(avg_spending, 2),
                "max_spending": round(max_spending, 2),
                "min_spending": round(min_spending, 2),
                "suggested_amount": suggested,
                "history": [round(h, 2) for h in history]
            })
    
    # Sort by average spending descending
    suggestions.sort(key=lambda x: x['average_spending'], reverse=True)
    return suggestions


@router.post("/auto-create")
def auto_create_budgets(
    month: str = None,
    months_to_analyze: int = 3,
    buffer_percent: float = 0.1,
    min_spending: float = 10.0,
    apply_to_past: bool = False,
    db: Session = Depends(get_db)
):
    """Auto-create budgets for all categories with spending history"""
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    # Get all months with transactions if applying to past
    target_months = [month]
    if apply_to_past:
        result = db.query(func.distinct(func.strftime("%Y-%m", Transaction.date))).all()
        target_months = sorted([r[0] for r in result if r[0]], reverse=True)
    
    categories = db.query(Category).filter(
        Category.is_income == False,
        ~Category.name.ilike('%transfer%'),
        ~Category.name.ilike('%payment%')
    ).all()
    created = []
    
    for category in categories:
        # Get spending history for suggestions
        history = get_category_spending_history(category.id, months_to_analyze, db)
        spending_months = [h for h in history if h > 0]
        
        if not spending_months:
            continue
            
        avg_spending = sum(spending_months) / len(spending_months)
        
        # Skip very small spending categories
        if avg_spending < min_spending:
            continue
        
        # Add buffer
        budget_amount = round(avg_spending * (1 + buffer_percent), 2)
        
        for target_month in target_months:
            # Skip if budget already exists
            existing = db.query(Budget).filter(
                Budget.category_id == category.id,
                Budget.month == target_month
            ).first()
            if existing:
                continue
            
            db_budget = Budget(
                category_id=category.id,
                amount=budget_amount,
                month=target_month,
                alert_threshold=0.8,
                is_recurring=True,
                auto_adjust=True
            )
            db.add(db_budget)
            created.append({
                "category": category.name,
                "month": target_month,
                "amount": budget_amount
            })
    
    db.commit()
    return {"created": len(created), "budgets": created}


@router.post("/rollover")
def rollover_budgets(
    from_month: str = None,
    to_month: str = None,
    db: Session = Depends(get_db)
):
    """Rollover recurring budgets to next month"""
    if not from_month:
        prev = datetime.now() - relativedelta(months=1)
        from_month = prev.strftime("%Y-%m")
    
    if not to_month:
        to_month = datetime.now().strftime("%Y-%m")
    
    # Get recurring budgets from previous month
    recurring = db.query(Budget).filter(
        Budget.month == from_month,
        Budget.is_recurring == True
    ).all()
    
    created = []
    for budget in recurring:
        # Skip if already exists
        existing = db.query(Budget).filter(
            Budget.category_id == budget.category_id,
            Budget.month == to_month
        ).first()
        if existing:
            continue
        
        # Calculate new amount if auto_adjust is enabled
        new_amount = budget.amount
        if budget.auto_adjust:
            history = get_category_spending_history(budget.category_id, 3, db)
            if any(h > 0 for h in history):
                avg = sum(history) / len([h for h in history if h > 0])
                # Adjust towards average with 10% buffer
                new_amount = round(avg * 1.1, 2)
        
        new_budget = Budget(
            category_id=budget.category_id,
            amount=new_amount,
            month=to_month,
            alert_threshold=budget.alert_threshold,
            is_recurring=budget.is_recurring,
            auto_adjust=budget.auto_adjust
        )
        db.add(new_budget)
        created.append({
            "category_id": budget.category_id,
            "old_amount": budget.amount,
            "new_amount": new_amount
        })
    
    db.commit()
    return {"rolled_over": len(created), "budgets": created}


@router.post("/adjust")
def adjust_budgets(month: str = None, db: Session = Depends(get_db)):
    """Adjust budgets based on spending trends"""
    if not month:
        month = datetime.now().strftime("%Y-%m")
    
    budgets = db.query(Budget).filter(
        Budget.month == month,
        Budget.auto_adjust == True
    ).all()
    
    adjusted = []
    for budget in budgets:
        history = get_category_spending_history(budget.category_id, 3, db)
        if not any(h > 0 for h in history):
            continue
        
        avg = sum(history) / len([h for h in history if h > 0])
        suggested = round(avg * 1.1, 2)
        
        # Only adjust if difference is significant (>10%)
        diff_percent = abs(budget.amount - suggested) / budget.amount if budget.amount > 0 else 1
        if diff_percent > 0.1:
            old_amount = budget.amount
            budget.amount = suggested
            adjusted.append({
                "category_id": budget.category_id,
                "old_amount": old_amount,
                "new_amount": suggested,
                "reason": "spending_trend"
            })
    
    db.commit()
    return {"adjusted": len(adjusted), "budgets": adjusted}
