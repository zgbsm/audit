"""Pipeline driver: Recon → (Hunt → Validate → Gapfill)* → Dedupe → Trace
                  → Feedback → (Hunt → Validate → Dedupe → Trace)* → Report
"""

from __future__ import annotations

import logging
from pathlib import Path

from audit import stages
from audit.config import HarnessConfig
from audit.runner import QuotaExhaustedError
from audit.state import StateDB
from audit.stages._common import StageContext

log = logging.getLogger(__name__)


class CostExceeded(RuntimeError):
    pass


async def run_pipeline(
    *,
    repo_path: Path,
    run_id: str,
    db: StateDB,
    config: HarnessConfig,
    max_cost_usd: float | None = None,
    resume: bool = False,
    max_recon_tasks: int | None = None,
    live_target: dict | None = None,
    scope_notes: str | None = None,
) -> Path:
    ctx = StageContext(
        run_id=run_id,
        repo_path=repo_path.resolve(),
        config=config,
        live_target=live_target,
        scope_notes=scope_notes,
    )

    if db.get_run(run_id) is None:
        db.create_run(str(repo_path.resolve()), run_id)
        log.info("[%s] starting fresh pipeline run against %s", run_id, repo_path)
    elif resume:
        # Flip status back to 'running' so subsequent /status calls don't
        # report a stale 'aborted'/'failed' while resume work is ongoing.
        db._conn.execute(  # type: ignore[attr-defined]
            "UPDATE runs SET status = 'running', finished_at = NULL WHERE run_id = ?",
            (run_id,),
        )
        db._conn.commit()  # type: ignore[attr-defined]
        # Recover tasks that were mid-execution when the process crashed:
        # the Hunt stage sets status='running' at dispatch and only flips
        # to 'done'/'failed' on completion. If the process died in between,
        # those tasks are orphaned — get_pending_tasks() won't see them.
        recovered = db.reset_running_tasks(run_id)
        if recovered:
            log.info("[%s] recovered %d running task(s) → pending", run_id, recovered)
        log.info("[%s] resuming existing run", run_id)
    else:
        raise RuntimeError(
            f"run_id {run_id!r} already exists; pass --resume to continue it."
        )

    def _budget_check(stage_name: str) -> None:
        if max_cost_usd is None:
            return
        spent = db.total_cost(run_id)
        if spent >= max_cost_usd:
            raise CostExceeded(
                f"[{run_id}] budget exhausted before {stage_name}: "
                f"${spent:.4f} >= ${max_cost_usd:.4f}"
            )

    try:
        # ---- Stage 1: Recon ----
        _budget_check("recon")
        recon_kwargs = {} if max_recon_tasks is None else {"max_tasks": max_recon_tasks}
        await stages.run_recon(ctx, db, **recon_kwargs)

        # ---- Stages 2-3-4 loop: Hunt → Validate → Gapfill ----
        # Budget = min(per_run + 1, max_iterations - already_used). The +1
        # preserves the legacy `range(gapfill_iterations + 1)` semantic.
        gapfill_used = db.get_loop_counter(run_id, "gapfill")
        gapfill_remaining = max(0, config.max_gapfill_iterations - gapfill_used)
        gapfill_budget = min(config.gapfill_per_run + 1, gapfill_remaining)
        if gapfill_budget <= 0:
            log.warning(
                "[%s] gapfill cap exhausted (%d/%d) — skipping loop",
                run_id, gapfill_used, config.max_gapfill_iterations,
            )
        else:
            if gapfill_remaining < config.gapfill_per_run + 1:
                log.info(
                    "[%s] gapfill loop bounded to %d iterations "
                    "(per_run=%d, cap_remaining=%d)",
                    run_id, gapfill_budget, config.gapfill_per_run, gapfill_remaining,
                )
            for i in range(gapfill_budget):
                _budget_check(f"hunt(iter={i})")
                findings_added = await stages.run_hunt(ctx, db, budget_check=_budget_check)
                if findings_added == 0 and i > 0:
                    log.info("[%s] no new findings — exiting Hunt/Gapfill loop", run_id)
                    break

                _budget_check(f"validate(iter={i})")
                await stages.run_validate(ctx, db)

                # Persist progress only after a successful iteration
                new_count = db.increment_loop_counter(run_id, "gapfill")
                log.debug("[%s] gapfill counter → %d", run_id, new_count)

                if i >= config.gapfill_per_run:
                    break  # final iteration: don't gapfill again
                _budget_check(f"gapfill(iter={i})")
                new_tasks = await stages.run_gapfill(ctx, db)
                if new_tasks == 0:
                    log.info("[%s] gapfill produced 0 tasks — exiting loop", run_id)
                    break

        # ---- Stage 5: Dedupe ----
        _budget_check("dedupe")
        await stages.run_dedupe(ctx, db)

        # ---- Stage 6: Trace ----
        _budget_check("trace")
        await stages.run_trace(ctx, db)

        # ---- Stage 7: Feedback (re-runs Hunt/Validate/Dedupe/Trace) ----
        # Budget = min(per_run, max_iterations - already_used). No +1 here —
        # matches the legacy `range(feedback_iterations)` semantic.
        feedback_used = db.get_loop_counter(run_id, "feedback")
        feedback_remaining = max(0, config.max_feedback_iterations - feedback_used)
        feedback_budget = min(config.feedback_per_run, feedback_remaining)
        if feedback_budget <= 0:
            log.warning(
                "[%s] feedback cap exhausted (%d/%d) — skipping loop",
                run_id, feedback_used, config.max_feedback_iterations,
            )
        else:
            if feedback_remaining < config.feedback_per_run:
                log.info(
                    "[%s] feedback loop bounded to %d iterations "
                    "(per_run=%d, cap_remaining=%d)",
                    run_id, feedback_budget, config.feedback_per_run, feedback_remaining,
                )
            for i in range(feedback_budget):
                _budget_check(f"feedback(iter={i})")
                new_tasks = await stages.run_feedback(ctx, db)
                if new_tasks == 0:
                    break
                _budget_check(f"feedback-hunt(iter={i})")
                await stages.run_hunt(ctx, db)
                _budget_check(f"feedback-validate(iter={i})")
                await stages.run_validate(ctx, db)
                _budget_check(f"feedback-dedupe(iter={i})")
                await stages.run_dedupe(ctx, db)
                _budget_check(f"feedback-trace(iter={i})")
                await stages.run_trace(ctx, db)
                # Persist progress only after a successful iteration
                new_count = db.increment_loop_counter(run_id, "feedback")
                log.debug("[%s] feedback counter → %d", run_id, new_count)

        # ---- Stage 8: Report ----
        _budget_check("report")
        report_path = await stages.run_report(ctx, db)

        db.finish_run(run_id, "completed")
        log.info(
            "[%s] pipeline complete: total cost $%.4f — report at %s",
            run_id, db.total_cost(run_id), report_path,
        )
        return report_path

    except CostExceeded as e:
        log.error(str(e))
        db.finish_run(run_id, "aborted")
        raise
    except QuotaExhaustedError as e:
        # Subscription quota exhausted — surface clearly; user must wait
        # for the reset window. Run is resumable via --resume once quota
        # returns.
        log.error(
            "[%s] subscription quota exhausted — aborting (resumable with --resume): %s",
            run_id, str(e)[:300],
        )
        db.finish_run(run_id, "aborted")
        raise
    except Exception:
        db.finish_run(run_id, "failed")
        raise
