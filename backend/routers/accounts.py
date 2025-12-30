from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from database import get_db
from models import Account, Transaction
from schemas import AccountCreate, AccountResponse, AccountUpdate

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

def calculate_account_balance(account: Account, db: Session) -> float:
    """Calculate current balance for an account"""
    # Only count transactions after the starting date
    query = db.query(func.sum(Transaction.amount)).filter(
        Transaction.account_id == account.id
    )
    
    if account.starting_date:
        query = query.filter(Transaction.date >= account.starting_date)
    
    total_change = query.scalar() or 0.0
    
    # For credit card accounts, we need to flip the sign
    # Credit card: positive amounts are charges (reduce balance/increase debt)
    if account.account_type == "credit_card":
        return account.starting_balance - total_change
    else:
        return account.starting_balance + total_change

@router.get("", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).all()
    result = []
    for account in accounts:
        balance = calculate_account_balance(account, db)
        result.append(AccountResponse(
            id=account.id,
            name=account.name,
            account_type=account.account_type,
            starting_balance=account.starting_balance,
            icon=account.icon,
            color=account.color,
            current_balance=round(balance, 2)
        ))
    return result

@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    balance = calculate_account_balance(account, db)
    return AccountResponse(
        id=account.id,
        name=account.name,
        account_type=account.account_type,
        starting_balance=account.starting_balance,
        icon=account.icon,
        color=account.color,
        current_balance=round(balance, 2)
    )

@router.post("", response_model=AccountResponse)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    existing = db.query(Account).filter(Account.name == account.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Account with this name already exists")
    
    db_account = Account(**account.model_dump())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    
    return AccountResponse(
        id=db_account.id,
        name=db_account.name,
        account_type=db_account.account_type,
        starting_balance=db_account.starting_balance,
        icon=db_account.icon,
        color=db_account.color,
        current_balance=db_account.starting_balance
    )

@router.put("/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, account: AccountUpdate, db: Session = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    update_data = account.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_account, key, value)
    
    db.commit()
    db.refresh(db_account)
    
    balance = calculate_account_balance(db_account, db)
    return AccountResponse(
        id=db_account.id,
        name=db_account.name,
        account_type=db_account.account_type,
        starting_balance=db_account.starting_balance,
        icon=db_account.icon,
        color=db_account.color,
        current_balance=round(balance, 2)
    )

@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Check if account has transactions
    txn_count = db.query(Transaction).filter(Transaction.account_id == account_id).count()
    if txn_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete account with {txn_count} transactions. Reassign or delete them first.")
    
    db.delete(db_account)
    db.commit()
    return {"message": "Account deleted"}

@router.get("/summary/total")
def get_total_balance(db: Session = Depends(get_db)):
    """Get total balance across all accounts"""
    accounts = db.query(Account).all()
    
    total_assets = 0.0  # checking, savings, investment, cash
    total_liabilities = 0.0  # credit cards
    
    account_balances = []
    for account in accounts:
        balance = calculate_account_balance(account, db)
        account_balances.append({
            "id": account.id,
            "name": account.name,
            "account_type": account.account_type,
            "icon": account.icon,
            "color": account.color,
            "balance": round(balance, 2)
        })
        
        if account.account_type == "credit_card":
            total_liabilities += balance
        else:
            total_assets += balance
    
    return {
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "net_worth": round(total_assets - total_liabilities, 2),
        "accounts": account_balances
    }
