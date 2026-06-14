"""Run manager — manages background pipeline execution.

Tracks active asyncio.Tasks per run_id, provides cancellation, and
handles cleanup on completion/failure.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable

from audit.config import HarnessConfig
from audit.orchestrator import CostExceeded, run_pipeline
from audit.runner import QuotaExhaustedError
from audit.state import StateDB

from web.observer import PipelineObserver, pipeline_observer, make_stream_forwarder

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent / "state.db"


class RunHandle:
    """Tracks a single running pipeline."""

    def __init__(self, run_id: str, task: asyncio.Task, cancel_event: asyncio.Event) -> None:
        self.run_id = run_id
        self.task = task
        self.cancel_event = cancel_event

    def cancel(self) -> None:
        self.cancel_event.set()


class RunManager:
    """Singleton managing all active pipeline runs.

    Each run_pipeline() invocation is wrapped in an asyncio.Task so the
    web server remains responsive during long-running pipelines.
    """

    def __init__(self) -> None:
        self._runs: dict[str, RunHandle] = {}

    async def start(
        self,
        repo_path: Path,
        run_id: str,
        db: StateDB,
        config: HarnessConfig,
        *,
        resume: bool = False,
        max_cost_usd: float | None = None,
        max_concurrency: int | None = None,
        max_recon_tasks: int | None = None,
        target_url: str | None = None,
        target_creds: dict[str, str] | None = None,
        scope_notes: str | None = None,
        observer: PipelineObserver = pipeline_observer,
    ) -> str:
        """Launch a pipeline run in the background."""
        if run_id in self._runs:
            raise ValueError(f"Run {run_id!r} is already running")

        cancel_event = asyncio.Event()
        stream_callback = make_stream_forwarder(run_id)

        # Build live_target dict if URL provided
        live_target: dict | None = None
        if target_url:
            live_target = {"url": target_url, "credentials": target_creds or {}}

        task = asyncio.create_task(
            _run_pipeline_wrapper(
                repo_path=repo_path,
                run_id=run_id,
                db=db,
                config=config,
                max_cost_usd=max_cost_usd,
                resume=resume,
                max_recon_tasks=max_recon_tasks,
                live_target=live_target,
                scope_notes=scope_notes,
                stream_callback=stream_callback,
                observer=observer,
                cancel_event=cancel_event,
            ),
            name=f"pipeline-{run_id}",
        )

        handle = RunHandle(run_id, task, cancel_event)
        self._runs[run_id] = handle

        # Schedule cleanup when task completes
        task.add_done_callback(lambda t: self._cleanup(run_id))

        log.info("run_manager: started %s", run_id)
        return run_id

    def cancel(self, run_id: str) -> bool:
        """Force-cancel a running pipeline. Returns True if found.

        Sets the cancel_event (for cooperative checks) AND calls
        task.cancel() to immediately inject CancelledError into the
        running coroutine — the pipeline stops without waiting for
        the current LLM call to finish.
        """
        handle = self._runs.get(run_id)
        if handle is None:
            return False
        handle.cancel_event.set()
        handle.task.cancel()
        log.info("run_manager: cancel requested for %s", run_id)
        return True

    def is_running(self, run_id: str) -> bool:
        return run_id in self._runs

    def get_active_runs(self) -> set[str]:
        return set(self._runs.keys())

    def _cleanup(self, run_id: str) -> None:
        self._runs.pop(run_id, None)
        log.info("run_manager: cleaned up %s", run_id)


# Singleton
run_manager = RunManager()


async def _run_pipeline_wrapper(
    repo_path: Path,
    run_id: str,
    db: StateDB,
    config: HarnessConfig,
    max_cost_usd: float | None = None,
    resume: bool = False,
    max_recon_tasks: int | None = None,
    live_target: dict | None = None,
    scope_notes: str | None = None,
    stream_callback: Callable[[dict], None] | None = None,
    observer: PipelineObserver = pipeline_observer,
    cancel_event: asyncio.Event | None = None,
) -> None:
    """Wrapper that calls run_pipeline and handles errors → observer events."""
    try:
        observer.on_stage_start(run_id, "pipeline", {"repo": str(repo_path)})

        report_path = await run_pipeline(
            repo_path=repo_path,
            run_id=run_id,
            db=db,
            config=config,
            max_cost_usd=max_cost_usd,
            resume=resume,
            max_recon_tasks=max_recon_tasks,
            live_target=live_target,
            scope_notes=scope_notes,
            stream_callback=stream_callback,
            observer=observer,
            cancel_event=cancel_event,
        )

        total_cost = db.total_cost(run_id)
        observer.on_run_complete(
            run_id,
            status="completed",
            report_path=str(report_path),
            total_cost=total_cost,
        )

    except asyncio.CancelledError:
        db.reset_running_tasks(run_id)  # so they can be retried on resume
        db.finish_run(run_id, "aborted")
        observer.on_run_complete(run_id, status="aborted", total_cost=db.total_cost(run_id))
        log.warning("[%s] pipeline cancelled", run_id)

    except CostExceeded as e:
        db.finish_run(run_id, "aborted")
        observer.on_run_error(run_id, "cost_exceeded", str(e))
        log.error("[%s] cost exceeded: %s", run_id, e)

    except QuotaExhaustedError as e:
        db.finish_run(run_id, "aborted")
        observer.on_run_error(run_id, "quota_exhausted", str(e)[:500])
        log.error("[%s] quota exhausted: %s", run_id, str(e)[:300])

    except Exception as e:
        db.finish_run(run_id, "failed")
        observer.on_run_error(run_id, type(e).__name__, str(e)[:1000])
        log.exception("[%s] pipeline failed: %s", run_id, e)
