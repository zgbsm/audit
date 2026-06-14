import { useState } from 'react';
import { X } from 'lucide-react';
import { startRun } from '@/api/client';
import type { RunCreateRequest } from '@/api/types';

interface Props {
  onClose: () => void;
  onCreated: (runId: string) => void;
}

export function NewRunDialog({ onClose, onCreated }: Props) {
  const [form, setForm] = useState<RunCreateRequest>({
    repo: '',
    run_id: null,
    max_cost_usd: null,
    max_concurrency: null,
    max_recon_tasks: null,
    target_url: null,
    target_creds: [],
    scope_notes: null,
    resume: false,
  });
  const [credInput, setCredInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!form.repo) {
      setError('Repo path is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const creds = credInput
        .split('\n')
        .map((l) => l.trim())
        .filter((l) => l.includes('='));
      const result = await startRun({ ...form, target_creds: creds });
      onCreated(result.run_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-lg max-h-[90vh] overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100">New Audit Run</h2>
          <button className="btn btn-ghost p-1" onClick={onClose}>
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Required: repo path */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-1">
            Repo Path <span className="text-red-400">*</span>
          </label>
          <input
            className="input-field"
            placeholder="/path/to/target/repo"
            value={form.repo}
            onChange={(e) => setForm({ ...form, repo: e.target.value })}
          />
        </div>

        {/* Optional: run ID */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-1">Run ID (optional)</label>
          <input
            className="input-field"
            placeholder="auto-generated if empty"
            value={form.run_id ?? ''}
            onChange={(e) => setForm({ ...form, run_id: e.target.value || null })}
          />
        </div>

        {/* Cost & concurrency controls */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Max Cost (USD)</label>
            <input
              className="input-field"
              type="number"
              placeholder="No limit"
              value={form.max_cost_usd ?? ''}
              onChange={(e) =>
                setForm({ ...form, max_cost_usd: e.target.value ? Number(e.target.value) : null })
              }
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Max Concurrency</label>
            <input
              className="input-field"
              type="number"
              placeholder="Default"
              value={form.max_concurrency ?? ''}
              onChange={(e) =>
                setForm({
                  ...form,
                  max_concurrency: e.target.value ? Number(e.target.value) : null,
                })
              }
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-1">Max Recon Tasks</label>
          <input
            className="input-field"
            type="number"
            placeholder="Default (80)"
            value={form.max_recon_tasks ?? ''}
            onChange={(e) =>
              setForm({
                ...form,
                max_recon_tasks: e.target.value ? Number(e.target.value) : null,
              })
            }
          />
        </div>

        {/* Live target */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-1">Target URL (live deployment)</label>
          <input
            className="input-field"
            placeholder="http://server.local:8888"
            value={form.target_url ?? ''}
            onChange={(e) => setForm({ ...form, target_url: e.target.value || null })}
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-1">
            Target Credentials (KEY=VALUE, one per line)
          </label>
          <textarea
            className="input-field min-h-[60px]"
            placeholder="email=admin@x.com\npassword=changeme"
            value={credInput}
            onChange={(e) => setCredInput(e.target.value)}
          />
        </div>

        {/* Scope notes */}
        <div className="mb-4">
          <label className="block text-sm text-slate-400 mb-1">Scope Notes</label>
          <textarea
            className="input-field min-h-[60px]"
            placeholder="Any exclusions or special instructions"
            value={form.scope_notes ?? ''}
            onChange={(e) => setForm({ ...form, scope_notes: e.target.value || null })}
          />
        </div>

        {/* Resume toggle */}
        <label className="flex items-center gap-2 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={form.resume ?? false}
            onChange={(e) => setForm({ ...form, resume: e.target.checked })}
            className="rounded border-slate-600 bg-slate-800 text-blue-500 focus:ring-blue-500"
          />
          <span className="text-sm text-slate-400">Resume existing run</span>
        </label>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}>
            {loading ? 'Starting...' : 'Start Run'}
          </button>
        </div>
      </div>
    </div>
  );
}
