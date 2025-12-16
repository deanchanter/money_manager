from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import SavingsGoal
from schemas import SavingsGoalCreate, SavingsGoalResponse, SavingsGoalUpdate

router = APIRouter(prefix="/api/savings-goals", tags=["savings-goals"])

def calculate_goal_stats(goal: SavingsGoal) -> dict:
    """Calculate percentage and remaining for a savings goal"""
    percentage = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
    remaining = goal.target_amount - goal.current_amount
    
    return {
        "percentage": round(percentage, 2),
        "remaining": round(remaining, 2)
    }

@router.get("/", response_model=List[SavingsGoalResponse])
def get_savings_goals(db: Session = Depends(get_db)):
    goals = db.query(SavingsGoal).all()
    
    result = []
    for goal in goals:
        stats = calculate_goal_stats(goal)
        goal_dict = {
            "id": goal.id,
            "name": goal.name,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
            "target_date": goal.target_date,
            "icon": goal.icon,
            "color": goal.color,
            **stats
        }
        result.append(SavingsGoalResponse(**goal_dict))
    
    return result

@router.get("/{goal_id}", response_model=SavingsGoalResponse)
def get_savings_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    
    stats = calculate_goal_stats(goal)
    return SavingsGoalResponse(
        id=goal.id,
        name=goal.name,
        target_amount=goal.target_amount,
        current_amount=goal.current_amount,
        target_date=goal.target_date,
        icon=goal.icon,
        color=goal.color,
        **stats
    )

@router.post("/", response_model=SavingsGoalResponse)
def create_savings_goal(goal: SavingsGoalCreate, db: Session = Depends(get_db)):
    db_goal = SavingsGoal(**goal.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    
    stats = calculate_goal_stats(db_goal)
    return SavingsGoalResponse(
        id=db_goal.id,
        name=db_goal.name,
        target_amount=db_goal.target_amount,
        current_amount=db_goal.current_amount,
        target_date=db_goal.target_date,
        icon=db_goal.icon,
        color=db_goal.color,
        **stats
    )

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
    
    stats = calculate_goal_stats(db_goal)
    return SavingsGoalResponse(
        id=db_goal.id,
        name=db_goal.name,
        target_amount=db_goal.target_amount,
        current_amount=db_goal.current_amount,
        target_date=db_goal.target_date,
        icon=db_goal.icon,
        color=db_goal.color,
        **stats
    )

@router.post("/{goal_id}/add-funds")
def add_funds_to_goal(goal_id: int, amount: float, db: Session = Depends(get_db)):
    db_goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    
    db_goal.current_amount += amount
    db.commit()
    db.refresh(db_goal)
    
    stats = calculate_goal_stats(db_goal)
    return SavingsGoalResponse(
        id=db_goal.id,
        name=db_goal.name,
        target_amount=db_goal.target_amount,
        current_amount=db_goal.current_amount,
        target_date=db_goal.target_date,
        icon=db_goal.icon,
        color=db_goal.color,
        **stats
    )

@router.delete("/{goal_id}")
def delete_savings_goal(goal_id: int, db: Session = Depends(get_db)):
    db_goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not db_goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")
    
    db.delete(db_goal)
    db.commit()
    return {"message": "Savings goal deleted"}
