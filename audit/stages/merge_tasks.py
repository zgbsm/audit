"""Stage 1b: Merge — consolidate similar pending tasks before Hunt.

Runs automatically after Recon (and optionally via CLI). When Recon
produces 30+ tasks, many target the same attack class / files from
slightly different angles — this stage sends the pending queue through
an AI de-duplicator so Hunt doesn't waste budget on redundant scans.
"""

from __future__ import annotations

import logging

from audit.runner import AgentRunError, TransientAgentError, run_agent
from audit.state import StateDB
from audit.stages._common import StageContext

log = logging.getLogger(__name__)

# Don't bother merging if there are fewer tasks than this.
MIN_TASKS_TO_MERGE = 5


async def run_merge_tasks(ctx: StageContext, db: StateDB) -> int:
    """Merge similar pending tasks into fewer, broader ones.

    Returns the number of tasks that were merged away (old_count - new_count).
    A positive number means consolidation happened. Zero means nothing changed
    (either too few tasks or the AI decided no merges were warranted).
    Raises on agent failure — caller should treat this as a soft error and
    continue with the original pending queue.
    """
    pending = db.get_pending_tasks(ctx.run_id)
    if len(pending) < MIN_TASKS_TO_MERGE:
        log.info(
            "[%s] merge: %d pending tasks (< %d), skipping",
            ctx.run_id, len(pending), MIN_TASKS_TO_MERGE,
        )
        return 0

    sc = ctx.stage("recon")  # reuse recon stage config (same tools/model)
    tasks_payload = [
        {
            "task_id": t.task_id,
            "attack_class": t.attack_class,
            "scope_hint": t.scope_hint,
            "target_files": t.target_files,
            "rationale": t.rationale,
            "priority": t.priority,
            "source": t.source,
        }
        for t in pending
    ]

    log.info(
        "[%s] merge: %d pending tasks → AI dedup (model=%s)",
        ctx.run_id, len(pending), sc.model,
    )

    try:
        result = await run_agent(
            stage="merge",
            prompt_file=ctx.prompt("merge-tasks"),
            user_input={
                "pending_tasks": tasks_payload,
                "repo_path": str(ctx.repo_path),
                **ctx.extras(),
            },
            schema_file=ctx.schema("merge_output"),
            allowed_tools=sc.tools,
            model=sc.model,
            cwd=ctx.repo_path,
            add_dirs=[ctx.repo_path],
            max_turns=sc.max_turns,
            permission_mode=sc.permission_mode,
            artifact_dir=ctx.results_dir("merge"),
            artifact_name="merge",
            repair_attempts=sc.repair_attempts,
            stream_callback=ctx.stream_callback,
        )
    except (AgentRunError, TransientAgentError) as e:
        log.warning(
            "[%s] merge agent failed: %s — keeping original %d tasks",
            ctx.run_id, e, len(pending),
        )
        return 0

    merged = result.payload.get("merged_tasks", []) or []
    merge_notes = result.payload.get("merge_notes", []) or []

    if not merged:
        log.warning(
            "[%s] merge agent returned 0 tasks — keeping original %d",
            ctx.run_id, len(pending),
        )
        return 0

    if len(merged) >= len(pending):
        log.info(
            "[%s] merge: no reduction (%d → %d tasks), skipping",
            ctx.run_id, len(pending), len(merged),
        )
        return 0

    # Atomically replace the pending queue.
    removed = db.delete_pending_tasks(ctx.run_id)
    added = 0
    for t in merged:
        t.setdefault("source", "recon")
        db.add_task(ctx.run_id, t)
        added += 1

    db.record_cost(ctx.run_id, "merge", None, result.raw_result_message)
    db.add_artifact(ctx.run_id, "merge", None, "jsonl", str(result.artifact_path))

    saved = removed - added
    log.info(
        "[%s] merge: %d pending tasks → %d (removed %d, added %d, saved %d)  "
        "merge_groups=%d",
        ctx.run_id, removed, added, removed, added, saved, len(merge_notes),
    )
    return saved
