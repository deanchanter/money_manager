import { useState, useEffect } from 'react';
import { getSavingsGoals, createSavingsGoal, updateSavingsGoal, addFundsToGoal, deleteSavingsGoal } from '../services/api';
import type { SavingsGoal } from '../types';
import Modal from '../components/Modal';
import ProgressBar from '../components/ProgressBar';

export default function SavingsGoals() {
  const [goals, setGoals] = useState<SavingsGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isFundModalOpen, setIsFundModalOpen] = useState(false);
  const [editingGoal, setEditingGoal] = useState<SavingsGoal | null>(null);
  const [fundingGoal, setFundingGoal] = useState<SavingsGoal | null>(null);
  const [fundAmount, setFundAmount] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    target_amount: '',
    current_amount: '0',
    target_date: '',
    icon: '🎯',
    color: '#10B981',
  });

  const icons = ['🎯', '🏠', '🚗', '✈️', '📱', '💻', '🎓', '💍', '🏖️', '🎁', '🏦', '💰'];
  const colors = ['#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#EF4444', '#14B8A6', '#6366F1'];

  useEffect(() => {
    loadGoals();
  }, []);

  const loadGoals = async () => {
    try {
      const data = await getSavingsGoals();
      setGoals(data);
    } catch (error) {
      console.error('Failed to load goals:', error);
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
        target_amount: parseFloat(formData.target_amount),
        current_amount: parseFloat(formData.current_amount),
        target_date: formData.target_date || null,
        icon: formData.icon,
        color: formData.color,
      };

      if (editingGoal) {
        await updateSavingsGoal(editingGoal.id, data);
      } else {
        await createSavingsGoal(data);
      }

      setIsModalOpen(false);
      setEditingGoal(null);
      resetForm();
      loadGoals();
    } catch (error) {
      console.error('Failed to save goal:', error);
    }
  };

  const handleAddFunds = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fundingGoal) return;
    
    try {
      await addFundsToGoal(fundingGoal.id, parseFloat(fundAmount));
      setIsFundModalOpen(false);
      setFundingGoal(null);
      setFundAmount('');
      loadGoals();
    } catch (error) {
      console.error('Failed to add funds:', error);
    }
  };

  const handleEdit = (goal: SavingsGoal) => {
    setEditingGoal(goal);
    setFormData({
      name: goal.name,
      target_amount: goal.target_amount.toString(),
      current_amount: goal.current_amount.toString(),
      target_date: goal.target_date || '',
      icon: goal.icon,
      color: goal.color,
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this savings goal?')) return;
    try {
      await deleteSavingsGoal(id);
      loadGoals();
    } catch (error) {
      console.error('Failed to delete goal:', error);
    }
  };

  const openFundModal = (goal: SavingsGoal) => {
    setFundingGoal(goal);
    setFundAmount('');
    setIsFundModalOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      target_amount: '',
      current_amount: '0',
      target_date: '',
      icon: '🎯',
      color: '#10B981',
    });
  };

  const openNewModal = () => {
    setEditingGoal(null);
    resetForm();
    setIsModalOpen(true);
  };

  const totalTarget = goals.reduce((sum, g) => sum + g.target_amount, 0);
  const totalSaved = goals.reduce((sum, g) => sum + g.current_amount, 0);

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
        <h1 className="text-2xl font-bold text-gray-900">Savings Goals</h1>
        <button
          onClick={openNewModal}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Add Goal
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <p className="text-sm font-medium text-gray-500">Total Goals</p>
          <p className="text-2xl font-bold text-gray-900">{goals.length}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <p className="text-sm font-medium text-gray-500">Total Saved</p>
          <p className="text-2xl font-bold text-green-600">{formatCurrency(totalSaved)}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <p className="text-sm font-medium text-gray-500">Total Target</p>
          <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalTarget)}</p>
        </div>
      </div>

      {goals.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 border text-center">
          <p className="text-gray-500">No savings goals yet. Create one to start saving!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {goals.map(goal => (
            <div 
              key={goal.id} 
              className="bg-white rounded-xl shadow-sm p-6 border"
              style={{ borderTopColor: goal.color, borderTopWidth: '4px' }}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-3xl">{goal.icon}</span>
                  <span className="font-semibold text-lg">{goal.name}</span>
                </div>
              </div>
              
              <div className="mb-4">
                <ProgressBar 
                  percentage={goal.percentage} 
                  color={goal.color}
                  height="h-4"
                />
              </div>
              
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-600">
                  Saved: <span className="font-medium text-green-600">{formatCurrency(goal.current_amount)}</span>
                </span>
                <span className="text-gray-600">
                  Target: <span className="font-medium">{formatCurrency(goal.target_amount)}</span>
                </span>
              </div>
              
              <div className="text-sm text-gray-500 mb-4">
                Remaining: {formatCurrency(goal.remaining)}
                {goal.target_date && (
                  <span className="ml-2">
                    | Due: {new Date(goal.target_date).toLocaleDateString()}
                  </span>
                )}
              </div>
              
              {goal.percentage >= 100 && (
                <div className="text-sm text-green-600 font-medium mb-4">
                  Goal reached!
                </div>
              )}
              
              <div className="flex gap-2">
                <button
                  onClick={() => openFundModal(goal)}
                  className="flex-1 px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  + Add Funds
                </button>
                <button
                  onClick={() => handleEdit(goal)}
                  className="px-3 py-2 text-sm text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(goal.id)}
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
        title={editingGoal ? 'Edit Savings Goal' : 'Add Savings Goal'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Goal Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              placeholder="e.g., Emergency Fund"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Target Amount</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.target_amount}
              onChange={(e) => setFormData({ ...formData, target_amount: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Current Amount</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.current_amount}
              onChange={(e) => setFormData({ ...formData, current_amount: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Target Date (optional)</label>
            <input
              type="date"
              value={formData.target_date}
              onChange={(e) => setFormData({ ...formData, target_date: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Icon</label>
            <div className="flex flex-wrap gap-2">
              {icons.map(icon => (
                <button
                  key={icon}
                  type="button"
                  onClick={() => setFormData({ ...formData, icon })}
                  className={`w-10 h-10 text-xl rounded-lg ${formData.icon === icon ? 'ring-2 ring-blue-500 bg-blue-50' : 'bg-gray-100'}`}
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
              {editingGoal ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal
        isOpen={isFundModalOpen}
        onClose={() => setIsFundModalOpen(false)}
        title={`Add Funds to ${fundingGoal?.name}`}
      >
        <form onSubmit={handleAddFunds} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Amount to Add</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={fundAmount}
              onChange={(e) => setFundAmount(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
            />
          </div>
          {fundingGoal && (
            <p className="text-sm text-gray-500">
              Current: {formatCurrency(fundingGoal.current_amount)} / {formatCurrency(fundingGoal.target_amount)}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsFundModalOpen(false)}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Add Funds
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
