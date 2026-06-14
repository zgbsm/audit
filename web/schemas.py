"""Pydantic models for web API request/response serialization."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Auth ──────────────────────────────────────────────────────────

class AuthCheckRequest(BaseModel):
    allow_api_key: bool = False


class AuthCheckResponse(BaseModel):
    auth_mode: str
    api_key_scrubbed: bool
    auth_token_scrubbed: bool
    claude_cli_path: str | None = None
    claude_cli_version: str | None = None
    credentials_file: str | None = None
    gateway_base_url: str | None = None
    gateway_model: str | None = None
    ok: bool = True
    error: str | None = None


# ── Runs ──────────────────────────────────────────────────────────

class RunCreateRequest(BaseModel):
    repo: str = Field(..., description="Path to target source-code repo")
    run_id: str | None = None
    resume: bool = False
    max_cost_usd: float | None = None
    max_concurrency: int | None = None
    max_recon_tasks: int | None = None
    target_url: str | None = None
    target_creds: list[str] = Field(default_factory=list)
    scope_notes: str | None = None
    config_path: str | None = None
    allow_api_key: bool = False
    stream: bool = True


class RunSummary(BaseModel):
    run_id: str
    repo_path: str
    status: str
    total_cost: float
    task_count: int = 0
    finding_count: int = 0
    started_at: float | None = None
    finished_at: float | None = None


class RunDetail(BaseModel):
    run_id: str
    repo_path: str
    status: str
    started_at: float | None = None
    finished_at: float | None = None
    total_cost: float
    tasks_total: int
    tasks_pending: int
    tasks_done: int
    tasks_failed: int
    tasks_running: int
    findings_raw: int
    findings_confirmed: int
    findings_canonical: int
    findings_reachable: int
    is_active: bool = False


# ── Tasks ─────────────────────────────────────────────────────────

class TaskResponse(BaseModel):
    task_id: str
    run_id: str
    source: str
    attack_class: str
    scope_hint: str
    target_files: list[str]
    rationale: str
    priority: int
    status: str


class RecoverRequest(BaseModel):
    apply: bool = False


class RecoverResponse(BaseModel):
    applied: bool
    failed_tasks: list[dict[str, Any]]
    changed_count: int = 0
    message: str = ""


class MergeRequest(BaseModel):
    apply: bool = False


class MergeResponse(BaseModel):
    applied: bool
    pending_tasks: list[dict[str, Any]]
    saved_count: int = 0
    message: str = ""


# ── Findings ──────────────────────────────────────────────────────

class FindingResponse(BaseModel):
    finding_id: str
    task_id: str
    run_id: str
    file: str
    line_start: int
    line_end: int
    vuln_class: str
    severity: str
    description: str
    evidence: str
    poc_succeeded: bool = False
    confidence: float | None = None
    validation_status: str | None = None
    validation_json: dict[str, Any] | None = None
    group_id: str | None = None
    is_canonical: bool = False
    trace: dict[str, Any] | None = None


# ── Report ────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    run_id: str
    target: dict[str, Any]
    summary: dict[str, Any]
    findings: list[dict[str, Any]]
    format: str = "json"


# ── Common ────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    run_id: str | None = None
