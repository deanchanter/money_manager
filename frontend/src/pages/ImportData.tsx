import { useState, useEffect } from 'react';
import { importCSV, getAccounts } from '../services/api';
import type { Account } from '../types';

export default function ImportData() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ imported: number; skipped?: number; errors: string[] } | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [options, setOptions] = useState({
    date_column: 'date',
    description_column: 'description',
    amount_column: 'amount',
    category_column: '',
    transaction_type_column: '',
    source: 'bank',
    sign_convention: 'standard',
    account_id: undefined as number | undefined,
  });

  useEffect(() => {
    getAccounts().then(setAccounts).catch(console.error);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await importCSV(file, options);
      setResult(response);
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const axiosError = error as { response?: { data?: { detail?: string } } };
      setResult({ 
        imported: 0, 
        errors: [axiosError.response?.data?.detail || errorMessage] 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Import Transactions</h1>

      <div className="bg-white rounded-xl shadow-sm p-6 border">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">CSV File</label>
            <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg">
              <div className="space-y-1 text-center">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <div className="flex text-sm text-gray-600">
                  <label className="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500">
                    <span>Upload a CSV file</span>
                    <input
                      type="file"
                      accept=".csv"
                      className="sr-only"
                      onChange={handleFileChange}
                    />
                  </label>
                </div>
                {file && (
                  <p className="text-sm text-gray-500">Selected: {file.name}</p>
                )}
              </div>
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Account Type</label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {[
                { value: 'bank', label: 'Bank Account', icon: '🏦' },
                { value: 'credit_card', label: 'Credit Card', icon: '💳' },
                { value: 'cash', label: 'Cash', icon: '💵' },
                { value: 'investment', label: 'Investment', icon: '📈' },
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setOptions({ ...options, source: opt.value })}
                  className={`p-3 rounded-lg border text-center ${
                    options.source === opt.value
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="text-2xl mb-1">{opt.icon}</div>
                  <div className="text-sm font-medium">{opt.label}</div>
                </button>
              ))}
            </div>
          </div>

          {accounts.length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Link to Account (recommended)</label>
              <select
                value={options.account_id || ''}
                onChange={(e) => setOptions({ ...options, account_id: e.target.value ? Number(e.target.value) : undefined })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              >
                <option value="">-- No account (don't track balance) --</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.icon} {account.name} ({account.account_type})
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">Link transactions to an account to track balances on the dashboard</p>
            </div>
          )}

          {options.source === 'credit_card' && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Credit Card Format</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setOptions({ ...options, sign_convention: 'standard' })}
                  className={`p-3 rounded-lg border text-left ${
                    options.sign_convention === 'standard'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium">Chase Style</div>
                  <div className="text-xs text-gray-500">Negative = expense</div>
                </button>
                <button
                  type="button"
                  onClick={() => setOptions({ ...options, sign_convention: 'inverted' })}
                  className={`p-3 rounded-lg border text-left ${
                    options.sign_convention === 'inverted'
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium">Amex Style</div>
                  <div className="text-xs text-gray-500">Positive = expense</div>
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Date Column Name</label>
              <input
                type="text"
                value={options.date_column}
                onChange={(e) => setOptions({ ...options, date_column: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Description Column Name</label>
              <input
                type="text"
                value={options.description_column}
                onChange={(e) => setOptions({ ...options, description_column: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Amount Column Name</label>
              <input
                type="text"
                value={options.amount_column}
                onChange={(e) => setOptions({ ...options, amount_column: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Category Column (optional)</label>
              <input
                type="text"
                value={options.category_column}
                onChange={(e) => setOptions({ ...options, category_column: e.target.value })}
                placeholder="e.g., category, type"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Transaction Type Column (optional)</label>
              <input
                type="text"
                value={options.transaction_type_column}
                onChange={(e) => setOptions({ ...options, transaction_type_column: e.target.value })}
                placeholder="e.g., Transaction Type (for Capital One)"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 border p-2"
              />
              <p className="text-xs text-gray-500 mt-1">Use if your CSV has a column like "Debit" or "Credit" instead of +/- amounts</p>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-medium text-gray-900 mb-2">CSV Format Tips</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>- Your CSV should have columns for date, description, and amount</li>
              <li>- Use negative amounts for expenses, positive for income</li>
              <li>- Transactions will be auto-categorized based on keywords</li>
              <li>- Column names are case-insensitive</li>
            </ul>
          </div>

          <button
            type="submit"
            disabled={!file || loading}
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {loading ? 'Importing...' : 'Import Transactions'}
          </button>
        </form>

        {result && (
          <div className={`mt-6 p-4 rounded-lg ${result.imported > 0 ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            {result.imported > 0 ? (
              <div className="text-green-800">
                <p className="font-medium">
                  Successfully imported {result.imported} transactions!
                  {result.skipped ? ` (${result.skipped} duplicates skipped)` : ''}
                </p>
              </div>
            ) : (
              <div className="text-red-800">
                <p className="font-medium">Import failed</p>
              </div>
            )}
            {result.errors.length > 0 && (
              <div className="mt-2">
                <p className="text-sm font-medium text-gray-700">Errors:</p>
                <ul className="text-sm text-red-600 mt-1">
                  {result.errors.map((error, i) => (
                    <li key={i}>- {error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6 border">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Sample CSV Format</h2>
        <pre className="bg-gray-50 p-4 rounded-lg text-sm overflow-x-auto">
{`date,description,amount
2024-01-15,Grocery Store,-125.50
2024-01-14,Monthly Salary,3500.00
2024-01-13,Netflix Subscription,-15.99
2024-01-12,Gas Station,-45.00
2024-01-11,Coffee Shop,-5.50`}
        </pre>
      </div>
    </div>
  );
}
