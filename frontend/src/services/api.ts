import axios from 'axios';
import type { Account, AccountSummary, Category, Transaction, Budget, SavingsGoal, DashboardStats } from '../types';

const api = axios.create({
  baseURL: '/api',
});

// Accounts
export const getAccounts = () => api.get<Account[]>('/accounts').then(res => res.data);
export const getAccount = (id: number) => api.get<Account>(`/accounts/${id}`).then(res => res.data);
export const createAccount = (data: Partial<Account>) => api.post<Account>('/accounts', data).then(res => res.data);
export const updateAccount = (id: number, data: Partial<Account>) => api.put<Account>(`/accounts/${id}`, data).then(res => res.data);
export const deleteAccount = (id: number) => api.delete(`/accounts/${id}`);
export const getAccountSummary = () => api.get<AccountSummary>('/accounts/summary/total').then(res => res.data);

// Categories
export const getCategories = () => api.get<Category[]>('/categories').then(res => res.data);
export const createCategory = (data: Partial<Category>) => api.post<Category>('/categories', data).then(res => res.data);
export const updateCategory = (id: number, data: Partial<Category>) => api.put<Category>(`/categories/${id}`, data).then(res => res.data);
export const deleteCategory = (id: number) => api.delete(`/categories/${id}`);

// Transactions
export const getTransactions = (params?: { start_date?: string; end_date?: string; category_id?: number | string; limit?: number }) => 
  api.get<Transaction[]>('/transactions', { params: { limit: 500, ...params } }).then(res => res.data);
export const createTransaction = (data: Partial<Transaction>) => api.post<Transaction>('/transactions', data).then(res => res.data);
export const updateTransaction = (id: number, data: Partial<Transaction>) => api.put<Transaction>(`/transactions/${id}`, data).then(res => res.data);
export const deleteTransaction = (id: number) => api.delete(`/transactions/${id}`);
export const bulkUpdateTransactions = (transactionIds: number[], data: { category_id?: number | null; notes?: string }) => 
  api.post('/transactions/bulk-update', { transaction_ids: transactionIds, data }).then(res => res.data);
export const bulkDeleteTransactions = (transactionIds: number[]) => 
  api.post('/transactions/bulk-delete', { transaction_ids: transactionIds }).then(res => res.data);

// Budgets
export const getBudgets = (month?: string) => api.get<Budget[]>('/budgets', { params: { month } }).then(res => res.data);
export const createBudget = (data: Partial<Budget>) => api.post<Budget>('/budgets', data).then(res => res.data);
export const updateBudget = (id: number, data: Partial<Budget>) => api.put<Budget>(`/budgets/${id}`, data).then(res => res.data);
export const deleteBudget = (id: number) => api.delete(`/budgets/${id}`);
export const getBudgetSuggestions = (months?: number) => api.get('/budgets/suggestions', { params: { months } }).then(res => res.data);
export const autoCreateBudgets = (month?: string, applyToPast?: boolean) => api.post('/budgets/auto-create', null, { params: { month, apply_to_past: applyToPast } }).then(res => res.data);
export const rolloverBudgets = (fromMonth?: string, toMonth?: string) => api.post('/budgets/rollover', null, { params: { from_month: fromMonth, to_month: toMonth } }).then(res => res.data);
export const adjustBudgets = (month?: string) => api.post('/budgets/adjust', null, { params: { month } }).then(res => res.data);

// Savings Goals
export const getSavingsGoals = () => api.get<SavingsGoal[]>('/savings-goals').then(res => res.data);
export const createSavingsGoal = (data: Partial<SavingsGoal>) => api.post<SavingsGoal>('/savings-goals', data).then(res => res.data);
export const updateSavingsGoal = (id: number, data: Partial<SavingsGoal>) => api.put<SavingsGoal>(`/savings-goals/${id}`, data).then(res => res.data);
export const addFundsToGoal = (id: number, amount: number) => api.post<SavingsGoal>(`/savings-goals/${id}/add-funds`, null, { params: { amount } }).then(res => res.data);
export const deleteSavingsGoal = (id: number) => api.delete(`/savings-goals/${id}`);

// Analytics
export const getDashboardStats = (params?: { start_date?: string; end_date?: string }) => 
  api.get<DashboardStats>('/analytics/dashboard', { params }).then(res => res.data);

export const getAllTimeBalance = (startingBalance: number = 0) => 
  api.get<{ starting_balance: number; total_income: number; total_expenses: number; net_balance: number }>(
    '/analytics/all-time-balance', 
    { params: { starting_balance: startingBalance } }
  ).then(res => res.data);

// Import/Export
export const importCSV = (file: File, options: { date_column: string; description_column: string; amount_column: string; category_column: string; transaction_type_column: string; source: string; sign_convention: string; account_id?: number }) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/import/csv', formData, {
    params: options,
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(res => res.data);
};

export const exportCSV = () => api.get('/export/csv', { responseType: 'blob' }).then(res => {
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `transactions_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  link.remove();
});

export const exportReport = () => api.get('/export/report', { responseType: 'blob' }).then(res => {
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `report_${new Date().toISOString().split('T')[0]}.txt`);
  document.body.appendChild(link);
  link.click();
  link.remove();
});
