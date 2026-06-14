"""Pipeline observer — emits structured events for WebSocket broadcast.

This sits alongside the existing stream_callback (which carries raw AI
messages) and emits higher-level pipeline events: stage transitions,
task status changes, new findings, and cost updates.
"""

from __future__ import annotations

import logging
from typing import Any

from audit.stages._common import StageContext

from web.ws_manager import ws_manager

log = logging.getLogger(__name__)


class PipelineObserver:
    """Observes pipeline progress and broadcasts structured events.

    Each method accepts a run_id and event-specific data, builds a
    typed event dict, and sends it to all WebSocket subscribers for
    that run.
    """

    def on_stage_start(self, run_id: str, stage: str, detail: dict | None = None) -> None:
        event: dict[str, Any] = {
            "type": "stage_start",
            "stage": stage,
            "detail": detail or {},
        }
        log.debug("[%s] stage_start: %s", run_id, stage)
        ws_manager.broadcast(run_id, event)

    def on_stage_end(self, run_id: str, stage: str, detail: dict | None = None) -> None:
        event: dict[str, Any] = {
            "type": "stage_end",
            "stage": stage,
            "detail": detail or {},
        }
        log.debug("[%s] stage_end: %s", run_id, stage)
        ws_manager.broadcast(run_id, event)

    def on_task_update(self, run_id: str, task_id: str, status: str,
                       attack_class: str = "", findings: int = 0) -> None:
        ws_manager.broadcast(run_id, {
            "type": "task_update",
            "task_id": task_id,
            "status": status,
            "attack_class": attack_class,
            "findings": findings,
        })

    def on_finding_added(self, run_id: str, finding_id: str, task_id: str,
                         vuln_class: str, severity: str, file: str) -> None:
        ws_manager.broadcast(run_id, {
            "type": "finding",
            "finding_id": finding_id,
            "task_id": task_id,
            "vuln_class": vuln_class,
            "severity": severity,
            "file": file,
        })

    def on_cost_update(self, run_id: str, stage: str, usd: float,
                       input_tokens: int = 0, output_tokens: int = 0) -> None:
        ws_manager.broadcast(run_id, {
            "type": "cost_update",
            "stage": stage,
            "usd": usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })

    def on_run_complete(self, run_id: str, status: str, report_path: str = "",
                        total_cost: float = 0.0) -> None:
        ws_manager.broadcast(run_id, {
            "type": "run_complete",
            "run_id": run_id,
            "status": status,
            "report_path": report_path,
            "total_cost": total_cost,
        })

    def on_run_error(self, run_id: str, error_type: str, message: str) -> None:
        ws_manager.broadcast(run_id, {
            "type": "run_error",
            "run_id": run_id,
            "error_type": error_type,
            "message": message,
        })

    def on_log(self, run_id: str, level: str, message: str) -> None:
        ws_manager.broadcast(run_id, {
            "type": "log",
            "level": level,
            "message": message,
        })


# Singleton
pipeline_observer = PipelineObserver()


def make_stream_forwarder(run_id: str):
    """Return a stream_callback that forwards raw AI messages to WebSocket.

    This mirrors the CLI's _make_stream_callback but sends messages as
    'stream_message' WebSocket events instead of printing Rich panels.
    """
    def _forward(msg: dict) -> None:
        ws_manager.broadcast(run_id, {
            "type": "stream_message",
            "data": msg,
        })
    return _forward
