"""WebSocket router — /ws/runs/{run_id} for real-time pipeline events."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from audit.state import StateDB

from web.ws_manager import ws_manager

router = APIRouter()

DB_PATH = Path(__file__).resolve().parent.parent.parent / "state.db"


@router.websocket("/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str):
    """Real-time pipeline event stream for a specific run.

    Receives structured events (stage_start, task_update, finding_added,
    cost_update, run_complete, run_error) and raw AI messages
    (stream_message with {kind, model, content}). Also accepts client
    commands: {"type": "cancel"} to cancel the active run, and
    {"type": "ping"} for keep-alive.
    """
    await ws_manager.connect(run_id, websocket)

    # Send initial snapshot so the client doesn't need a separate HTTP round-trip
    try:
        db = StateDB(DB_PATH)
        run = db.get_run(run_id)
        if run:
            tasks = db.get_all_tasks(run_id)
            findings = db.get_findings(run_id)
            await websocket.send_json({
                "type": "snapshot",
                "run": {
                    "run_id": run_id,
                    "repo_path": run["repo_path"],
                    "status": run["status"],
                    "started_at": run["started_at"],
                    "finished_at": run["finished_at"],
                },
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "attack_class": t.attack_class,
                        "target_files": t.target_files,
                        "priority": t.priority,
                        "status": t.status,
                    }
                    for t in tasks
                ],
                "findings": [
                    {
                        "finding_id": f.finding_id,
                        "task_id": f.task_id,
                        "vuln_class": f.vuln_class,
                        "severity": f.severity,
                        "file": f.file,
                        "validation_status": f.validation_status,
                        "is_canonical": f.is_canonical,
                    }
                    for f in findings
                ],
                "total_cost": db.total_cost(run_id),
            })
        db.close()
    except Exception:
        pass  # Don't let snapshot failure kill the WS

    try:
        while True:
            msg = await websocket.receive_json()
            cmd_type = msg.get("type", "")

            if cmd_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif cmd_type == "cancel":
                from web.run_manager import run_manager
                if run_manager.is_running(run_id):
                    run_manager.cancel(run_id)
                    await websocket.send_json({
                        "type": "cancel_ack",
                        "run_id": run_id,
                        "status": "cancelling",
                    })

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(run_id, websocket)
