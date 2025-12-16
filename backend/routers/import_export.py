from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
import pandas as pd
import io
from database import get_db
from models import Transaction, Category, AutoCategoryRule
from schemas import TransactionResponse

router = APIRouter(prefix="/api", tags=["import-export"])

@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    date_column: str = "date",
    description_column: str = "description",
    amount_column: str = "amount",
    category_column: str = "",  # Optional category column from statement
    transaction_type_column: str = "",  # Optional column for credit/debit (e.g., Capital One)
    source: str = "bank",  # bank, credit_card, cash, investment
    sign_convention: str = "standard",  # standard (neg=expense), inverted (pos=expense for amex-style), or type_column
    db: Session = Depends(get_db)
):
    """
    Import transactions from a CSV file.
    Supports various CSV formats by specifying column names.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")
    
    # Normalize column names (lowercase, strip whitespace)
    df.columns = df.columns.str.lower().str.strip()
    date_column = date_column.lower().strip()
    description_column = description_column.lower().strip()
    amount_column = amount_column.lower().strip()
    category_column = category_column.lower().strip() if category_column else ""
    transaction_type_column = transaction_type_column.lower().strip() if transaction_type_column else ""
    
    # Validate required columns
    required_columns = [date_column, description_column, amount_column]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        available = list(df.columns)
        raise HTTPException(
            status_code=400, 
            detail=f"Missing columns: {missing}. Available columns: {available}"
        )
    
    # Get categories for auto-categorization
    categories = db.query(Category).all()
    category_map = {cat.name.lower(): cat.id for cat in categories}
    
    def find_category_by_name(name: str) -> Optional[int]:
        """Find category by name (case-insensitive, partial match)"""
        if not name or pd.isna(name):
            return None
        name_lower = str(name).lower().strip()
        # Exact match first
        if name_lower in category_map:
            return category_map[name_lower]
        # Partial match
        for cat_name, cat_id in category_map.items():
            if name_lower in cat_name or cat_name in name_lower:
                return cat_id
        return None
    
    def auto_categorize(description: str) -> Optional[int]:
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
        for category in categories:
            if category.keywords:
                keywords = [k.strip().lower() for k in category.keywords.split(",")]
                for keyword in keywords:
                    if keyword and keyword in description_lower:
                        return category.id
        return None
    
    imported = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            # Parse date - auto-detect format
            date_str = str(row[date_column]).strip()
            transaction_date = None
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y", "%m-%d-%Y", "%Y/%m/%d"]:
                try:
                    transaction_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if not transaction_date:
                raise ValueError(f"Could not parse date: {date_str}")
            
            # Parse amount
            amount_str = str(row[amount_column]).replace('$', '').replace(',', '').strip()
            amount = abs(float(amount_str))  # Start with absolute value
            
            # Determine sign based on transaction type column or existing sign
            if transaction_type_column and transaction_type_column in df.columns:
                txn_type = str(row[transaction_type_column]).lower().strip()
                # Debit = expense (negative for bank, positive for credit card)
                # Credit = income/payment
                if txn_type in ['debit', 'sale', 'purchase', 'withdrawal']:
                    if source == 'credit_card':
                        amount = abs(amount)  # Positive for credit card expenses
                    else:
                        amount = -abs(amount)  # Negative for bank expenses
                elif txn_type in ['credit', 'payment', 'deposit', 'refund']:
                    if source == 'credit_card':
                        amount = -abs(amount)  # Negative for credit card payments
                    else:
                        amount = abs(amount)  # Positive for bank income
            else:
                # Use original sign from the CSV
                original_amount = float(str(row[amount_column]).replace('$', '').replace(',', '').strip())
                amount = original_amount
            
            # Get description
            description = str(row[description_column]).strip()
            
            # Get category - try from CSV first, then auto-categorize
            category_id = None
            if category_column and category_column in df.columns:
                category_id = find_category_by_name(row[category_column])
            if not category_id:
                category_id = auto_categorize(description)
            
            # Create transaction
            transaction = Transaction(
                date=transaction_date,
                description=description,
                amount=amount,
                category_id=category_id,
                source=source,
                sign_convention=sign_convention
            )
            db.add(transaction)
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
    
    db.commit()
    
    return {
        "message": f"Successfully imported {imported} transactions",
        "imported": imported,
        "errors": errors[:10] if errors else []  # Return first 10 errors
    }

@router.get("/export/csv")
def export_csv(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Export transactions to CSV"""
    query = db.query(Transaction)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    
    transactions = query.order_by(Transaction.date.desc()).all()
    
    data = []
    for t in transactions:
        data.append({
            "Date": t.date.strftime("%Y-%m-%d"),
            "Description": t.description,
            "Amount": t.amount,
            "Category": t.category.name if t.category else "Uncategorized",
            "Notes": t.notes or ""
        })
    
    df = pd.DataFrame(data)
    
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transactions_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@router.get("/export/report")
def export_report(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Export a spending report"""
    from sqlalchemy import func
    
    if not start_date:
        today = datetime.now()
        start_date = date(today.year, today.month, 1)
    if not end_date:
        end_date = date.today()
    
    # Get transactions
    transactions = db.query(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    total_income = sum(t.amount for t in transactions if t.amount > 0)
    total_expenses = abs(sum(t.amount for t in transactions if t.amount < 0))
    
    # Spending by category
    category_spending = db.query(
        Category.name,
        func.sum(func.abs(Transaction.amount)).label('total')
    ).join(Transaction).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.amount < 0
    ).group_by(Category.id).all()
    
    report_lines = [
        f"Money Manager Report",
        f"Period: {start_date} to {end_date}",
        f"",
        f"Summary",
        f"{'='*40}",
        f"Total Income:   ${total_income:,.2f}",
        f"Total Expenses: ${total_expenses:,.2f}",
        f"Net Balance:    ${total_income - total_expenses:,.2f}",
        f"",
        f"Spending by Category",
        f"{'='*40}"
    ]
    
    for cat_name, total in category_spending:
        percentage = (total / total_expenses * 100) if total_expenses > 0 else 0
        report_lines.append(f"{cat_name}: ${total:,.2f} ({percentage:.1f}%)")
    
    report_content = "\n".join(report_lines)
    
    return StreamingResponse(
        io.BytesIO(report_content.encode()),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=report_{datetime.now().strftime('%Y%m%d')}.txt"}
    )
