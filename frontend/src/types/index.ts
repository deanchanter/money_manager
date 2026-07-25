export interface Account {
  id: number;
  name: string;
  account_type: string;
  starting_balance: number;
  starting_date: string | null;
  icon: string;
  color: string;
  net_worth_group: string; // everyday | short_term | long_term
  current_balance: number;
}

export interface AccountSummary {
  total_assets: number;
  total_liabilities: number;
  net_worth: number;
  accounts: AccountBalance[];
  short_term_accounts: AccountBalance[];
  short_term_total: number;
  long_term_accounts: AccountBalance[];
  long_term_total: number;
}

export interface AccountBalance {
  id: number;
  name: string;
  account_type: string;
  icon: string;
  color: string;
  balance: number;
}

export interface Category {
  id: number;
  name: string;
  icon: string;
  color: string;
  is_income: boolean;
  is_transfer: boolean;
  keywords: string;
}

export interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  category_id: number | null;
  account_id: number | null;
  source: string;
  sign_convention: string;
  notes: string;
  category: Category | null;
  account: { id: number; name: string; icon: string } | null;
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
  is_income: boolean;
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
  category_id: number | null;
  percentage: number;
  remaining: number;
  category: Category | null;
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

// SimpleFIN
export interface SimpleFinLinkedAccount {
  account_id: number;
  name: string;
  account_type: string;
  simplefin_account_id: string;
  last_synced_at: string | null;
}

export interface SimpleFinStatus {
  connected: boolean;
  org_name: string | null;
  endpoint: string | null;
  last_synced_at: string | null;
  linked_accounts: SimpleFinLinkedAccount[];
}

export interface SimpleFinRemoteAccount {
  simplefin_account_id: string;
  name: string;
  balance: string;
  currency: string;
  org: string | null;
  linked_account_id: number | null;
  linked_account_name: string | null;
}

export interface SimpleFinSyncResult {
  imported: number;
  updated: number;
  unchanged: number;
  adopted: number;
  skipped_unlinked: number;
  transfers_detected: number;
  accounts_synced: string[];
  balances: {
    account: string;
    reported_balance: number;
    starting_balance_set_to: number;
    as_of: string | null;
  }[];
  unlinked_accounts: { simplefin_account_id: string; name: string; balance: string }[];
  warnings: string[];
  message: string;
}
