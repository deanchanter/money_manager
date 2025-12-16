import { useState, useEffect } from 'react';
import { getAccounts, createAccount, updateAccount, deleteAccount } from '../services/api';
import type { Account } from '../types';
import Modal from '../components/Modal';

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    account_type: 'checking',
    starting_balance: '0',
    starting_date: '',
    icon: '🏦',
    color: '#3B82F6',
  });

  const accountTypes = [
    { value: 'checking', label: 'Checking', icon: '🏦' },
    { value: 'savings', label: 'Savings', icon: '💰' },
    { value: 'credit_card', label: 'Credit Card', icon: '💳' },
    { value: 'investment', label: 'Investment', icon: '📈' },
    { value: 'cash', label: 'Cash', icon: '💵' },
  ];

  const icons = ['🏦', '💰', '💳', '📈', '💵', '🏠', '🚗', '💎', '🎯', '🔒'];
  const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6366F1', '#14B8A6'];

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const data = await getAccounts();
      setAccounts(data);
    } catch (error) {
      console.error('Failed to load accounts:', error);
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
        name: formData.name,
        account_type: formData.account_type,
        starting_balance: parseFloat(formData.starting_balance),
        starting_date: formData.starting_date || null,
        icon: formData.icon,
        color: formData.color,
      };

      if (editingAccount) {
        await updateAccount(editingAccount.id, data);
      } else {
        await createAccount(data);
      }

      setIsModalOpen(false);
      setEditingAccount(null);
      resetForm();
      loadAccounts();
    } catch (error) {
      console.error('Failed to save account:', error);
      alert('Failed to save account. Name may already exist.');
    }
  };

  const handleEdit = (account: Account) => {
    setEditingAccount(account);
    setFormData({
      name: account.name,
      account_type: account.account_type,
      starting_balance: account.starting_balance.toString(),
      starting_date: account.starting_date || '',
      icon: account.icon,
      color: account.color,
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this account?')) return;
    try {
      await deleteAccount(id);
      loadAccounts();
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } };
      alert(axiosError.response?.data?.detail || 'Failed to delete account');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      account_type: 'checking',
      starting_balance: '0',
      starting_date: '',
      icon: '🏦',
      color: '#3B82F6',
    });
  };

  const openNewModal = () => {
    setEditingAccount(null);
    resetForm();
    setIsModalOpen(true);
  };

  const totalAssets = accounts
    .filter(a => a.account_type !== 'credit_card')
    .reduce((sum, a) => sum + a.current_balance, 0);
  
  const totalLiabilities = accounts
    .filter(a => a.account_type === 'credit_card')
    .reduce((sum, a) => sum + a.current_balance, 0);

  const netWorth = totalAssets - totalLiabilities;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Accounts</h1>
        <button
          onClick={openNewModal}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Add Account
        </button>
      </div>

      <div className="bg-gradient-to-r from-blue-600 to-blue-800 rounded-xl shadow-lg p-6 text-white">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-blue-100 text-sm font-medium">Total Assets</p>
            <p className="text-2xl font-bold">{formatCurrency(totalAssets)}</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm font-medium">Total Liabilities</p>
            <p className="text-2xl font-bold">{formatCurrency(totalLiabilities)}</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm font-medium">Net Worth</p>
            <p className={`text-2xl font-bold ${netWorth < 0 ? 'text-red-300' : ''}`}>
              {formatCurrency(netWorth)}
            </p>
          </div>
        </div>
      </div>

      {accounts.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 border text-center">
          <p className="text-gray-500">No accounts yet. Add one to start tracking your balances!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map(account => (
            <div
              key={account.id}
              className="bg-white rounded-xl shadow-sm p-6 border"
              style={{ borderTopColor: account.color, borderTopWidth: '4px' }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{account.icon}</span>
                  <div>
                    <h3 className="font-semibold">{account.name}</h3>
                    <p className="text-xs text-gray-500 capitalize">{account.account_type.replace('_', ' ')}</p>
                  </div>
                </div>
              </div>
              
              <div className={`text-2xl font-bold ${
                account.account_type === 'credit_card' 
                  ? (account.current_balance > 0 ? 'text-red-600' : 'text-green-600')
                  : (account.current_balance >= 0 ? 'text-gray-900' : 'text-red-600')
              }`}>
                {formatCurrency(account.current_balance)}
              </div>
              
              <p className="text-xs text-gray-500 mt-1">
                Starting: {formatCurrency(account.starting_balance)}
                {account.starting_date && ` (as of ${new Date(account.starting_date).toLocaleDateString()})`}
              </p>
              
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => handleEdit(account)}
                  className="flex-1 px-3 py-2 text-sm text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(account.id)}
                  className="px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg hover:bg-red-100"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingAccount ? 'Edit Account' : 'Add Account'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Account Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Chase Checking"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Account Type</label>
            <select
              value={formData.account_type}
              onChange={(e) => {
                const type = accountTypes.find(t => t.value === e.target.value);
                setFormData({ 
                  ...formData, 
                  account_type: e.target.value,
                  icon: type?.icon || formData.icon
                });
              }}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
            >
              {accountTypes.map(type => (
                <option key={type.value} value={type.value}>
                  {type.icon} {type.label}
                </option>
              ))}
            </select>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Starting Balance</label>
              <input
                type="number"
                step="0.01"
                value={formData.starting_balance}
                onChange={(e) => setFormData({ ...formData, starting_balance: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">As of Date</label>
              <input
                type="date"
                value={formData.starting_date}
                onChange={(e) => setFormData({ ...formData, starting_date: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              />
            </div>
          </div>
          <p className="text-xs text-gray-500">
            {formData.account_type === 'credit_card' 
              ? 'Enter balance owed (positive = debt). Only transactions after this date will be counted.' 
              : 'Enter your account balance on this date. Only transactions after this date will be counted.'}
          </p>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Icon</label>
            <div className="flex flex-wrap gap-2">
              {icons.map(icon => (
                <button
                  key={icon}
                  type="button"
                  onClick={() => setFormData({ ...formData, icon })}
                  className={`w-10 h-10 text-xl rounded-lg ${formData.icon === icon ? 'ring-2 ring-blue-500 bg-blue-50' : 'bg-gray-100 hover:bg-gray-200'}`}
                >
                  {icon}
                </button>
              ))}
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Color</label>
            <div className="flex flex-wrap gap-2">
              {colors.map(color => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setFormData({ ...formData, color })}
                  className={`w-8 h-8 rounded-full ${formData.color === color ? 'ring-2 ring-offset-2 ring-gray-400' : ''}`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
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
              {editingAccount ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
