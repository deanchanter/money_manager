import { useState, useEffect } from 'react';
import {
  getSimpleFinStatus,
  getSimpleFinAccounts,
  getAccounts,
  linkSimpleFinAccount,
  unlinkSimpleFinAccount,
  syncSimpleFin,
} from '../services/api';
import type {
  Account,
  SimpleFinStatus,
  SimpleFinRemoteAccount,
  SimpleFinSyncResult,
} from '../types';

const accountTypes = [
  { value: 'checking', label: 'Checking' },
  { value: 'savings', label: 'Savings' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'investment', label: 'Investment' },
  { value: 'cash', label: 'Cash' },
];

export default function Sync() {
  const [status, setStatus] = useState<SimpleFinStatus | null>(null);
  const [remotes, setRemotes] = useState<SimpleFinRemoteAccount[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [days, setDays] = useState(30);
  const [result, setResult] = useState<SimpleFinSyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Per-remote-account form state: which local account to link to, or a new one
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [newType, setNewType] = useState<Record<string, string>>({});

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const statusData = await getSimpleFinStatus();
      setStatus(statusData);
      setAccounts(await getAccounts());
      if (statusData.connected) {
        const remoteData = await getSimpleFinAccounts();
        setRemotes(remoteData.accounts);
      }
    } catch (err) {
      setError(readError(err));
    } finally {
      setLoading(false);
    }
  };

  const handleLink = async (remote: SimpleFinRemoteAccount) => {
    const selection = choice[remote.simplefin_account_id] ?? '';
    setError(null);
    try {
      if (selection === 'new') {
        await linkSimpleFinAccount({
          simplefin_account_id: remote.simplefin_account_id,
          create_as: newType[remote.simplefin_account_id] || 'credit_card',
          name: remote.name,
        });
      } else if (selection) {
        await linkSimpleFinAccount({
          simplefin_account_id: remote.simplefin_account_id,
          account_id: Number(selection),
        });
      } else {
        return;
      }
      await load();
    } catch (err) {
      setError(readError(err));
    }
  };

  const handleUnlink = async (accountId: number) => {
    setError(null);
    try {
      await unlinkSimpleFinAccount(accountId);
      await load();
    } catch (err) {
      setError(readError(err));
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setResult(null);
    setError(null);
    try {
      setResult(await syncSimpleFin(days));
      await load();
    } catch (err) {
      setError(readError(err));
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return <div className="text-gray-500">Loading…</div>;
  }

  const linkedCount = status?.linked_accounts.length ?? 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Bank Sync</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-4 text-sm">
          {error}
        </div>
      )}

      {/* Connection */}
      <div className="bg-white rounded-xl shadow-sm p-6 border">
        {status?.connected ? (
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
                <span className="font-medium text-gray-900">
                  Connected{status.org_name ? ` to ${status.org_name}` : ''}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-1">{status.endpoint}</p>
              <p className="text-sm text-gray-500">
                Last synced: {formatDate(status.last_synced_at)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="rounded-md border-gray-300 border p-2 text-sm"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={365}>Last year</option>
              </select>
              <button
                onClick={handleSync}
                disabled={syncing || linkedCount === 0}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:bg-gray-300"
              >
                {syncing ? 'Syncing…' : 'Sync now'}
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-gray-300" />
              <span className="font-medium text-gray-900">Not connected</span>
            </div>
            <p className="text-sm text-gray-600 mt-2">
              Add a SimpleFIN setup token to <code className="bg-gray-100 px-1 rounded">.env</code> and run:
            </p>
            <pre className="mt-2 bg-gray-50 border rounded p-3 text-xs overflow-x-auto">
              cd backend &amp;&amp; uv run python scripts/simplefin_setup.py
            </pre>
          </div>
        )}
        {status?.connected && linkedCount === 0 && (
          <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3 mt-4">
            Link at least one account below before syncing.
          </p>
        )}
      </div>

      {/* Sync result */}
      {result && (
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <h2 className="font-medium text-gray-900 mb-3">{result.message}</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
            <Stat label="New" value={result.imported} />
            <Stat label="Updated" value={result.updated} />
            <Stat label="Matched existing" value={result.adopted} />
            <Stat label="Unchanged" value={result.unchanged} />
            <Stat label="Transfers found" value={result.transfers_detected} />
          </div>
          {result.transfers_detected > 0 && (
            <p className="text-sm text-gray-600 mb-3">
              Transfers between your own accounts (card payments, moves to savings) are
              excluded from income and expense totals.
            </p>
          )}
          {result.balances.length > 0 && (
            <div className="text-sm text-gray-600 space-y-1">
              {result.balances.map((b) => (
                <div key={b.account}>
                  <span className="font-medium text-gray-900">{b.account}</span>: balance
                  set to {formatMoney(b.reported_balance)}
                  {b.as_of ? ` (as of ${b.as_of})` : ''}
                </div>
              ))}
            </div>
          )}
          {result.warnings.length > 0 && (
            <ul className="mt-3 text-sm text-amber-700 list-disc list-inside space-y-1">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Account linking */}
      {status?.connected && (
        <div className="bg-white rounded-xl shadow-sm p-6 border">
          <h2 className="font-medium text-gray-900 mb-1">Accounts at your bank</h2>
          <p className="text-sm text-gray-500 mb-4">
            Only linked accounts are synced. Linking to an existing account keeps its
            history and categories.
          </p>

          <div className="space-y-3">
            {remotes.map((remote) => (
              <div
                key={remote.simplefin_account_id}
                className="border rounded-lg p-4 flex flex-col md:flex-row md:items-center gap-3 justify-between"
              >
                <div className="min-w-0">
                  <div className="font-medium text-gray-900 truncate">{remote.name}</div>
                  <div className="text-sm text-gray-500">
                    {formatMoney(Number(remote.balance))} {remote.currency}
                  </div>
                </div>

                {remote.linked_account_id ? (
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-full px-3 py-1">
                      Linked to {remote.linked_account_name}
                    </span>
                    <button
                      onClick={() => handleUnlink(remote.linked_account_id!)}
                      className="text-sm text-gray-500 hover:text-red-600"
                    >
                      Unlink
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <select
                      value={choice[remote.simplefin_account_id] ?? ''}
                      onChange={(e) =>
                        setChoice({ ...choice, [remote.simplefin_account_id]: e.target.value })
                      }
                      className="rounded-md border-gray-300 border p-2 text-sm"
                    >
                      <option value="">-- Link to --</option>
                      {accounts.map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.icon} {account.name}
                        </option>
                      ))}
                      <option value="new">+ Create new account</option>
                    </select>

                    {choice[remote.simplefin_account_id] === 'new' && (
                      <select
                        value={newType[remote.simplefin_account_id] ?? 'credit_card'}
                        onChange={(e) =>
                          setNewType({ ...newType, [remote.simplefin_account_id]: e.target.value })
                        }
                        className="rounded-md border-gray-300 border p-2 text-sm"
                      >
                        {accountTypes.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    )}

                    <button
                      onClick={() => handleLink(remote)}
                      disabled={!choice[remote.simplefin_account_id]}
                      className="px-3 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-700 disabled:bg-gray-300"
                    >
                      Link
                    </button>
                  </div>
                )}
              </div>
            ))}
            {remotes.length === 0 && (
              <p className="text-sm text-gray-500">No accounts returned by SimpleFIN.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="text-2xl font-semibold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

function formatMoney(value: number) {
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : 'never';
}

function readError(err: unknown) {
  const axiosError = err as { response?: { data?: { detail?: string } } };
  if (axiosError.response?.data?.detail) return axiosError.response.data.detail;
  return err instanceof Error ? err.message : 'Something went wrong';
}
