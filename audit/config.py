"""Load per-stage configuration from config/stages.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class StageConfig:
    name: str
    model: str
    concurrency: int
    tools: list[str]
    max_turns: int
    permission_mode: str
    repair_attempts: int


@dataclass
class HarnessConfig:
    stages: dict[str, StageConfig] = field(default_factory=dict)
    # Per-run soft cap. Each `run_pipeline` invocation runs at most this many
    # iterations of the corresponding loop.
    gapfill_per_run: int = 2
    feedback_per_run: int = 1
    # Per-run-id hard cap. The counter is persisted in DB and survives
    # --resume. Effective iterations = min(per_run, max - already_used).
    max_gapfill_iterations: int = 100
    max_feedback_iterations: int = 50

    def get(self, stage: str) -> StageConfig:
        try:
            return self.stages[stage]
        except KeyError:
            raise KeyError(
                f"Unknown stage {stage!r}. Known: {sorted(self.stages)}"
            ) from None

    def cap_concurrency(self, cap: int) -> None:
        """Mutate every stage's concurrency to min(current, cap). Useful
        for cost-contained test runs."""
        if cap < 1:
            raise ValueError("concurrency cap must be >= 1")
        for sc in self.stages.values():
            sc.concurrency = min(sc.concurrency, cap)


def load_config(path: Path | None = None) -> HarnessConfig:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config" / "stages.yaml"
    raw = yaml.safe_load(path.read_text())
    defaults = raw.get("defaults", {}) or {}
    stages: dict[str, StageConfig] = {}
    for name, spec in (raw.get("stages") or {}).items():
        stages[name] = StageConfig(
            name=name,
            model=spec["model"],
            concurrency=int(spec["concurrency"]),
            tools=list(spec["tools"]),
            max_turns=int(spec.get("max_turns", defaults.get("max_turns", 25))),
            permission_mode=spec.get(
                "permission_mode", defaults.get("permission_mode", "acceptEdits")
            ),
            repair_attempts=int(
                spec.get("repair_attempts", defaults.get("repair_attempts", 1))
            ),
        )
    loops = raw.get("loops", {}) or {}
    max_iters = loops.get("max_iterations", {}) or {}
    return HarnessConfig(
        stages=stages,
        # New key is gapfill_per_run / feedback_per_run; fall back to the
        # legacy gapfill_iterations / feedback_iterations for old yaml.
        gapfill_per_run=int(loops.get(
            "gapfill_per_run", loops.get("gapfill_iterations", 2)
        )),
        feedback_per_run=int(loops.get(
            "feedback_per_run", loops.get("feedback_iterations", 1)
        )),
        max_gapfill_iterations=int(max_iters.get("gapfill", 100)),
        max_feedback_iterations=int(max_iters.get("feedback", 50)),
    )
