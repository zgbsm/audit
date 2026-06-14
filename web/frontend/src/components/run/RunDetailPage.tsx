import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Play,
  RotateCcw,
  GitMerge,
  Download,
  StopCircle,
  AlertTriangle,
  Shield,
  FileCode,
  DollarSign,
  Clock,
} from 'lucide-react';
import { useRun } from '@/hooks/useRun';
import { useFindings } from '@/hooks/useFindings';
import { cancelRun, recoverTasks, mergeTasks, resumeRun, listTasks } from '@/api/client';
import { useWebSocket } from '@/api/ws';
import { PipelineProgress } from '@/components/run/PipelineProgress';
import { TasksPanel } from '@/components/task/TasksPanel';
import { FindingsPanel } from '@/components/finding/FindingsPanel';
import { StreamViewer } from '@/components/stream/StreamViewer';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { CostDisplay } from '@/components/shared/CostDisplay';
import { EmptyState } from '@/components/shared/EmptyState';
import { Spinner } from '@/components/shared/Spinner';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';
import { formatDuration, timeAgo } from '@/lib/utils';
import { useQueryClient } from '@tanstack/react-query';
import type { WsEvent, TaskItem } from '@/api/types';

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: run, isLoading, error, refetch } = useRun(runId);
  const { data: findings } = useFindings(runId);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [wsStages, setWsStages] = useState<Record<string, { started: boolean; done: boolean; failed: boolean }>>({});
  const [running, setRunning] = useState(false);

  // Load tasks
  useState(() => {
    if (runId) {
      listTasks(runId).then(setTasks).catch(() => {});
    }
  });

  // WebSocket for real-time updates
  useWebSocket({
    runId: runId ?? null,
    onMessage: (event: WsEvent) => {
      if (event.type === 'stage_start') {
        setWsStages((prev) => ({
          ...prev,
          [event.stage as string]: { started: true, done: false, failed: false },
        }));
      } else if (event.type === 'stage_end') {
        setWsStages((prev) => ({
          ...prev,
          [event.stage as string]: { started: true, done: true, failed: false },
        }));
      } else if (event.type === 'task_update') {
        setTasks((prev) =>
          prev.map((t) =>
            t.task_id === event.task_id ? { ...t, status: event.status as TaskItem['status'] } : t
          )
        );
        // Refetch run metrics periodically
        if (event.status === 'done' || event.status === 'failed') {
          refetch();
          queryClient.invalidateQueries({ queryKey: ['findings', runId] });
        }
      } else if (event.type === 'run_complete') {
        setRunning(false);
        refetch();
        queryClient.invalidateQueries({ queryKey: ['findings', runId] });
      } else if (event.type === 'snapshot') {
        const snap = event as unknown as {
          tasks: TaskItem[];
        };
        if (snap.tasks) setTasks(snap.tasks);
      }
    },
  });

  const handleCancel = async () => {
    if (runId && confirm('Cancel this run?')) {
      await cancelRun(runId);
      refetch();
    }
  };

  const handleRecover = async () => {
    if (runId) {
      const res = await recoverTasks(runId, true);
      alert(res.message);
      refetch();
    }
  };

  const handleMerge = async () => {
    if (runId) {
      const res = await mergeTasks(runId, true);
      alert(res.message);
      refetch();
    }
  };

  const handleResume = async () => {
    if (runId && confirm('Resume this run? Failed tasks will be auto-recovered.')) {
      try {
        await resumeRun(runId);
        setRunning(true);
        refetch();
      } catch (e) {
        alert(`Resume failed: ${(e as Error).message}`);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner className="h-8 w-8 text-blue-400" />
      </div>
    );
  }

  if (error || !run) {
    return (
      <EmptyState
        icon={<AlertTriangle className="h-10 w-10" />}
        title="Run not found"
        description={(error as Error)?.message || `Run "${runId}" does not exist.`}
      >
        <Link to="/" className="btn btn-secondary mt-4">
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
      </EmptyState>
    );
  }

  const isActive = run.status === 'running' || run.is_active;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/" className="btn btn-ghost p-1">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-blue-500" />
              <h1 className="text-xl font-semibold text-slate-100 font-mono">{run.run_id}</h1>
              <StatusBadge status={run.status} />
            </div>
            <p className="text-sm text-slate-500 mt-0.5">{run.repo_path}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isActive && (
            <button className="btn btn-danger" onClick={handleCancel}>
              <StopCircle className="h-4 w-4" />
              Cancel
            </button>
          )}
          {!isActive && (
            <button className="btn btn-primary" onClick={handleResume}>
              <Play className="h-4 w-4" />
              Resume
            </button>
          )}
          <button className="btn btn-secondary" onClick={handleRecover} disabled={isActive}>
            <RotateCcw className="h-4 w-4" />
            Recover
          </button>
          <button className="btn btn-secondary" onClick={handleMerge} disabled={isActive}>
            <GitMerge className="h-4 w-4" />
            Merge
          </button>
          {run.status === 'completed' && (
            <Link to={`/runs/${runId}/report`} className="btn btn-primary">
              <Download className="h-4 w-4" />
              Report
            </Link>
          )}
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-4 gap-3">
        <MetricCard
          icon={<DollarSign className="h-4 w-4 text-green-400" />}
          label="Total Cost"
          value={<CostDisplay usd={run.total_cost} />}
        />
        <MetricCard
          icon={<FileCode className="h-4 w-4 text-blue-400" />}
          label="Tasks"
          value={`${run.tasks_done}/${run.tasks_total}`}
          sub={`${run.tasks_pending} pending · ${run.tasks_failed} failed`}
        />
        <MetricCard
          icon={<Shield className="h-4 w-4 text-yellow-400" />}
          label="Findings"
          value={`${run.findings_confirmed}`}
          sub={`${run.findings_raw} raw · ${run.findings_reachable} reachable`}
        />
        <MetricCard
          icon={<Clock className="h-4 w-4 text-purple-400" />}
          label="Duration"
          value={run.started_at ? timeAgo(run.started_at) : '—'}
        />
      </div>

      {/* Pipeline progress */}
      <ErrorBoundary>
        <PipelineProgress stages={wsStages} />
      </ErrorBoundary>

      {/* Stream viewer (only for active runs) */}
      {isActive && (
        <ErrorBoundary>
          <StreamViewer runId={runId!} />
        </ErrorBoundary>
      )}

      {/* Tasks */}
      <ErrorBoundary>
        <TasksPanel tasks={tasks} />
      </ErrorBoundary>

      {/* Findings */}
      <ErrorBoundary>
        <FindingsPanel findings={findings || []} />
      </ErrorBoundary>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="glass-panel p-3">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <div className="text-lg font-semibold text-slate-100">{value}</div>
      {sub && <div className="text-xs text-slate-600 mt-0.5">{sub}</div>}
    </div>
  );
}
