import { useQuery } from '@tanstack/react-query';
import { listRuns, getRun } from '@/api/client';
import type { RunSummary, RunDetail } from '@/api/types';

export function useRuns() {
  return useQuery<RunSummary[]>({
    queryKey: ['runs'],
    queryFn: listRuns,
    refetchInterval: 5000,
  });
}

export function useRun(runId: string | undefined) {
  return useQuery<RunDetail>({
    queryKey: ['runs', runId],
    queryFn: () => getRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.is_active) return 2000;
      return data?.status === 'running' ? 5000 : 30000;
    },
  });
}
