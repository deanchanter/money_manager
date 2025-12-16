export interface Account {
  id: number;
  name: string;
  account_type: string;
  starting_balance: number;
  starting_date: string | null;
  icon: string;
  color: string;
  current_balance: number;
}

export interface AccountSummary {
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
  accounts: {
    id: number;
    name: string;
    account_type: string;
    icon: string;
    color: string;
    balance: number;
  }[];
}

export interface Category {
  id: number;
  name: string;
  icon: string;
  color: string;
  is_income: boolean;
  keywords: string;
}

export interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  category_id: number | null;
  source: string;
  sign_convention: string;
  notes: string;
  category: Category | null;
}

export interface Budget {
  id: number;
  category_id: number;
  amount: number;
  month: string;
  alert_threshold: number;
  is_recurring: boolean;
  auto_adjust: boolean;
  category: Category | null;
  spent: number;
  remaining: number;
  percentage: number;
  is_over_budget: boolean;
  is_alert: boolean;
}

export interface BudgetSuggestion {
  category_id: number;
  category_name: string;
  category_icon: string;
  average_spending: number;
  max_spending: number;
  min_spending: number;
  suggested_amount: number;
  history: number[];
}

export interface SavingsGoal {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  target_date: string | null;
  icon: string;
  color: string;
  percentage: number;
  remaining: number;
}

export interface SpendingByCategory {
  category_id: number;
  category_name: string;
  category_color: string;
  category_icon?: string;
  total: number;
  percentage: number;
  count?: number;
}

export interface MonthlySpending {
  month: string;
  income: number;
  expenses: number;
  net: number;
}

export interface DashboardStats {
  total_income: number;
  total_expenses: number;
  net_balance: number;
  spending_by_category: SpendingByCategory[];
  monthly_trend: MonthlySpending[];
  budget_alerts: Budget[];
}
