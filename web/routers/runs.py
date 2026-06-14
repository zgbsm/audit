"""Runs router — /api/runs CRUD, cancel, recover, merge-tasks."""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from audit.auth import AuthError, configure_auth
from audit.config import load_config
from audit.state import StateDB

from web.run_manager import run_manager
from web.schemas import (
    ErrorResponse,
    MergeRequest,
    MergeResponse,
    RecoverRequest,
    RecoverResponse,
    RunCreateRequest,
    RunDetail,
    RunSummary,
)

router = APIRouter()

DB_PATH = Path(__file__).resolve().parent.parent.parent / "state.db"


def _get_db() -> StateDB:
    return StateDB(DB_PATH)


@router.get("/runs", response_model=list[RunSummary])
async def list_runs():
    """List all runs (equivalent to `audit status` without --run-id)."""
    db = _get_db()
    try:
        runs = db.list_runs()
        out = []
        for r in runs:
            run_id = r["run_id"]
            tasks = db.get_all_tasks(run_id)
            findings = db.get_findings(run_id)
            out.append(RunSummary(
                run_id=run_id,
                repo_path=r["repo_path"],
                status=r["status"],
                total_cost=db.total_cost(run_id),
                task_count=len(tasks),
                finding_count=len(findings),
                started_at=r["started_at"],
                finished_at=r["finished_at"],
            ))
        return out
    finally:
        db.close()


@router.post("/runs", response_model=RunSummary, status_code=202)
async def start_run(req: RunCreateRequest):
    """Start a new pipeline run (equivalent to `audit run ...`)."""
    # Auth check first
    allow = _allow_api_key(req.allow_api_key)
    try:
        configure_auth(allow_api_key=allow)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repo_path = Path(req.repo).resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Repo path not found: {repo_path}")

    config = load_config(Path(req.config_path)) if req.config_path else load_config()
    if req.max_concurrency is not None:
        config.cap_concurrency(req.max_concurrency)

    # Build live_target
    target_url = req.target_url
    target_creds = _parse_creds(req.target_creds)
    scope_notes = req.scope_notes

    run_id = req.run_id or f"run_{uuid.uuid4().hex[:8]}"

    db = _get_db()
    try:
        # Check if run exists
        existing = db.get_run(run_id)
        if existing and not req.resume:
            raise HTTPException(
                status_code=409,
                detail=f"Run {run_id!r} already exists. Use resume=true to continue it.",
            )
        if not existing and req.resume:
            raise HTTPException(
                status_code=404,
                detail=f"Run {run_id!r} not found — cannot resume.",
            )

        # Start the pipeline in background
        await run_manager.start(
            repo_path=repo_path,
            run_id=run_id,
            db=db,
            config=config,
            resume=req.resume,
            max_cost_usd=req.max_cost_usd,
            max_concurrency=req.max_concurrency,
            max_recon_tasks=req.max_recon_tasks,
            target_url=target_url,
            target_creds=target_creds,
            scope_notes=scope_notes,
        )

        return RunSummary(
            run_id=run_id,
            repo_path=str(repo_path),
            status="running",
            total_cost=0.0,
            task_count=0,
            finding_count=0,
        )
    finally:
        # Don't close db — the pipeline needs it
        pass


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(run_id: str):
    """Get run detail with metrics (equivalent to `audit status --run-id`)."""
    db = _get_db()
    try:
        run = db.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")

        tasks = db.get_all_tasks(run_id)
        findings = db.get_findings(run_id)
        confirmed = [f for f in findings if f.validation_status == "confirmed"]
        canonical = [f for f in confirmed if f.is_canonical]
        reachable = db.get_reachable_canonical_findings(run_id)

        return RunDetail(
            run_id=run_id,
            repo_path=run["repo_path"],
            status=run["status"],
            started_at=run["started_at"],
            finished_at=run["finished_at"],
            total_cost=db.total_cost(run_id),
            tasks_total=len(tasks),
            tasks_pending=sum(1 for t in tasks if t.status == "pending"),
            tasks_done=sum(1 for t in tasks if t.status == "done"),
            tasks_failed=sum(1 for t in tasks if t.status == "failed"),
            tasks_running=sum(1 for t in tasks if t.status == "running"),
            findings_raw=len(findings),
            findings_confirmed=len(confirmed),
            findings_canonical=len(canonical),
            findings_reachable=len(reachable),
            is_active=run_manager.is_running(run_id),
        )
    finally:
        db.close()


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel a running pipeline."""
    if not run_manager.is_running(run_id):
        raise HTTPException(status_code=409, detail=f"Run {run_id!r} is not running")
    run_manager.cancel(run_id)
    return {"status": "cancelling", "run_id": run_id}


@router.post("/runs/{run_id}/resume", response_model=RunSummary, status_code=202)
async def resume_run(run_id: str):
    """Resume a stopped/aborted/failed run — auto-recovers failed tasks and continues."""
    db = _get_db()
    try:
        run = db.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")

        if run_manager.is_running(run_id):
            raise HTTPException(status_code=409, detail=f"Run {run_id!r} is already running")

        # Auto-recover failed tasks so they get re-attempted
        db.recover_failed_tasks(run_id)

        # Reset any stuck "running" tasks back to "pending"
        db.reset_running_tasks(run_id)

        # Launch pipeline with resume=True
        config = load_config()
        repo_path = Path(run["repo_path"])

        await run_manager.start(
            repo_path=repo_path,
            run_id=run_id,
            db=db,
            config=config,
            resume=True,
        )

        return RunSummary(
            run_id=run_id,
            repo_path=run["repo_path"],
            status="running",
            total_cost=db.total_cost(run_id),
            task_count=len(db.get_all_tasks(run_id)),
            finding_count=len(db.get_findings(run_id)),
        )
    finally:
        pass  # keep db open — the pipeline needs it


@router.get("/runs/{run_id}/tasks")
async def list_tasks(run_id: str):
    """List all tasks for a run."""
    db = _get_db()
    try:
        run = db.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
        tasks = db.get_all_tasks(run_id)
        return [
            {
                "task_id": t.task_id,
                "run_id": t.run_id,
                "source": t.source,
                "attack_class": t.attack_class,
                "scope_hint": t.scope_hint,
                "target_files": t.target_files,
                "rationale": t.rationale,
                "priority": t.priority,
                "status": t.status,
            }
            for t in tasks
        ]
    finally:
        db.close()


@router.post("/runs/{run_id}/recover", response_model=RecoverResponse)
async def recover_tasks(run_id: str, req: RecoverRequest):
    """Reset failed tasks back to pending (equivalent to `audit recover`)."""
    db = _get_db()
    try:
        run = db.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")

        failed = db.get_failed_tasks(run_id)
        failed_payload = [
            {
                "task_id": t.task_id,
                "attack_class": t.attack_class,
                "rationale": t.rationale[:80],
            }
            for t in failed
        ]

        if not failed:
            return RecoverResponse(
                applied=False,
                failed_tasks=[],
                changed_count=0,
                message=f"No failed tasks in {run_id}",
            )

        if not req.apply:
            return RecoverResponse(
                applied=False,
                failed_tasks=failed_payload,
                changed_count=0,
                message=f"Dry-run: {len(failed)} tasks would be reset. Pass apply=true to execute.",
            )

        changed = db.recover_failed_tasks(run_id)
        return RecoverResponse(
            applied=True,
            failed_tasks=failed_payload,
            changed_count=len(changed),
            message=f"Reset {len(changed)} task(s) to 'pending'. Resume the run to re-execute.",
        )
    finally:
        db.close()


@router.post("/runs/{run_id}/merge", response_model=MergeResponse)
async def merge_tasks_handler(run_id: str, req: MergeRequest):
    """Merge similar pending tasks (equivalent to `audit merge-tasks`)."""
    from audit.config import load_config
    from audit.stages._common import StageContext
    from audit.stages.merge_tasks import MIN_TASKS_TO_MERGE, run_merge_tasks

    db = _get_db()
    try:
        run = db.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")

        pending = db.get_pending_tasks(run_id)
        pending_payload = [
            {
                "task_id": t.task_id,
                "attack_class": t.attack_class,
                "priority": t.priority,
                "target_files": t.target_files,
                "rationale": t.rationale[:80],
            }
            for t in pending
        ]

        if not pending:
            return MergeResponse(
                applied=False,
                pending_tasks=[],
                saved_count=0,
                message=f"No pending tasks in {run_id}",
            )

        if len(pending) < MIN_TASKS_TO_MERGE:
            return MergeResponse(
                applied=False,
                pending_tasks=pending_payload,
                saved_count=0,
                message=f"Only {len(pending)} pending tasks (minimum {MIN_TASKS_TO_MERGE} required)",
            )

        if not req.apply:
            return MergeResponse(
                applied=False,
                pending_tasks=pending_payload,
                saved_count=0,
                message=f"Dry-run: {len(pending)} pending tasks. Pass apply=true to run merge.",
            )

        config = load_config()
        ctx = StageContext(
            run_id=run_id,
            repo_path=Path(run["repo_path"]),
            config=config,
        )
        saved = await run_merge_tasks(ctx, db)

        if saved > 0:
            return MergeResponse(
                applied=True,
                pending_tasks=pending_payload,
                saved_count=saved,
                message=f"Merged: removed {saved} redundant task(s)",
            )
        else:
            return MergeResponse(
                applied=True,
                pending_tasks=pending_payload,
                saved_count=0,
                message="Merge produced no reduction",
            )
    finally:
        db.close()


def _allow_api_key(flag: bool) -> bool:
    import os
    if flag:
        return True
    return os.environ.get("AUDIT_ALLOW_API_KEY", "").strip() not in ("", "0", "false", "False")


def _parse_creds(creds_list: list[str]) -> dict[str, str]:
    creds: dict[str, str] = {}
    for kv in creds_list:
        if "=" not in kv:
            raise HTTPException(status_code=400, detail=f"Invalid cred: {kv!r} — expected KEY=VALUE")
        k, _, v = kv.partition("=")
        creds[k.strip()] = v.strip()
    return creds
