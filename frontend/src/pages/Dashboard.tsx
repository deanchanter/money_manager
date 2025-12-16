import { useState, useEffect } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title } from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import { getDashboardStats, getAccountSummary, exportCSV, exportReport } from '../services/api';
import type { DashboardStats, AccountSummary } from '../types';
import StatCard from '../components/StatCard';
import ProgressBar from '../components/ProgressBar';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title);

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [accountSummary, setAccountSummary] = useState<AccountSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });

  useEffect(() => {
    loadStats();
  }, [selectedMonth]);

  const loadStats = async () => {
    setLoading(true);
    try {
      const [year, month] = selectedMonth.split('-').map(Number);
      const startDate = `${year}-${String(month).padStart(2, '0')}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const endDate = `${year}-${String(month).padStart(2, '0')}-${lastDay}`;
      
      const [monthData, summaryData] = await Promise.all([
        getDashboardStats({ start_date: startDate, end_date: endDate }),
        getAccountSummary()
      ]);
      setStats(monthData);
      setAccountSummary(summaryData);
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Failed to load dashboard data</p>
      </div>
    );
  }

  const categoryChartData = {
    labels: stats.spending_by_category.map(c => c.category_name),
    datasets: [{
      data: stats.spending_by_category.map(c => c.total),
      backgroundColor: stats.spending_by_category.map(c => c.category_color),
      borderWidth: 0,
    }],
  };

  const monthlyChartData = {
    labels: stats.monthly_trend.map(m => m.month),
    datasets: [
      {
        label: 'Income',
        data: stats.monthly_trend.map(m => m.income),
        backgroundColor: '#22C55E',
      },
      {
        label: 'Expenses',
        data: stats.monthly_trend.map(m => m.expenses),
        backgroundColor: '#EF4444',
      },
    ],
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <input
            type="month"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => exportCSV()}
            className="px-4 py-2 text-sm bg-white border rounded-lg hover:bg-gray-50"
          >
            Export CSV
          </button>
          <button
            onClick={() => exportReport()}
            className="px-4 py-2 text-sm bg-white border rounded-lg hover:bg-gray-50"
          >
            Export Report
          </button>
        </div>
      </div>

      {accountSummary && (
        <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl shadow-lg p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-blue-100 text-sm font-medium">Net Worth</p>
              <p className={`text-3xl font-bold mt-1 ${accountSummary.net_worth < 0 ? 'text-red-300' : ''}`}>
                {formatCurrency(accountSummary.net_worth)}
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm text-blue-100">
                <span>Assets: {formatCurrency(accountSummary.total_assets)}</span>
                <span className="mx-2">|</span>
                <span>Liabilities: {formatCurrency(accountSummary.total_liabilities)}</span>
              </div>
            </div>
          </div>
          {accountSummary.accounts.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-4 border-t border-blue-500">
              {accountSummary.accounts.map(account => (
                <div key={account.id} className="bg-blue-700/50 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span>{account.icon}</span>
                    <span className="text-sm truncate">{account.name}</span>
                  </div>
                  <p className={`text-lg font-semibold ${
                    account.account_type === 'credit_card' && account.balance > 0 ? 'text-red-300' : ''
                  }`}>
                    {formatCurrency(account.balance)}
                  </p>
                </div>
              ))}
            </div>
          )}
          {accountSummary.accounts.length === 0 && (
            <p className="text-blue-200 text-sm pt-4 border-t border-blue-500">
              No accounts yet. <a href="/accounts" className="underline">Add accounts</a> to track balances.
            </p>
          )}
        </div>
      )}

      <h2 className="text-lg font-semibold text-gray-700">This Month</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Monthly Income"
          value={formatCurrency(stats.total_income)}
          icon="📈"
          color="green"
        />
        <StatCard
          title="Monthly Expenses"
          value={formatCurrency(stats.total_expenses)}
          icon="📉"
          color="red"
        />
        <StatCard
          title="Monthly Net"
          value={formatCurrency(stats.net_balance)}
          icon={stats.net_balance >= 0 ? '✅' : '⚠️'}
          color={stats.net_balance >= 0 ? 'blue' : 'red'}
        />
      </div>

      {stats.budget_alerts.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h3 className="font-semibold text-yellow-800 mb-2">⚠️ Budget Alerts</h3>
          <div className="space-y-2">
            {stats.budget_alerts.map(budget => (
              <div key={budget.id} className="flex items-center justify-between bg-white rounded p-3">
                <span className="font-medium">
                  {budget.category?.icon} {budget.category?.name}
                </span>
                <span className={budget.is_over_budget ? 'text-red-600 font-bold' : 'text-yellow-600'}>
                  {formatCurrency(budget.spent)} / {formatCurrency(budget.amount)} ({budget.percentage.toFixed(1)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Spending by Category</h2>
          {stats.spending_by_category.length > 0 ? (
            <div className="flex items-center justify-center">
              <div className="w-64 h-64">
                <Doughnut 
                  data={categoryChartData} 
                  options={{
                    plugins: {
                      legend: {
                        position: 'bottom',
                      },
                    },
                  }}
                />
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No spending data yet</p>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Monthly Trend</h2>
          <Bar 
            data={monthlyChartData}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: 'bottom',
                },
              },
              scales: {
                y: {
                  beginAtZero: true,
                },
              },
            }}
          />
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6 border">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Spending Breakdown</h2>
        {stats.spending_by_category.length > 0 ? (
          <div className="space-y-4">
            {stats.spending_by_category.map(cat => (
              <div key={cat.category_id} className="flex items-center gap-4">
                <div className="w-32 font-medium truncate">{cat.category_name}</div>
                <div className="flex-1">
                  <ProgressBar 
                    percentage={cat.percentage} 
                    color={cat.category_color}
                    showLabel={false}
                    height="h-3"
                  />
                </div>
                <div className="w-24 text-right font-medium">{formatCurrency(cat.total)}</div>
                <div className="w-16 text-right text-gray-500">{cat.percentage.toFixed(1)}%</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No spending data yet. Import transactions to get started!</p>
        )}
      </div>
    </div>
  );
}
