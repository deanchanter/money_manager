import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getBudgets, getCategories, createBudget, updateBudget, deleteBudget, getBudgetSuggestions, autoCreateBudgets, rolloverBudgets, adjustBudgets, getTransactions } from '../services/api';
import type { Budget, Category, BudgetSuggestion } from '../types';
import Modal from '../components/Modal';
import ProgressBar from '../components/ProgressBar';

export default function Budgets() {
  const navigate = useNavigate();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentMonth, setCurrentMonth] = useState(new Date().toISOString().slice(0, 7));
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [formData, setFormData] = useState({
    category_id: '',
    amount: '',
    alert_threshold: '0.8',
    is_recurring: true,
    auto_adjust: true,
  });
  const [suggestions, setSuggestions] = useState<BudgetSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [monthlyIncome, setMonthlyIncome] = useState(0);
  const [calculatedIncome, setCalculatedIncome] = useState(0);
  const [editingIncome, setEditingIncome] = useState(false);

  useEffect(() => {
    loadData();
  }, [currentMonth]);

  const loadData = async () => {
    try {
      const [year, month] = currentMonth.split('-').map(Number);
      const startDate = `${year}-${String(month).padStart(2, '0')}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const endDate = `${year}-${String(month).padStart(2, '0')}-${lastDay}`;
      
      const [budgetData, categoryData, transactions] = await Promise.all([
        getBudgets(currentMonth),
        getCategories(),
        getTransactions({ start_date: startDate, end_date: endDate })
      ]);
      setBudgets(budgetData);
      setCategories(categoryData.filter(c => !c.name.toLowerCase().includes('transfer') && !c.name.toLowerCase().includes('payment')));
      
      // Calculate monthly income (positive amounts, excluding transfers)
      const income = transactions
        .filter(t => t.amount > 0 && !t.description.toLowerCase().includes('transfer') && !t.description.toLowerCase().includes('payment'))
        .reduce((sum, t) => sum + t.amount, 0);
      setCalculatedIncome(income);
      
      // Check for user-set income override
      const savedIncome = localStorage.getItem(`income_${currentMonth}`);
      if (savedIncome) {
        setMonthlyIncome(parseFloat(savedIncome));
      } else {
        setMonthlyIncome(income);
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data = {
        category_id: parseInt(formData.category_id),
        amount: parseFloat(formData.amount),
        month: currentMonth,
        alert_threshold: parseFloat(formData.alert_threshold),
        is_recurring: formData.is_recurring,
        auto_adjust: formData.auto_adjust,
      };

      if (editingBudget) {
        await updateBudget(editingBudget.id, data);
      } else {
        await createBudget(data);
      }

      setIsModalOpen(false);
      setEditingBudget(null);
      resetForm();
      loadData();
    } catch (error) {
      console.error('Failed to save budget:', error);
      alert('Failed to save budget. This category may already have a budget for this month.');
    }
  };

  const handleEdit = (budget: Budget) => {
    setEditingBudget(budget);
    setFormData({
      category_id: budget.category_id.toString(),
      amount: budget.amount.toString(),
      alert_threshold: budget.alert_threshold.toString(),
      is_recurring: budget.is_recurring,
      auto_adjust: budget.auto_adjust,
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this budget?')) return;
    try {
      await deleteBudget(id);
      loadData();
    } catch (error) {
      console.error('Failed to delete budget:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      category_id: '',
      amount: '',
      alert_threshold: '0.8',
      is_recurring: true,
      auto_adjust: true,
    });
  };

  const loadSuggestions = async () => {
    try {
      const data = await getBudgetSuggestions(3);
      setSuggestions(data);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const handleAutoCreate = async () => {
    if (!confirm('This will create budgets for all categories with spending history for the current month. Continue?')) return;
    try {
      const result = await autoCreateBudgets(currentMonth, false);
      alert(`Created ${result.created} budgets`);
      loadData();
    } catch (error) {
      console.error('Failed to auto-create budgets:', error);
    }
  };

  const handleRollover = async () => {
    try {
      const result = await rolloverBudgets(undefined, currentMonth);
      alert(`Rolled over ${result.rolled_over} budgets`);
      loadData();
    } catch (error) {
      console.error('Failed to rollover budgets:', error);
    }
  };

  const handleAdjust = async () => {
    if (!confirm('This will adjust budgets based on recent spending trends. Continue?')) return;
    try {
      const result = await adjustBudgets(currentMonth);
      alert(`Adjusted ${result.adjusted} budgets`);
      loadData();
    } catch (error) {
      console.error('Failed to adjust budgets:', error);
    }
  };

  const createFromSuggestion = (suggestion: BudgetSuggestion) => {
    setFormData({
      category_id: suggestion.category_id.toString(),
      amount: suggestion.suggested_amount.toString(),
      alert_threshold: '0.8',
      is_recurring: true,
      auto_adjust: true,
    });
    setShowSuggestions(false);
    setIsModalOpen(true);
  };

  const openNewModal = () => {
    setEditingBudget(null);
    resetForm();
    setIsModalOpen(true);
  };

  const usedCategoryIds = budgets.map(b => b.category_id);
  const availableCategories = editingBudget 
    ? categories 
    : categories.filter(c => !usedCategoryIds.includes(c.id));

  const totalBudget = budgets.reduce((sum, b) => sum + b.amount, 0);
  const totalSpent = budgets.reduce((sum, b) => sum + b.spent, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Budgets</h1>
            <p className="text-sm text-gray-500">
              Income: <span className="text-green-600 font-medium">{formatCurrency(monthlyIncome)}</span>
              {' | '}Budgeted: <span className="font-medium">{formatCurrency(totalBudget)}</span>
              {' | '}Spent: <span className={`font-medium ${totalSpent > monthlyIncome ? 'text-red-600' : ''}`}>{formatCurrency(totalSpent)}</span>
            </p>
          </div>
          <input
            type="month"
            value={currentMonth}
            onChange={(e) => setCurrentMonth(e.target.value)}
            className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={loadSuggestions}
            className="px-3 py-2 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 text-sm"
          >
            Suggestions
          </button>
          <button
            onClick={handleAutoCreate}
            className="px-3 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 text-sm"
          >
            Auto Create
          </button>
          <button
            onClick={handleRollover}
            className="px-3 py-2 bg-yellow-100 text-yellow-700 rounded-lg hover:bg-yellow-200 text-sm"
          >
            Rollover
          </button>
          <button
            onClick={handleAdjust}
            className="px-3 py-2 bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 text-sm"
          >
            Adjust
          </button>
          <button
            onClick={openNewModal}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            disabled={availableCategories.length === 0}
          >
            + Add Budget
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <p className="text-sm font-medium text-gray-500">Monthly Income</p>
          {editingIncome ? (
            <input
              type="number"
              defaultValue={monthlyIncome}
              onBlur={(e) => {
                const value = parseFloat(e.target.value) || 0;
                setMonthlyIncome(value);
                localStorage.setItem(`income_${currentMonth}`, value.toString());
                setEditingIncome(false);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const value = parseFloat((e.target as HTMLInputElement).value) || 0;
                  setMonthlyIncome(value);
                  localStorage.setItem(`income_${currentMonth}`, value.toString());
                  setEditingIncome(false);
                }
              }}
              className="text-2xl font-bold text-green-600 w-full border-b-2 border-green-500 outline-none"
              autoFocus
            />
          ) : (
            <p 
              className="text-2xl font-bold text-green-600 cursor-pointer hover:underline"
              onClick={() => setEditingIncome(true)}
              title="Click to edit"
            >
              {formatCurrency(monthlyIncome)}
            </p>
          )}
          {calculatedIncome !== monthlyIncome && (
            <p className="text-xs text-gray-400 mt-1">
              Calculated: {formatCurrency(calculatedIncome)}
              <button 
                onClick={() => {
                  setMonthlyIncome(calculatedIncome);
                  localStorage.removeItem(`income_${currentMonth}`);
                }}
                className="ml-2 text-blue-500 hover:underline"
              >
                Reset
              </button>
            </p>
          )}
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <p className="text-sm font-medium text-gray-500">Total Budget</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalBudget)}</p>
          <p className="text-xs text-gray-500 mt-1">
            {monthlyIncome > 0 ? `${Math.round(totalBudget / monthlyIncome * 100)}% of income` : ''}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <p className="text-sm font-medium text-gray-500">Total Spent</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalSpent)}</p>
          <p className="text-xs text-gray-500 mt-1">
            {monthlyIncome > 0 ? `${Math.round(totalSpent / monthlyIncome * 100)}% of income` : ''}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <p className="text-sm font-medium text-gray-500">Net (Income - Spent)</p>
          <p className={`text-2xl font-bold ${monthlyIncome - totalSpent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(monthlyIncome - totalSpent)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Total Budget Card */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-green-300 bg-green-50">
          <div className="flex items-center justify-between mb-4">
            <div 
              className="flex items-center gap-2 cursor-pointer hover:opacity-70"
              onClick={() => navigate(`/transactions?month=${currentMonth}`)}
              title="View all transactions"
            >
              <span className="text-2xl">💰</span>
              <span className="font-semibold text-lg hover:underline">Total Budget</span>
            </div>
          </div>
          
          <div className="mb-4">
            <ProgressBar 
              percentage={monthlyIncome > 0 ? Math.min((totalSpent / monthlyIncome) * 100, 100) : 0} 
              color="#10B981"
              height="h-3"
            />
          </div>
          
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">
              Spent: <span className="font-medium">{formatCurrency(totalSpent)}</span>
            </span>
            <span className="text-gray-600">
              Income: <span className="font-medium text-green-600">{formatCurrency(monthlyIncome)}</span>
            </span>
          </div>
          
          <div className="mt-2 text-sm">
            <span className={monthlyIncome - totalSpent >= 0 ? 'text-green-600' : 'text-red-600'}>
              {monthlyIncome - totalSpent >= 0 ? 'Remaining' : 'Over'}: {formatCurrency(Math.abs(monthlyIncome - totalSpent))}
            </span>
            <span className="text-gray-500 ml-2">
              ({monthlyIncome > 0 ? Math.round((totalSpent / monthlyIncome) * 100) : 0}% of income)
            </span>
          </div>
        </div>

        {budgets.map(budget => {
            const isIncome = budget.is_income;
            const metGoal = isIncome && budget.spent >= budget.amount;
            return (
            <div 
              key={budget.id} 
              className={`bg-white rounded-xl shadow-sm p-6 border ${
                isIncome 
                  ? metGoal ? 'border-green-300 bg-green-50' : ''
                  : budget.is_over_budget ? 'border-red-300 bg-red-50' : budget.is_alert ? 'border-yellow-300 bg-yellow-50' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-4">
                <div 
                  className="flex items-center gap-2 cursor-pointer hover:opacity-70"
                  onClick={() => navigate(`/transactions?month=${currentMonth}&category=${budget.category_id}`)}
                  title="View transactions"
                >
                  <span className="text-2xl">{budget.category?.icon}</span>
                  <span className="font-semibold text-lg hover:underline">{budget.category?.name}</span>
                  {isIncome && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Income</span>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleEdit(budget)}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(budget.id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Delete
                  </button>
                </div>
              </div>
              
              <div className="mb-4">
                <ProgressBar 
                  percentage={budget.percentage} 
                  color={isIncome ? '#22C55E' : budget.category?.color}
                  height="h-3"
                />
              </div>
              
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">
                  {isIncome ? 'Earned' : 'Spent'}: <span className="font-medium">{formatCurrency(budget.spent)}</span>
                </span>
                <span className="text-gray-600">
                  {isIncome ? 'Goal' : 'Budget'}: <span className="font-medium">{formatCurrency(budget.amount)}</span>
                </span>
              </div>
              
              <div className="mt-2 text-sm">
                {isIncome ? (
                  <span className={metGoal ? 'text-green-600' : 'text-gray-600'}>
                    {metGoal ? 'Goal met!' : `${formatCurrency(budget.remaining)} to go`}
                  </span>
                ) : (
                  <span className={budget.remaining >= 0 ? 'text-green-600' : 'text-red-600'}>
                    {budget.remaining >= 0 ? 'Remaining' : 'Over'}: {formatCurrency(Math.abs(budget.remaining))}
                  </span>
                )}
              </div>
              
              {!isIncome && budget.is_over_budget && (
                <div className="mt-3 text-sm text-red-600 font-medium">
                  Over budget by {formatCurrency(Math.abs(budget.remaining))}
                </div>
              )}
              {!isIncome && budget.is_alert && !budget.is_over_budget && (
                <div className="mt-3 text-sm text-yellow-600 font-medium">
                  Warning: Approaching budget limit
                </div>
              )}
            </div>
          )})}
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingBudget ? 'Edit Budget' : 'Add Budget'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Category</label>
            <select
              value={formData.category_id}
              onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
              disabled={!!editingBudget}
            >
              <option value="">Select category</option>
              {availableCategories.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.icon} {cat.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Monthly Budget Amount</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Alert Threshold (%)</label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={formData.alert_threshold}
              onChange={(e) => setFormData({ ...formData, alert_threshold: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
            />
            <p className="text-xs text-gray-500 mt-1">Alert when spending reaches this percentage (0.8 = 80%)</p>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_recurring}
                onChange={(e) => setFormData({ ...formData, is_recurring: e.target.checked })}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">Recurring (rollover monthly)</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.auto_adjust}
                onChange={(e) => setFormData({ ...formData, auto_adjust: e.target.checked })}
                className="rounded border-gray-300"
              />
              <span className="text-sm text-gray-700">Auto-adjust to trends</span>
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              {editingBudget ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={showSuggestions}
        onClose={() => setShowSuggestions(false)}
        title="Budget Suggestions"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Based on your spending over the past 3 months, here are suggested budgets:
          </p>
          {suggestions.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No spending history found to generate suggestions.</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {suggestions.filter(s => !usedCategoryIds.includes(s.category_id)).map(suggestion => (
                <div key={suggestion.category_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{suggestion.category_icon}</span>
                    <div>
                      <p className="font-medium">{suggestion.category_name}</p>
                      <p className="text-xs text-gray-500">
                        Avg: {formatCurrency(suggestion.average_spending)} | 
                        Range: {formatCurrency(suggestion.min_spending)} - {formatCurrency(suggestion.max_spending)}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-green-600">{formatCurrency(suggestion.suggested_amount)}</p>
                    <button
                      onClick={() => createFromSuggestion(suggestion)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Use this
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="flex justify-end">
            <button
              onClick={() => setShowSuggestions(false)}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
