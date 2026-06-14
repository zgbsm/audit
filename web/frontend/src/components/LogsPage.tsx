import { useRuns } from '@/hooks/useRun';

export function LogsPage() {
  const { data: runs } = useRuns();
  const activeRunIds = runs?.filter((r) => r.status === 'running').map((r) => r.run_id) ?? [];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-2xl font-semibold text-slate-100 mb-4">Activity Logs</h1>
      <div className="glass-panel p-4">
        <div className="text-sm text-slate-400 py-8 text-center space-y-2">
          <p>
            {activeRunIds.length > 0
              ? `${activeRunIds.length} pipeline(s) active`
              : 'No active pipelines'}
          </p>
          <p className="text-slate-600">
            Open a <a href="/" className="text-blue-400 hover:underline">run detail page</a> to view
            live AI streams for each pipeline.
          </p>
        </div>
      </div>
    </div>
  );
}
