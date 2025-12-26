from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from database import get_db
from models import Transaction, Category, AutoCategoryRule
from schemas import TransactionCreate, TransactionResponse, TransactionUpdate

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

@router.get("/", response_model=List[TransactionResponse])
def get_transactions(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Transaction)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if category_id == 'null':
        query = query.filter(Transaction.category_id.is_(None))
    elif category_id:
        query = query.filter(Transaction.category_id == int(category_id))
    
    return query.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.post("/", response_model=TransactionResponse)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    db_transaction = Transaction(**transaction.model_dump())
    
    # Auto-categorize if no category provided
    if not db_transaction.category_id:
        db_transaction.category_id = auto_categorize(db_transaction.description, db)
    
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(transaction_id: int, transaction: dict, db: Session = Depends(get_db)):
    from datetime import datetime
    
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    old_category_id = db_transaction.category_id
    
    allowed_fields = ['date', 'description', 'amount', 'category_id', 'account_id', 'source', 'sign_convention', 'notes']
    for key, value in transaction.items():
        if key in allowed_fields:
            # Convert date string to date object
            if key == 'date' and isinstance(value, str):
                value = datetime.strptime(value, '%Y-%m-%d').date()
            setattr(db_transaction, key, value)
    
    # Learn from manual categorization and apply to similar transactions
    # Only if setting a category (not uncategorizing)
    if 'category_id' in transaction:
        new_category_id = transaction.get('category_id')
        if new_category_id and new_category_id != old_category_id:
            learn_category_rule(db_transaction.description, new_category_id, db)
            # Update other uncategorized transactions with similar descriptions
            apply_category_to_similar(db_transaction.description, new_category_id, db_transaction.id, db)
    
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def learn_category_rule(description: str, category_id: int, db: Session):
    """Learn a new auto-categorization rule from user's manual categorization"""
    # Clean up the description to create a pattern
    pattern = description.strip().lower()
    
    # Check if we already have a rule for this pattern
    existing = db.query(AutoCategoryRule).filter(
        AutoCategoryRule.pattern == pattern
    ).first()
    
    if existing:
        # Update existing rule
        existing.category_id = category_id
        existing.updated_at = datetime.now()
    else:
        # Create new rule with high priority (user-defined rules take precedence)
        rule = AutoCategoryRule(
            pattern=pattern,
            category_id=category_id,
            match_type="contains",
            priority=100  # Higher than default category keywords
        )
        db.add(rule)

def apply_category_to_similar(description: str, category_id: int, exclude_id: int, db: Session):
    """Apply category to other transactions with similar descriptions"""
    description_clean = description.strip()
    
    # Find uncategorized transactions with exact same description (case-insensitive)
    from sqlalchemy import func
    similar = db.query(Transaction).filter(
        Transaction.id != exclude_id,
        Transaction.category_id.is_(None),
        func.lower(Transaction.description) == description_clean.lower()
    ).all()
    
    for txn in similar:
        txn.category_id = category_id

@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    db.delete(db_transaction)
    db.commit()
    return {"message": "Transaction deleted"}

def auto_categorize(description: str, db: Session) -> Optional[int]:
    """Auto-categorize based on learned rules and category keywords"""
    description_lower = description.lower()
    
    # First check learned rules (higher priority)
    learned_rules = db.query(AutoCategoryRule).order_by(AutoCategoryRule.priority.desc()).all()
    for rule in learned_rules:
        if rule.match_type == "exact" and rule.pattern == description_lower:
            return rule.category_id
        elif rule.match_type == "starts_with" and description_lower.startswith(rule.pattern):
            return rule.category_id
        elif rule.match_type == "contains" and rule.pattern in description_lower:
            return rule.category_id
    
    # Fall back to category keywords
    categories = db.query(Category).all()
    
    for category in categories:
        if category.keywords:
            keywords = [k.strip().lower() for k in category.keywords.split(",")]
            for keyword in keywords:
                if keyword and keyword in description_lower:
                    return category.id
    return None
