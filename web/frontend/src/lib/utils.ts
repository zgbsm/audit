export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function formatCost(usd: number): string {
  return `$${usd.toFixed(4)}`;
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60000);
  const secs = Math.round((ms % 60000) / 1000);
  return `${mins}m ${secs}s`;
}

export function timeAgo(ts: number | null): string {
  if (!ts) return '—';
  const diff = Date.now() - ts * 1000;
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

export function statusColor(status: string): string {
  switch (status) {
    case 'running':
    case 'in_progress':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    case 'completed':
    case 'done':
      return 'bg-green-500/20 text-green-400 border-green-500/30';
    case 'failed':
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'aborted':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    case 'pending':
    default:
      return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  }
}

export function severityColor(severity: string): string {
  switch (severity) {
    case 'critical':
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'high':
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    case 'medium':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    case 'low':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    case 'info':
    default:
      return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  }
}

export const STAGES = [
  'recon', 'merge', 'hunt', 'validate', 'gapfill',
  'dedupe', 'trace', 'feedback', 'report',
] as const;
