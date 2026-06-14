"""Findings router — GET /api/runs/{run_id}/findings."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from audit.state import StateDB

from web.schemas import FindingResponse

router = APIRouter()

DB_PATH = Path(__file__).resolve().parent.parent.parent / "state.db"


def _get_db() -> StateDB:
    return StateDB(DB_PATH)


@router.get("/runs/{run_id}/findings", response_model=list[FindingResponse])
async def list_findings(
    run_id: str,
    validation_status: str | None = None,
    canonical_only: bool = False,
):
    """List findings for a run with optional filters."""
    db = _get_db()
    try:
        run = db.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")

        findings = db.get_findings(
            run_id,
            validation_status=validation_status,
            canonical_only=canonical_only,
        )

        out = []
        for f in findings:
            trace = db.get_trace(f.finding_id)
            out.append(FindingResponse(
                finding_id=f.finding_id,
                task_id=f.task_id,
                run_id=f.run_id,
                file=f.file,
                line_start=f.line_start,
                line_end=f.line_end,
                vuln_class=f.vuln_class,
                severity=f.severity,
                description=f.description,
                evidence=f.evidence,
                poc_succeeded=f.poc_succeeded,
                confidence=f.confidence,
                validation_status=f.validation_status,
                validation_json=f.validation_json,
                group_id=f.group_id,
                is_canonical=f.is_canonical,
                trace=trace,
            ))
        return out
    finally:
        db.close()
