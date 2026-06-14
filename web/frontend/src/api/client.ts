import type {
  RunSummary,
  RunDetail,
  RunCreateRequest,
  TaskItem,
  FindingItem,
  AuthCheckResponse,
  RecoverResponse,
  MergeResponse,
  ReportData,
} from './types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Auth ────────────────────────────────────────────────────────

export function authCheck(allowApiKey: boolean = false): Promise<AuthCheckResponse> {
  return request('/auth/check', {
    method: 'POST',
    body: JSON.stringify({ allow_api_key: allowApiKey }),
  });
}

// ── Runs ────────────────────────────────────────────────────────

export function listRuns(): Promise<RunSummary[]> {
  return request('/runs');
}

export function getRun(runId: string): Promise<RunDetail> {
  return request(`/runs/${runId}`);
}

export function startRun(data: RunCreateRequest): Promise<RunSummary> {
  return request('/runs', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function cancelRun(runId: string): Promise<{ status: string; run_id: string }> {
  return request(`/runs/${runId}/cancel`, { method: 'POST' });
}

// ── Tasks ───────────────────────────────────────────────────────

export function listTasks(runId: string): Promise<TaskItem[]> {
  return request(`/runs/${runId}/tasks`);
}

// ── Findings ────────────────────────────────────────────────────

export function listFindings(
  runId: string,
  params?: { validation_status?: string; canonical_only?: boolean }
): Promise<FindingItem[]> {
  const qs = new URLSearchParams();
  if (params?.validation_status) qs.set('validation_status', params.validation_status);
  if (params?.canonical_only) qs.set('canonical_only', 'true');
  const q = qs.toString();
  return request(`/runs/${runId}/findings${q ? `?${q}` : ''}`);
}

// ── Recover / Merge ─────────────────────────────────────────────

export function recoverTasks(runId: string, apply: boolean): Promise<RecoverResponse> {
  return request(`/runs/${runId}/recover`, {
    method: 'POST',
    body: JSON.stringify({ apply }),
  });
}

export function mergeTasks(runId: string, apply: boolean): Promise<MergeResponse> {
  return request(`/runs/${runId}/merge`, {
    method: 'POST',
    body: JSON.stringify({ apply }),
  });
}

// ── Report ──────────────────────────────────────────────────────

export function getReport(runId: string, format: 'json' | 'md' = 'json'): Promise<ReportData | string> {
  return request(`/runs/${runId}/report?format=${format}`);
}

// ── Health ──────────────────────────────────────────────────────

export function health(): Promise<{ status: string; active_runs: string[]; ws_connections: number }> {
  return request('/health');
}
