# Money Manager

A personal finance management web application for tracking spending, budgets, accounts, and savings goals.

## Features

### Transactions
- Import transactions from CSV files (supports Chase, Amex, Capital One formats)
- Auto-categorization using keywords and learned rules
- Manual categorization that teaches the system for future imports
- Filter by month, category, and search text

### Budgets
- Set monthly budgets per category
- Auto-create budgets based on past spending history
- Recurring budgets that rollover monthly
- Auto-adjust budgets based on spending trends
- Income tracking with % of income spent
- Click on category to view transactions

### Accounts
- Track multiple accounts (checking, savings, credit card, investment, cash)
- Set starting balance with a date
- Automatic balance calculation from transactions
- Net worth overview

### Categories
- Customizable categories with icons and colors
- Keyword-based auto-categorization
- Learned categorization from user corrections

### Savings Goals
- Set savings targets with deadlines
- Track progress toward goals

### Dashboard
- Monthly spending overview
- Account balances and net worth
- Spending by category charts
- Budget alerts

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Frontend**: React, TypeScript, Tailwind CSS, Chart.js

## Getting Started

### Backend

```bash
cd backend
uv sync
uv run start
```

The API runs at http://localhost:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:3000

## CSV Import

Supports various CSV formats with configurable column mapping:
- Date column (auto-detects format)
- Description column
- Amount column
- Optional category column
- Optional transaction type column (for debit/credit)
- Sign convention: standard (negative = expense) or inverted (positive = expense for credit cards)

