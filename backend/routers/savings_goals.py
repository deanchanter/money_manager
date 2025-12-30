from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
from database import get_db
from models import SavingsGoal, Category
from schemas import SavingsGoalCreate, SavingsGoalResponse, SavingsGoalUpdate, CategoryResponse

router = APIRouter(prefix="/api/savings-goals", tags=["savings-goals"])

def calculate_goal_stats(goal: SavingsGoal) -> dict:
    """Calculate percentage and remaining for a savings goal"""
    percentage = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
    remaining = goal.target_amount - goal.current_amount
    
    return {
        "percentage": round(percentage, 2),
        "remaining": round(remaining, 2)
    }

def build_goal_response(goal: SavingsGoal) -> SavingsGoalResponse:
    """Build a SavingsGoalResponse from a SavingsGoal model"""
    stats = calculate_goal_stats(goal)
    category_response = None
    if goal.category:
        category_response = CategoryResponse(
            id=goal.category.id,
            name=goal.category.name,
            icon=goal.category.icon,
            color=goal.category.color,
            is_income=goal.category.is_income,
            keywords=goal.category.keywords
        )
    return SavingsGoalResponse(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        icon=goal.icon,
        color=goal.color,
        category_id=goal.category_id,
        category=category_response,
        **stats
    )

@router.get("", response_model=List[SavingsGoalResponse])
def get_savings_goals(db: Session = Depends(get_db)):
    goals = db.query(SavingsGoal).options(joinedload(SavingsGoal.category)).all()
    return [build_goal_response(goal) for goal in goals]

@router.get("/{goal_id}", response_model=SavingsGoalResponse)
def get_savings_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoal).options(joinedload(SavingsGoal.category)).filter(SavingsGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    return build_goal_response(goal)

@router.post("", response_model=SavingsGoalResponse)
def create_savings_goal(goal: SavingsGoalCreate, db: Session = Depends(get_db)):
    db_goal = SavingsGoal(**goal.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    # Reload with category relationship
    db_goal = db.query(SavingsGoal).options(joinedload(SavingsGoal.category)).filter(SavingsGoal.id == db_goal.id).first()
    return build_goal_response(db_goal)

@router.put("/{goal_id}", response_model=SavingsGoalResponse)
def update_savings_goal(goal_id: int, goal: SavingsGoalUpdate, db: Session = Depends(get_db)):
    db_goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    
    update_data = goal.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_goal, key, value)
    
    db.commit()
    db.refresh(db_goal)
    # Reload with category relationship
    db_goal = db.query(SavingsGoal).options(joinedload(SavingsGoal.category)).filter(SavingsGoal.id == db_goal.id).first()
    return build_goal_response(db_goal)

@router.post("/{goal_id}/add-funds")
def add_funds_to_goal(goal_id: int, amount: float, db: Session = Depends(get_db)):
    db_goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    
    db_goal.current_amount += amount
    db.commit()
    db.refresh(db_goal)
    # Reload with category relationship
    db_goal = db.query(SavingsGoal).options(joinedload(SavingsGoal.category)).filter(SavingsGoal.id == db_goal.id).first()
    return build_goal_response(db_goal)

@router.delete("/{goal_id}")
def delete_savings_goal(goal_id: int, db: Session = Depends(get_db)):
    db_goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    
    db.delete(db_goal)
    db.commit()
    return {"message": "Savings goal deleted"}
