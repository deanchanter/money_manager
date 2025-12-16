from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
from models import Category, Transaction, Budget, SavingsGoal
from routers import (
    transactions_router,
    categories_router,
    budgets_router,
    savings_goals_router,
    analytics_router,
    import_export_router,
    accounts_router
)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Money Manager API",
    description="API for personal finance management",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(transactions_router)
app.include_router(categories_router)
app.include_router(budgets_router)
app.include_router(savings_goals_router)
app.include_router(analytics_router)
app.include_router(import_export_router)
app.include_router(accounts_router)

@app.get("/")
def root():
    return {"message": "Money Manager API", "docs": "/docs"}

@app.on_event("startup")
def seed_default_categories():
    """Seed default categories if none exist"""
    from database import SessionLocal
    db = SessionLocal()
    
    if db.query(Category).count() == 0:
        default_categories = [
            {"name": "Groceries", "icon": "🛒", "color": "#10B981", "keywords": "grocery,supermarket,walmart,target,costco,trader joe,whole foods,safeway,kroger,aldi"},
            {"name": "Dining", "icon": "🍽️", "color": "#F59E0B", "keywords": "restaurant,cafe,coffee,starbucks,mcdonalds,uber eats,doordash,grubhub"},
            {"name": "Transportation", "icon": "🚗", "color": "#3B82F6", "keywords": "gas,fuel,uber,lyft,parking,transit,metro,bus"},
            {"name": "Utilities", "icon": "💡", "color": "#8B5CF6", "keywords": "electric,water,gas,internet,phone,utility,comcast,verizon,at&t"},
            {"name": "Entertainment", "icon": "🎬", "color": "#EC4899", "keywords": "netflix,spotify,hulu,movie,theater,concert,game"},
            {"name": "Shopping", "icon": "🛍️", "color": "#F97316", "keywords": "amazon,ebay,clothing,electronics,online"},
            {"name": "Healthcare", "icon": "🏥", "color": "#EF4444", "keywords": "pharmacy,doctor,hospital,medical,cvs,walgreens,health"},
            {"name": "Housing", "icon": "🏠", "color": "#6366F1", "keywords": "rent,mortgage,hoa,maintenance,repair"},
            {"name": "Insurance", "icon": "🛡️", "color": "#14B8A6", "keywords": "insurance,premium,geico,state farm,allstate"},
            {"name": "Subscriptions", "icon": "📱", "color": "#A855F7", "keywords": "subscription,membership,monthly,annual"},
            {"name": "Credit Card Payment", "icon": "💳", "color": "#64748B", "keywords": "credit card,card payment,payment thank you,autopay,credit card payment"},
            {"name": "Transfer", "icon": "🔄", "color": "#94A3B8", "keywords": "transfer,zelle,venmo,paypal"},
            {"name": "Income", "icon": "💰", "color": "#22C55E", "is_income": True, "keywords": "salary,paycheck,direct deposit,payroll"},
            {"name": "Other", "icon": "📁", "color": "#6B7280", "keywords": ""}
        ]
        
        for cat_data in default_categories:
            db.add(Category(**cat_data))
        
        db.commit()
    
    db.close()

def run():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    run()
