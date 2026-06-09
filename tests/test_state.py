"""StateDB roundtrip tests."""

from __future__ import annotations

from pathlib import Path

from audit.state import StateDB


def test_run_and_task_lifecycle(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "state.db")
    rid = db.create_run("/some/repo", "test_run")
    assert db.get_run(rid)["status"] == "running"

    db.add_task(rid, {
        "task_id": "t_1",
        "attack_class": "sqli",
        "scope_hint": "lookup name parameter",
        "target_files": ["app.py"],
        "rationale": "raw string formatting",
        "priority": 1,
        "source": "recon",
    })
    pending = db.get_pending_tasks(rid)
    assert len(pending) == 1
    assert pending[0].task_id == "t_1"

    db.update_task_status("t_1", "done")
    assert db.get_pending_tasks(rid) == []
    assert any(t.status == "done" for t in db.get_all_tasks(rid))

    db.finish_run(rid)
    assert db.get_run(rid)["status"] == "completed"
    db.close()


def test_finding_validation_and_dedupe(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "state.db")
    rid = db.create_run("/some/repo", "test_run")
    db.add_task(rid, {
        "task_id": "t_1", "attack_class": "sqli", "scope_hint": "x",
        "target_files": ["a.py"], "rationale": "r", "priority": 1, "source": "recon",
    })
    db.add_finding(rid, "t_1", {
        "finding_id": "f_1", "file": "a.py", "line_start": 1, "line_end": 2,
        "vuln_class": "sqli", "severity": "high",
        "description": "x", "evidence_snippet": "y", "confidence": 0.9,
    })
    assert len(db.get_unvalidated_findings(rid)) == 1

    db.set_finding_validation("f_1", "confirmed", {
        "finding_id": "f_1", "verdict": "confirmed",
        "rationale": "ok", "validator_confidence": 0.9,
    })
    assert len(db.get_findings(rid, validation_status="confirmed")) == 1

    db.add_dedupe_group(rid, {
        "group_id": "g_1", "root_cause": "rc",
        "canonical_finding_id": "f_1", "member_finding_ids": ["f_1"],
    })
    db.assign_finding_group("f_1", "g_1", True)
    assert len(db.get_findings(rid, canonical_only=True)) == 1

    db.add_trace("f_1", {
        "finding_id": "f_1", "reachable": True, "confidence": 0.9,
        "rationale": "trivial", "entry_points": [], "call_chain": [],
    })
    reachable = db.get_reachable_canonical_findings(rid)
    assert len(reachable) == 1
    db.close()


def test_cost_aggregation(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "state.db")
    rid = db.create_run("/r", "test_run")
    db.record_cost(rid, "hunt", "t_1", {"total_cost_usd": 0.01, "usage": {
        "input_tokens": 100, "output_tokens": 50,
    }, "num_turns": 3, "duration_ms": 1234})
    db.record_cost(rid, "hunt", "t_2", {"total_cost_usd": 0.02, "usage": {
        "input_tokens": 200, "output_tokens": 100,
    }, "num_turns": 5, "duration_ms": 4321})
    assert abs(db.total_cost(rid) - 0.03) < 1e-9
    db.close()


def test_loop_counter_increment(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "state.db")
    rid = db.create_run("/r", "test_run")
    assert db.get_loop_counter(rid, "gapfill") == 0
    assert db.increment_loop_counter(rid, "gapfill") == 1
    assert db.increment_loop_counter(rid, "gapfill") == 2
    assert db.get_loop_counter(rid, "gapfill") == 2
    db.close()


def test_loop_counter_independent_per_loop_name(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "state.db")
    rid = db.create_run("/r", "test_run")
    db.increment_loop_counter(rid, "gapfill")
    db.increment_loop_counter(rid, "gapfill")
    db.increment_loop_counter(rid, "feedback")
    assert db.get_loop_counter(rid, "gapfill") == 2
    assert db.get_loop_counter(rid, "feedback") == 1
    assert db.get_loop_counter(rid, "trace") == 0  # not touched
    db.close()


def test_loop_counter_persists_across_reopen(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "state.db")
    rid = db.create_run("/r", "test_run")
    db.increment_loop_counter(rid, "gapfill")
    db.increment_loop_counter(rid, "feedback")
    db.close()
    db2 = StateDB(tmp_path / "state.db")  # reopen same file
    assert db2.get_loop_counter(rid, "gapfill") == 1
    assert db2.get_loop_counter(rid, "feedback") == 1
    db2.close()


def test_reset_running_tasks(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "state.db")
    rid = db.create_run("/r", "test_run")
    db.add_task(rid, {"task_id": "t_1", "attack_class": "sqli",
                      "scope_hint": "x", "target_files": ["a.py"],
                      "rationale": "r", "priority": 1, "source": "recon"})
    db.add_task(rid, {"task_id": "t_2", "attack_class": "xss",
                      "scope_hint": "y", "target_files": ["b.py"],
                      "rationale": "r", "priority": 2, "source": "recon"})
    db.add_task(rid, {"task_id": "t_3", "attack_class": "ssrf",
                      "scope_hint": "z", "target_files": ["c.py"],
                      "rationale": "r", "priority": 3, "source": "recon"})
    db.update_task_status("t_1", "done")
    db.update_task_status("t_2", "running")
    # t_3 left as 'pending' — must not be touched

    n = db.reset_running_tasks(rid)
    assert n == 1
    statuses = {t.task_id: t.status for t in db.get_all_tasks(rid)}
    assert statuses == {"t_1": "done", "t_2": "pending", "t_3": "pending"}

    # Re-running is a no-op (nothing running)
    assert db.reset_running_tasks(rid) == 0
    db.close()


def test_recover_failed_tasks(tmp_path: Path) -> None:
    db = StateDB(tmp_path / "state.db")
    rid = db.create_run("/r", "test_run")
    db.add_task(rid, {"task_id": "t_1", "attack_class": "sqli",
                      "scope_hint": "x", "target_files": ["a.py"],
                      "rationale": "raw f-string", "priority": 1,
                      "source": "recon"})
    db.add_task(rid, {"task_id": "t_2", "attack_class": "xss",
                      "scope_hint": "y", "target_files": ["b.py"],
                      "rationale": "unescaped", "priority": 2,
                      "source": "recon"})
    db.add_task(rid, {"task_id": "t_3", "attack_class": "ssrf",
                      "scope_hint": "z", "target_files": ["c.py"],
                      "rationale": "user-controlled url", "priority": 3,
                      "source": "recon"})
    db.update_task_status("t_1", "done")
    db.update_task_status("t_2", "failed")
    # t_3 left as 'pending' — must not be touched

    failed = db.get_failed_tasks(rid)
    assert [t.task_id for t in failed] == ["t_2"]

    changed = db.recover_failed_tasks(rid)
    assert changed == ["t_2"]
    statuses = {t.task_id: t.status for t in db.get_all_tasks(rid)}
    assert statuses == {"t_1": "done", "t_2": "pending", "t_3": "pending"}

    # Re-running on a clean slate is a no-op (nothing failed)
    assert db.recover_failed_tasks(rid) == []
    db.close()
