"""Report router — GET /api/runs/{run_id}/report."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from audit.state import StateDB

router = APIRouter()

DB_PATH = Path(__file__).resolve().parent.parent.parent / "state.db"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_ROOT = REPO_ROOT / "results"


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str, format: str = "json"):
    """Get the final report (equivalent to `audit report --run-id`)."""
    report_path = RESULTS_ROOT / run_id / "report" / "report.json"

    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No report found for run {run_id!r}. The run may not be complete yet.",
        )

    payload = json.loads(report_path.read_text())

    if format == "md":
        from audit.cli import _render_markdown_report
        md = _render_markdown_report(payload)
        return PlainTextResponse(content=md, media_type="text/markdown")

    return payload
