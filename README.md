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
- Net worth overview, with each account grouped as **everyday**, **short-term
  savings** (emergency fund and sinking funds — counted in net worth, totalled
  on its own line) or **long-term savings** (retirement — tracked and totalled
  separately, but left out so it does not swamp the headline figure)

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

## Automatic Sync (SimpleFIN)

Pulls transactions and balances straight from your banks instead of downloading CSVs.
Requires a [SimpleFIN Bridge](https://beta-bridge.simplefin.org/) subscription (~$15/yr).

### One-time setup

Put a setup token from the SimpleFIN Bridge UI in `.env` at the repo root:

```
SIMPLEFIN_SETUP_TOKEN=<token>
```

Then claim it:

```bash
cd backend && uv run python scripts/simplefin_setup.py
```

Setup tokens are **single-use**. The script exchanges the token for a permanent access
URL and writes it back to `.env` as `SIMPLEFIN_ACCESS_URL` before doing anything else,
so resetting the database never costs you a new token.

### Linking and syncing

Open the **Sync** page, link each bank account to a local account, and hit *Sync now*.
Only linked accounts are pulled. Linking to an existing account preserves its history,
categories and learned rules.

The same sync is available from the command line, without the API server running:

```bash
cd backend && uv run python scripts/simplefin_sync.py --days 30
```

To inspect a connection without touching the database (defaults to SimpleFIN's public
demo server, so it works with no credentials):

```bash
cd backend && uv run python scripts/simplefin_probe.py
```

### How it behaves

- **Idempotent.** Transactions are keyed on `(account_id, external_id)` — SimpleFIN ids
  are unique per account, not globally. Re-syncing the same window changes nothing.
- **Balances are authoritative.** Each sync rewrites `starting_balance` on linked
  accounts so the computed balance matches what the bank reports. Pass
  `anchor_balances=false` to opt out. Without it, balances reflect only the synced
  window and are meaningless.
- **Descriptions are the raw statement text**, matching what CSV import stores, so
  existing learned categorization rules keep working. The tidied `payee` goes to `notes`.
- **Existing rows are adopted, not duplicated.** A transaction already imported from CSV
  is claimed by matching date + amount (description preferred) rather than re-inserted.
- **Long ranges are paged** in 45-day windows; SimpleFIN silently caps long ranges
  instead of erroring.
- **Transfers between your own accounts are detected and excluded** from income and
  expense totals. A credit card payment is matched to its opposite leg on the card;
  where an institution reports no transactions (Betterment reports balances only), a
  transaction naming another of your accounts is flagged on its own. Run
  `POST /api/simplefin/detect-transfers` to backfill older imports.

### Known limits

- History depth is set by each institution — typically ~90 days. A deeper backfill
  silently returns only what the bank has.
- `mcc` (merchant category code) is mapped to categories in `services/mcc.py`, but every
  institution tested returns it as null, so it currently contributes nothing.
- Multi-currency accounts are flagged in sync warnings but not converted.
- Transfer detection keys off account names, so naming an account after somewhere you
  also shop would misfire. Matching is on whole words, so "Chase" does not match
  "PURCHASE". Any category can also be marked *Money between my own accounts* on the
  Categories page to exclude it from totals.

## CSV Import

Supports various CSV formats with configurable column mapping:
- Date column (auto-detects format)
- Description column
- Amount column
- Optional category column
- Optional transaction type column (for debit/credit)
- Sign convention: standard (negative = expense) or inverted (positive = expense for credit cards)

