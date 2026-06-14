// ── Run ──────────────────────────────────────────────────────────

export interface RunSummary {
  run_id: string;
  repo_path: string;
  status: 'running' | 'completed' | 'aborted' | 'failed';
  total_cost: number;
  task_count: number;
  finding_count: number;
  started_at: number | null;
  finished_at: number | null;
}

export interface RunDetail {
  run_id: string;
  repo_path: string;
  status: string;
  started_at: number | null;
  finished_at: number | null;
  total_cost: number;
  tasks_total: number;
  tasks_pending: number;
  tasks_done: number;
  tasks_failed: number;
  tasks_running: number;
  findings_raw: number;
  findings_confirmed: number;
  findings_canonical: number;
  findings_reachable: number;
  is_active: boolean;
}

export interface RunCreateRequest {
  repo: string;
  run_id?: string | null;
  resume?: boolean;
  max_cost_usd?: number | null;
  max_concurrency?: number | null;
  max_recon_tasks?: number | null;
  target_url?: string | null;
  target_creds?: string[];
  scope_notes?: string | null;
  config_path?: string | null;
  allow_api_key?: boolean;
  stream?: boolean;
}

// ── Task ─────────────────────────────────────────────────────────

export interface TaskItem {
  task_id: string;
  run_id: string;
  source: string;
  attack_class: string;
  scope_hint: string;
  target_files: string[];
  rationale: string;
  priority: number;
  status: 'pending' | 'running' | 'done' | 'failed';
}

// ── Finding ──────────────────────────────────────────────────────

export interface FindingItem {
  finding_id: string;
  task_id: string;
  run_id: string;
  file: string;
  line_start: number;
  line_end: number;
  vuln_class: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  description: string;
  evidence: string;
  poc_succeeded: boolean;
  confidence: number | null;
  validation_status: 'confirmed' | 'rejected' | 'needs_more_info' | null;
  validation_json: Record<string, unknown> | null;
  group_id: string | null;
  is_canonical: boolean;
  trace: TraceData | null;
}

export interface TraceData {
  finding_id: string;
  reachable: boolean;
  confidence: number | null;
  rationale: string;
  entry_points?: { kind: string; location: string }[];
  call_chain?: { file: string; line: number; function: string }[];
  blockers?: { kind: string; location: string; description: string }[];
}

// ── Auth ─────────────────────────────────────────────────────────

export interface AuthCheckResponse {
  auth_mode: string;
  api_key_scrubbed: boolean;
  auth_token_scrubbed: boolean;
  claude_cli_path: string | null;
  claude_cli_version: string | null;
  credentials_file: string | null;
  gateway_base_url: string | null;
  gateway_model: string | null;
  ok: boolean;
  error: string | null;
}

// ── Recover / Merge ──────────────────────────────────────────────

export interface RecoverResponse {
  applied: boolean;
  failed_tasks: { task_id: string; attack_class: string; rationale: string }[];
  changed_count: number;
  message: string;
}

export interface MergeResponse {
  applied: boolean;
  pending_tasks: { task_id: string; attack_class: string; priority: number; target_files: string[]; rationale: string }[];
  saved_count: number;
  message: string;
}

// ── Report ───────────────────────────────────────────────────────

export interface ReportData {
  run_id: string;
  target: { repo_path: string };
  summary: { total: number; by_severity: Record<string, number> };
  findings: ReportFinding[];
}

export interface ReportFinding {
  finding_id: string;
  title: string;
  severity: string;
  vuln_class: string;
  cwe?: string;
  file: string;
  line_start: number;
  line_end: number;
  description: string;
  evidence: string;
  trace: {
    entry_points: { kind: string; location: string }[];
    call_chain: { file: string; line: number; function: string }[];
  };
  recommendation: string;
  variants?: string[];
}

// ── WebSocket Events ─────────────────────────────────────────────

export type WsEventType =
  | 'snapshot'
  | 'stage_start'
  | 'stage_end'
  | 'task_update'
  | 'finding'
  | 'cost_update'
  | 'stream_message'
  | 'log'
  | 'run_complete'
  | 'run_error'
  | 'cancel_ack'
  | 'pong';

export interface WsEvent {
  type: WsEventType;
  [key: string]: unknown;
}

export interface WsSnapshot extends WsEvent {
  type: 'snapshot';
  run: { run_id: string; repo_path: string; status: string; started_at: number; finished_at: number | null };
  tasks: { task_id: string; attack_class: string; target_files: string[]; priority: number; status: string }[];
  findings: { finding_id: string; task_id: string; vuln_class: string; severity: string; file: string; validation_status: string | null; is_canonical: boolean }[];
  total_cost: number;
}
