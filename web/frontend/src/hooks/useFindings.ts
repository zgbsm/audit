import { useQuery } from '@tanstack/react-query';
import { listFindings } from '@/api/client';
import type { FindingItem } from '@/api/types';

export function useFindings(
  runId: string | undefined,
  params?: { validation_status?: string; canonical_only?: boolean }
) {
  return useQuery<FindingItem[]>({
    queryKey: ['findings', runId, params],
    queryFn: () => listFindings(runId!, params),
    enabled: !!runId,
    refetchInterval: 10000,
  });
}
