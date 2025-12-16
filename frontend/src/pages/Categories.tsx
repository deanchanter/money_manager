import { useState, useEffect } from 'react';
import { getCategories, createCategory, updateCategory, deleteCategory } from '../services/api';
import type { Category } from '../types';
import Modal from '../components/Modal';

export default function Categories() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    icon: '📁',
    color: '#6B7280',
    is_income: false,
    keywords: '',
  });

  const icons = ['📁', '🛒', '🍽️', '🚗', '💡', '🎬', '🛍️', '🏥', '🏠', '🛡️', '📱', '💳', '🔄', '💰', '🎯', '✈️', '🎓', '💻', '🏦', '🎁'];
  const colors = ['#6B7280', '#10B981', '#F59E0B', '#3B82F6', '#8B5CF6', '#EC4899', '#F97316', '#EF4444', '#6366F1', '#14B8A6', '#A855F7', '#22C55E'];

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const data = await getCategories();
      setCategories(data);
    } catch (error) {
      console.error('Failed to load categories:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingCategory) {
        await updateCategory(editingCategory.id, formData);
      } else {
        await createCategory(formData);
      }
      setIsModalOpen(false);
      setEditingCategory(null);
      resetForm();
      loadCategories();
    } catch (error) {
      console.error('Failed to save category:', error);
      alert('Failed to save category. Name may already exist.');
    }
  };

  const handleEdit = (category: Category) => {
    setEditingCategory(category);
    setFormData({
      name: category.name,
      icon: category.icon,
      color: category.color,
      is_income: category.is_income,
      keywords: category.keywords,
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this category? Transactions using it will become uncategorized.')) return;
    try {
      await deleteCategory(id);
      loadCategories();
    } catch (error) {
      console.error('Failed to delete category:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      icon: '📁',
      color: '#6B7280',
      is_income: false,
      keywords: '',
    });
  };

  const openNewModal = () => {
    setEditingCategory(null);
    resetForm();
    setIsModalOpen(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  const expenseCategories = categories.filter(c => !c.is_income);
  const incomeCategories = categories.filter(c => c.is_income);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
        <button
          onClick={openNewModal}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Add Category
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Expense Categories</h2>
          <div className="space-y-2">
            {expenseCategories.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No expense categories</p>
            ) : (
              expenseCategories.map(category => (
                <div
                  key={category.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className="w-10 h-10 rounded-full flex items-center justify-center text-xl"
                      style={{ backgroundColor: `${category.color}20` }}
                    >
                      {category.icon}
                    </span>
                    <div>
                      <div className="font-medium">{category.name}</div>
                      {category.keywords && (
                        <div className="text-xs text-gray-500 truncate max-w-xs">
                          {category.keywords}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEdit(category)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(category.id)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Income Categories</h2>
          <div className="space-y-2">
            {incomeCategories.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No income categories</p>
            ) : (
              incomeCategories.map(category => (
                <div
                  key={category.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className="w-10 h-10 rounded-full flex items-center justify-center text-xl"
                      style={{ backgroundColor: `${category.color}20` }}
                    >
                      {category.icon}
                    </span>
                    <div>
                      <div className="font-medium">{category.name}</div>
                      {category.keywords && (
                        <div className="text-xs text-gray-500 truncate max-w-xs">
                          {category.keywords}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEdit(category)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(category.id)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingCategory ? 'Edit Category' : 'Add Category'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              required
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
          
          <div>
            <label className="block text-sm font-medium text-gray-700">Keywords (for auto-categorization)</label>
            <input
              type="text"
              value={formData.keywords}
              onChange={(e) => setFormData({ ...formData, keywords: e.target.value })}
              placeholder="e.g., grocery,supermarket,walmart"
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
            />
            <p className="text-xs text-gray-500 mt-1">Comma-separated keywords to match transaction descriptions</p>
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="is_income"
              checked={formData.is_income}
              onChange={(e) => setFormData({ ...formData, is_income: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label htmlFor="is_income" className="ml-2 block text-sm text-gray-700">
              This is an income category
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
              {editingCategory ? 'Update' : 'Add'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
