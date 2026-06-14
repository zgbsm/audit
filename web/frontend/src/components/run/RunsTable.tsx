import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Play, Plus, Folder, ShieldAlert } from 'lucide-react';
import { useRuns } from '@/hooks/useRun';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { CostDisplay } from '@/components/shared/CostDisplay';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { NewRunDialog } from '@/components/run/NewRunDialog';
import { timeAgo } from '@/lib/utils';
import type { RunSummary } from '@/api/types';

export function RunsDashboard() {
  const { data: runs, isLoading, error } = useRuns();
  const [showNew, setShowNew] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner className="h-8 w-8 text-blue-400" />
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        icon={<ShieldAlert className="h-10 w-10" />}
        title="Failed to load runs"
        description={(error as Error).message}
      />
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Runs</h1>
          <p className="text-sm text-slate-400 mt-1">
            Vulnerability discovery pipelines
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowNew(true)}>
          <Plus className="h-4 w-4" />
          New Run
        </button>
      </div>

      {/* Run list */}
      {!runs || runs.length === 0 ? (
        <EmptyState
          icon={<Folder className="h-10 w-10" />}
          title="No runs yet"
          description="Start your first vulnerability discovery pipeline."
        >
          <button className="btn btn-primary mt-4" onClick={() => setShowNew(true)}>
            <Play className="h-4 w-4" />
            Start a Run
          </button>
        </EmptyState>
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <RunRow
              key={run.run_id}
              run={run}
              onClick={() => navigate(`/runs/${run.run_id}`)}
            />
          ))}
        </div>
      )}

      {showNew && (
        <NewRunDialog
          onClose={() => setShowNew(false)}
          onCreated={(runId) => {
            setShowNew(false);
            queryClient.invalidateQueries({ queryKey: ['runs'] });
            navigate(`/runs/${runId}`);
          }}
        />
      )}
    </div>
  );
}

function RunRow({ run, onClick }: { run: RunSummary; onClick: () => void }) {
  return (
    <div
      className="glass-panel glass-panel-hover p-4 flex items-center gap-4"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3 mb-1">
          <span className="font-mono text-sm text-blue-400">{run.run_id}</span>
          <StatusBadge status={run.status} />
        </div>
        <p className="text-sm text-slate-400 truncate">{run.repo_path}</p>
      </div>

      <div className="flex items-center gap-6 text-sm">
        <div className="text-center">
          <div className="text-slate-400">Tasks</div>
          <div className="font-mono text-slate-200 tabular-nums">{run.task_count}</div>
        </div>
        <div className="text-center">
          <div className="text-slate-400">Findings</div>
          <div className="font-mono text-slate-200 tabular-nums">{run.finding_count}</div>
        </div>
        <div className="text-center min-w-[80px]">
          <div className="text-slate-400">Cost</div>
          <CostDisplay usd={run.total_cost} />
        </div>
        <div className="text-center min-w-[80px]">
          <div className="text-slate-400">Started</div>
          <div className="text-xs text-slate-300">{timeAgo(run.started_at)}</div>
        </div>
      </div>
    </div>
  );
}
