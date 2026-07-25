import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getTransactions, getCategories, createTransaction, updateTransaction, deleteTransaction, bulkUpdateTransactions, bulkDeleteTransactions } from '../services/api';
import type { Transaction, Category } from '../types';
import Modal from '../components/Modal';

export default function Transactions() {
  const [searchParams] = useSearchParams();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isBulkEditModalOpen, setIsBulkEditModalOpen] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkCategory, setBulkCategory] = useState<string>('');
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const urlMonth = searchParams.get('month');
    if (urlMonth) return urlMonth;
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [filterCategory, setFilterCategory] = useState<string>(() => {
    return searchParams.get('category') || '';
  });
  const [searchText, setSearchText] = useState('');
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    description: '',
    amount: '',
    category_id: '',
    notes: '',
  });

  useEffect(() => {
    loadData();
  }, [selectedMonth, filterCategory]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [year, month] = selectedMonth.split('-').map(Number);
      const startDate = `${year}-${String(month).padStart(2, '0')}-01`;
      const lastDay = new Date(year, month, 0).getDate();
      const endDate = `${year}-${String(month).padStart(2, '0')}-${lastDay}`;
      
      const params: { start_date: string; end_date: string; category_id?: number | string } = {
        start_date: startDate,
        end_date: endDate,
      };
      if (filterCategory === 'uncategorized') {
        params.category_id = 'null';
      } else if (filterCategory) {
        params.category_id = parseInt(filterCategory);
      }
      
      const [txns, cats] = await Promise.all([getTransactions(params), getCategories()]);
      setTransactions(txns);
      setCategories(cats);
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to connect to server. Please check if the backend is running.');
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };
  
  const filteredTransactions = transactions.filter(t => {
    if (!searchText) return true;
    return t.description.toLowerCase().includes(searchText.toLowerCase());
  });

  const hasActiveFilter = filterCategory !== '' || searchText !== '';
  
  const filteredTotal = filteredTransactions.reduce((sum, t) => {
    const isCreditCard = t.source === 'credit_card';
    const isInverted = t.sign_convention === 'inverted';
    
    if (isCreditCard) {
      // Inverted: positive = expense (subtract), Standard: negative = expense (add as-is)
      return sum + (isInverted ? -t.amount : t.amount);
    }
    return sum + t.amount;
  }, 0);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const data: Record<string, unknown> = {
        date: formData.date,
        description: formData.description,
        amount: parseFloat(formData.amount),
        notes: formData.notes || '',
        category_id: formData.category_id ? parseInt(formData.category_id) : null,
      };

      if (editingTransaction) {
        const updated = await updateTransaction(editingTransaction.id, data);
        // Update in-place without reloading
        setTransactions(prev => prev.map(t => t.id === editingTransaction.id ? updated : t));
      } else {
        await createTransaction(data);
        loadData(); // Only reload for new transactions
      }

      setIsModalOpen(false);
      setEditingTransaction(null);
      resetForm();
    } catch (error) {
      console.error('Failed to save transaction:', error);
    }
  };

  const handleEdit = (transaction: Transaction) => {
    setEditingTransaction(transaction);
    setFormData({
      date: transaction.date.split('T')[0],  // Ensure YYYY-MM-DD format
      description: transaction.description,
      amount: transaction.amount.toString(),
      category_id: transaction.category_id?.toString() || '',
      notes: transaction.notes || '',
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this transaction?')) return;
    try {
      await deleteTransaction(id);
      loadData();
    } catch (error) {
      console.error('Failed to delete transaction:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      date: new Date().toISOString().split('T')[0],
      description: '',
      amount: '',
      category_id: '',
      notes: '',
    });
  };

  const openNewModal = () => {
    setEditingTransaction(null);
    resetForm();
    setIsModalOpen(true);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredTransactions.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredTransactions.map(t => t.id)));
    }
  };

  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const openBulkEditModal = () => {
    setBulkCategory('');
    setIsBulkEditModalOpen(true);
  };

  const handleBulkUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedIds.size === 0) return;
    
    try {
      const categoryId = bulkCategory === '' ? undefined : 
                         bulkCategory === 'none' ? null : 
                         parseInt(bulkCategory);
      await bulkUpdateTransactions(Array.from(selectedIds), { category_id: categoryId });
      setIsBulkEditModalOpen(false);
      setSelectedIds(new Set());
      loadData();
    } catch (error) {
      console.error('Failed to bulk update:', error);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedIds.size} transactions?`)) return;
    
    try {
      await bulkDeleteTransactions(Array.from(selectedIds));
      setSelectedIds(new Set());
      loadData();
    } catch (error) {
      console.error('Failed to bulk delete:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <div className="text-red-600 font-medium">{error}</div>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
        <button
          onClick={openNewModal}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Add Transaction
        </button>
      </div>

      <div className="flex flex-wrap gap-4 items-center">
        <input
          type="month"
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(e.target.value)}
          className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
        />
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
        >
          <option value="">All Categories</option>
          <option value="uncategorized">Uncategorized</option>
          {categories.map(cat => (
            <option key={cat.id} value={cat.id}>
              {cat.icon} {cat.name}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search descriptions..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2 flex-1 min-w-[200px]"
        />
        <span className="text-sm text-gray-500">
          {filteredTransactions.length} transactions
          {hasActiveFilter && (
            <span className={`ml-2 font-medium ${filteredTotal >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              (Total: {filteredTotal >= 0 ? '+' : '-'}{formatCurrency(filteredTotal)})
            </span>
          )}
        </span>
      </div>

      {selectedIds.size > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center justify-between">
          <span className="text-sm text-blue-800 font-medium">
            {selectedIds.size} transaction{selectedIds.size !== 1 ? 's' : ''} selected
          </span>
          <div className="flex gap-2">
            <button
              onClick={openBulkEditModal}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Set Category
            </button>
            <button
              onClick={handleBulkDelete}
              className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Delete Selected
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Clear Selection
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={filteredTransactions.length > 0 && selectedIds.size === filteredTransactions.length}
                  onChange={toggleSelectAll}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Account</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredTransactions.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                  No transactions found for this period.
                </td>
              </tr>
            ) : (
              filteredTransactions.map(transaction => {
                // Determine if this is an expense based on source and sign convention
                const isCreditCard = transaction.source === 'credit_card';
                const isInverted = transaction.sign_convention === 'inverted';
                
                let isExpense = false;
                if (isCreditCard) {
                  // Inverted (Amex): positive = expense, Standard (Chase): negative = expense
                  isExpense = isInverted ? transaction.amount > 0 : transaction.amount < 0;
                } else {
                  isExpense = transaction.amount < 0;
                }
                const isIncome = !isExpense && !isCreditCard && transaction.amount > 0;
                
                return (
                <tr key={transaction.id} className={`hover:bg-gray-50 ${selectedIds.has(transaction.id) ? 'bg-blue-50' : ''}`}>
                  <td className="px-4 py-4">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(transaction.id)}
                      onChange={() => toggleSelect(transaction.id)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(transaction.date).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    <div className="flex items-center gap-2">
                      {transaction.description}
                      {isCreditCard && (
                        <span className="text-xs text-gray-400">💳</span>
                      )}
                    </div>
                    {transaction.notes && (
                      <div className="text-xs text-gray-500">{transaction.notes}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {transaction.category ? (
                      <span 
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                        style={{ 
                          backgroundColor: `${transaction.category.color}20`,
                          color: transaction.category.color 
                        }}
                      >
                        {transaction.category.icon} {transaction.category.name}
                      </span>
                    ) : (
                      <span className="text-gray-400">Uncategorized</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {transaction.account ? (
                      <span>{transaction.account.icon} {transaction.account.name}</span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-sm text-right font-medium ${
                    isExpense ? 'text-red-600' : isIncome ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {isExpense ? '-' : isIncome ? '+' : ''}{formatCurrency(transaction.amount)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <button
                      onClick={() => handleEdit(transaction)}
                      className="text-blue-600 hover:text-blue-800 mr-3"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(transaction.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              )})
            )}
          </tbody>
        </table>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingTransaction ? 'Edit Transaction' : 'Add Transaction'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Date</label>
            <input
              type="date"
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Amount (negative for expense)</label>
            <input
              type="number"
              step="0.01"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Category</label>
            <select
              value={formData.category_id}
              onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
            >
              <option value="">Uncategorized</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.icon} {cat.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              rows={2}
            />
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
              {editingTransaction ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isBulkEditModalOpen}
        onClose={() => setIsBulkEditModalOpen(false)}
        title={`Edit ${selectedIds.size} Transaction${selectedIds.size !== 1 ? 's' : ''}`}
      >
        <form onSubmit={handleBulkUpdate} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Set Category</label>
            <select
              value={bulkCategory}
              onChange={(e) => setBulkCategory(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
            >
              <option value="">-- Select Category --</option>
              <option value="none">Uncategorized</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.icon} {cat.name}
                </option>
              ))}
            </select>
          </div>
          <p className="text-sm text-gray-500">
            This will update the category for all {selectedIds.size} selected transaction{selectedIds.size !== 1 ? 's' : ''}.
          </p>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsBulkEditModalOpen(false)}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Update All
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
