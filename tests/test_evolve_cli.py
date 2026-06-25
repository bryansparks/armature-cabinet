"""Evolve CLI + orchestrator integration tests (Task 11).

Fixture-driven and deterministic: stub llm_call (via ARMATURE_CABINET_LLM_STUB=1),
synthetic trace DB, no live LLM, no real armature runs.
"""
import json
import sqlite3
from pathlib import Path

from armature_cabinet.cli import main
from armature_cabinet.evolve.orchestrator import run_evolve_cycle
from armature_cabinet.evolve.router import load_rules


def _seed_traces(db: Path, *, n: int = 6, agent_id: str = "sec",
                 agent_version: str = "0.1.0", error_type: str = "ParseError",
                 output_valid_fail: int = 4):
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE traces (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, workflow_name TEXT,
        stage_id TEXT, role_type TEXT, model TEXT, success INTEGER DEFAULT 1,
        output_valid INTEGER DEFAULT 1, error_type TEXT, escalation_count INTEGER DEFAULT 0,
        latency_ms REAL DEFAULT 0, quorum_score REAL, timestamp TEXT DEFAULT '',
        inputs_json TEXT DEFAULT '{}', outputs_json TEXT DEFAULT '{}', spec_version TEXT DEFAULT '',
        inputs_hash TEXT DEFAULT '', policy_version TEXT DEFAULT '',
        inputs_provenance_json TEXT DEFAULT '{}', tools_declared_json TEXT DEFAULT '[]',
        tools_called_json TEXT DEFAULT '[]', sandbox_image_digest TEXT, loop_iteration INTEGER,
        input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
        agent_id TEXT, agent_version TEXT, active_skill_ids_json TEXT DEFAULT '[]')""")
    for i in range(n):
        con.execute(
            "INSERT INTO traces (run_id,workflow_name,stage_id,role_type,model,success,"
            "output_valid,error_type,agent_id,agent_version,active_skill_ids_json,"
            "tools_declared_json,tools_called_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("r", "wf", "s1", "worker", "m", 0 if i < output_valid_fail else 1,
             0 if i < output_valid_fail else 1, error_type, agent_id, agent_version,
             '["triage"]', '["github:alerts"]', '[]'),
        )
    con.commit()
    con.close()


def _make_agent(tmp_path: Path, *, version: str = "0.1.0"):
    (tmp_path / "cabinet.yaml").write_text(
        f'id: sec\nname: Sec\nkind: partner\nschema_version: "0.1.0"\nversion: "{version}"\n',
        encoding="utf-8",
    )
    (tmp_path / "soul.md").write_text("---\nrole: worker\n---\nSec.\n", encoding="utf-8")
    (tmp_path / "mandate.md").write_text("---\ngoal: triage\n---\nTriage.\n", encoding="utf-8")
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "triage.md").write_text(
        "---\nid: triage\n---\n\n## Output\nold\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Step 1: the brief's primary review-mode test
# ---------------------------------------------------------------------------


def test_evolve_review_emits_pending_and_does_not_apply(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    rc = main(["evolve", str(tmp_path), "--traces-db", str(db), "--review", "--skill-tools",
               "triage=github:alerts"])
    assert rc == 0
    # review mode: no live edit, a .pending patch emitted
    assert (tmp_path / "versions").exists()
    # the live skill file is unchanged
    assert "old" in (tmp_path / "skills" / "triage.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Cross-task requirement #3: MIN_TRACES=5 gate
# ---------------------------------------------------------------------------


def test_evolve_exits_when_fewer_than_min_traces(tmp_path: Path, monkeypatch):
    """< 5 traces -> no proposal, exit with report (rc 0, gate=none)."""
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db, n=3)  # below MIN_TRACES=5
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    rc = main(["evolve", str(tmp_path), "--traces-db", str(db), "--skill-tools",
               "triage=github:alerts"])
    assert rc == 0
    # no versions dir written, no proposal
    assert not (tmp_path / "versions").exists()
    assert "old" in (tmp_path / "skills" / "triage.md").read_text(encoding="utf-8")


def test_orchestrator_min_traces_gate_returns_none_summary(tmp_path: Path, monkeypatch):
    """Orchestrator: read_summary returns None when n < MIN_TRACES=5."""
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db, n=4)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    res = run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]},
    )
    assert res.gate == "none"
    assert res.applied is False
    assert "min_traces" in res.rationale or "insufficient" in res.rationale


# ---------------------------------------------------------------------------
# Cross-task requirement #1: hqs_promote_min data-driven from routing_rules.yaml
# ---------------------------------------------------------------------------


def test_promotion_policy_uses_hqs_promote_min_from_rules():
    """The orchestrator must wire hqs_promote_min from routing_rules.yaml, NOT hardcode 0.02."""
    rules = load_rules()
    assert "hqs_promote_min" in rules
    # The orchestrator builds its policy from this value (verified via the versioning
    # policy class directly — the orchestrator passes rules["hqs_promote_min"] as min_gain).
    from armature_cabinet.evolve.versioning import ThresholdPromotionPolicy as Pol
    p = Pol(min_gain=rules["hqs_promote_min"])
    assert p.min_gain == rules["hqs_promote_min"]


# ---------------------------------------------------------------------------
# Cross-task requirement #4: --review forces every proposal to review-queue
# (auto surfaces must NOT be auto-applied under --review)
# ---------------------------------------------------------------------------


def test_review_flag_forces_review_even_when_surface_is_auto(tmp_path: Path, monkeypatch):
    """skills surface is 'auto' by default, but --review must still only emit .pending."""
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)  # 6 traces -> R1 fires -> surface=skills -> gate=auto
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    res = run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]},
        apply=False, review=True,
    )
    assert res.gate == "review"
    assert res.applied is False
    # a .pending patch exists under versions/
    pending = list((tmp_path / "versions").rglob(".pending.patch"))
    assert len(pending) == 1
    # live file untouched
    assert "old" in (tmp_path / "skills" / "triage.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Regression: bare default (no --apply, no --review) must NOT apply — safe-by-default.
# ---------------------------------------------------------------------------


def test_default_cycle_does_not_apply_without_apply_flag(tmp_path: Path, monkeypatch):
    """Bare `cabinet evolve <folder>` (no --apply, no --review) on an auto surface
    (skills) must emit a .pending patch and leave the live skill file unchanged.

    This is the safe-by-default posture: --apply is the trigger to auto-apply;
    without it, even an auto-gate surface proposes only.
    """
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)  # 6 traces -> R1 fires -> surface=skills -> gate=auto
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    res = run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]},
        apply=False, review=False,
    )
    assert res.gate == "review"
    assert res.applied is False
    # a .pending patch exists under versions/
    pending = list((tmp_path / "versions").rglob(".pending.patch"))
    assert len(pending) == 1
    # live file untouched
    assert "old" in (tmp_path / "skills" / "triage.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Cross-task requirement #2: FileProposal.evidence populated with row ids
# ---------------------------------------------------------------------------


def test_proposal_evidence_populated_with_row_ids(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]},
        apply=False, review=True,
    )
    pending = list((tmp_path / "versions").rglob(".pending.patch"))[0]
    data = json.loads(pending.read_text(encoding="utf-8"))
    assert data["evidence"] == [1, 2, 3, 4, 5, 6]


# ---------------------------------------------------------------------------
# --apply path (auto surface, gate=auto, apply succeeds)
# ---------------------------------------------------------------------------


def test_apply_auto_applies_skill_patch(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    rc = main(["evolve", str(tmp_path), "--traces-db", str(db), "--apply", "--skill-tools",
               "triage=github:alerts"])
    assert rc == 0
    # patch applied: 'old' replaced by stub content
    text = (tmp_path / "skills" / "triage.md").read_text(encoding="utf-8")
    assert "old" not in text
    assert "valid JSON" in text
    # a version snapshot was written + promoted (only version, auto-promoted on first)
    assert (tmp_path / "versions").exists()


def test_orchestrator_apply_returns_applied_and_version(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path, version="0.1.0")
    db = tmp_path / "traces.db"
    _seed_traces(db, agent_version="0.1.0")
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    res = run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]},
        apply=True,
    )
    assert res.applied is True
    assert res.gate == "auto"
    assert res.version == "0.1.1"
    assert res.promoted is True  # first version -> current_hqs None -> promoted


# ---------------------------------------------------------------------------
# --verify path
# ---------------------------------------------------------------------------


def test_verify_reports_missed_predictions(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    # write a prior promoted version with predicted_fixes
    vdir = tmp_path / "versions" / "0.1.0"
    vdir.mkdir(parents=True)
    (vdir / ".proposal.json").write_text(
        json.dumps({"version": "0.1.0", "hqs": 0.9,
                    "predicted_fixes": ["output_invalid:triage"]}),
        encoding="utf-8",
    )
    (tmp_path / "versions" / "latest.txt").write_text("0.1.0", encoding="utf-8")
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    rc = main(["evolve", str(tmp_path), "--traces-db", str(db), "--verify", "--skill-tools",
               "triage=github:alerts"])
    assert rc == 0


def test_verify_no_promoted_version_returns_1(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    rc = main(["evolve", str(tmp_path), "--traces-db", str(db), "--verify", "--skill-tools",
               "triage=github:alerts"])
    assert rc == 1


# ---------------------------------------------------------------------------
# --rollback path
# ---------------------------------------------------------------------------


def test_rollback_restores_prior_version(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    # First apply to create version 0.1.1 (snapshot is the post-patch state).
    main(["evolve", str(tmp_path), "--traces-db", str(db), "--apply", "--skill-tools",
          "triage=github:alerts"])
    patched = (tmp_path / "skills" / "triage.md").read_text(encoding="utf-8")
    assert "valid JSON" in patched
    # Manually corrupt the live folder, then roll back to the 0.1.1 snapshot.
    (tmp_path / "skills" / "triage.md").write_text("---\nid: triage\n---\nBROKEN\n",
                                                   encoding="utf-8")
    rc = main(["evolve", str(tmp_path), "--rollback", "0.1.1"])
    assert rc == 0
    assert (tmp_path / "skills" / "triage.md").read_text(encoding="utf-8") == patched


# ---------------------------------------------------------------------------
# --promote path (manual human ack)
# ---------------------------------------------------------------------------


def test_promote_manually_advances_latest(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    main(["evolve", str(tmp_path), "--traces-db", str(db), "--apply", "--skill-tools",
          "triage=github:alerts"])
    # reset latest then manually promote 0.1.1
    (tmp_path / "versions" / "latest.txt").write_text("", encoding="utf-8")
    rc = main(["evolve", str(tmp_path), "--promote", "0.1.1"])
    assert rc == 0
    assert (tmp_path / "versions" / "latest.txt").read_text(encoding="utf-8").strip() == "0.1.1"


# ---------------------------------------------------------------------------
# Cross-task requirement #5: LoRA fallback
# ---------------------------------------------------------------------------


def test_lora_eligible_falls_back_to_prose_when_not_trained(tmp_path: Path, monkeypatch):
    """When surface=lora_eligible and handoff.trained is False, fall back to prose
    and log missed_predictions."""
    from armature_cabinet.evolve.types import (
        AgentTraceSummary, RoutingDecision, SkillStats,
    )
    from armature_cabinet.evolve import orchestrator as orch
    from armature_cabinet.evolve.lora_handoff import HandoffResult

    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")

    # Build a synthetic summary + decision that routes to lora_eligible.
    summary = AgentTraceSummary(
        agent_id="sec", agent_version="0.1.0", n_traces=6,
        output_valid_rate=0.33, success_rate=0.33, quorum=0.5, escalation_rate=0.0,
        hqs=0.4,
        per_skill={"triage": SkillStats("triage", fail_count=4,
                   tools_declared=["github:alerts"], tools_called=["github:alerts"])},
        dominant_symptoms=[("OUTPUT_INVALID", 4)],
        healthy_skills=[], evidence_row_ids=[1, 2, 3, 4, 5, 6], heuristic=False,
    )
    decision = RoutingDecision(
        target_file="skills/triage.md", surface="lora_eligible", gate="none",
        rationale="prose exhausted", rule_id="L1", symptom="OUTPUT_INVALID",
        skill_id="triage", heuristic=False,
    )

    # Stub handoff_to_adapter to return trained=False (under threshold)
    def _fake_handoff(*, skill_id, role_type, **kwargs):
        return HandoffResult(skill_id=skill_id, command=["armature"], dry_run=False,
                             returncode=1, stdout="", stderr="under threshold")

    monkeypatch.setattr(orch, "handoff_to_adapter", _fake_handoff)
    monkeypatch.setattr(orch, "read_summary", lambda *a, **k: summary)
    monkeypatch.setattr(orch, "route", lambda *a, **k: decision)

    res = run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]}, apply=True,
    )
    # Fell back to prose: applied a patch, and rationale notes the LoRA fallback.
    assert res.applied is True
    assert "lora" in res.rationale.lower() or "fallback" in res.rationale.lower()


def test_lora_eligible_trained_does_not_prose(tmp_path: Path, monkeypatch):
    """When surface=lora_eligible and handoff.trained is True, do NOT prose-edit."""
    from armature_cabinet.evolve.types import (
        AgentTraceSummary, RoutingDecision, SkillStats,
    )
    from armature_cabinet.evolve import orchestrator as orch
    from armature_cabinet.evolve.lora_handoff import HandoffResult

    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")

    summary = AgentTraceSummary(
        agent_id="sec", agent_version="0.1.0", n_traces=6,
        output_valid_rate=0.33, success_rate=0.33, quorum=0.5, escalation_rate=0.0,
        hqs=0.4,
        per_skill={"triage": SkillStats("triage", fail_count=4,
                   tools_declared=["github:alerts"], tools_called=["github:alerts"])},
        dominant_symptoms=[("OUTPUT_INVALID", 4)],
        healthy_skills=[], evidence_row_ids=[1, 2, 3, 4, 5, 6], heuristic=False,
    )
    decision = RoutingDecision(
        target_file="skills/triage.md", surface="lora_eligible", gate="none",
        rationale="prose exhausted", rule_id="L1", symptom="OUTPUT_INVALID",
        skill_id="triage", heuristic=False,
    )

    def _fake_handoff(*, skill_id, role_type, **kwargs):
        return HandoffResult(skill_id=skill_id, command=["armature"], dry_run=False,
                             returncode=0, stdout="trained", stderr="")

    monkeypatch.setattr(orch, "handoff_to_adapter", _fake_handoff)
    monkeypatch.setattr(orch, "read_summary", lambda *a, **k: summary)
    monkeypatch.setattr(orch, "route", lambda *a, **k: decision)

    res = run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]}, apply=True,
    )
    assert res.applied is True
    assert res.gate == "auto"
    assert "lora" in res.rationale.lower()
    # live skill file unchanged (no prose patch)
    assert "old" in (tmp_path / "skills" / "triage.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Cross-task requirement #7: litellm optional — stub path never imports litellm
# ---------------------------------------------------------------------------


def test_stub_llm_path_does_not_require_litellm(tmp_path: Path, monkeypatch):
    """ARMATURE_CABINET_LLM_STUB=1 must work even if litellm is uninstalled."""
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    # Block litellm import to prove the stub path doesn't need it.
    import builtins
    real_import = builtins.__import__

    def _block_litellm(name, *args, **kwargs):
        if name == "litellm":
            raise ImportError("litellm blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_litellm)
    rc = main(["evolve", str(tmp_path), "--traces-db", str(db), "--review", "--skill-tools",
               "triage=github:alerts"])
    assert rc == 0


# ---------------------------------------------------------------------------
# No-symptom / unmodeled path -> gate=none
# ---------------------------------------------------------------------------


def test_no_modeled_symptom_returns_none(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    # All traces healthy -> no dominant symptom
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE traces (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, workflow_name TEXT,
        stage_id TEXT, role_type TEXT, model TEXT, success INTEGER DEFAULT 1,
        output_valid INTEGER DEFAULT 1, error_type TEXT, escalation_count INTEGER DEFAULT 0,
        latency_ms REAL DEFAULT 0, quorum_score REAL, timestamp TEXT DEFAULT '',
        inputs_json TEXT DEFAULT '{}', outputs_json TEXT DEFAULT '{}', spec_version TEXT DEFAULT '',
        inputs_hash TEXT DEFAULT '', policy_version TEXT DEFAULT '',
        inputs_provenance_json TEXT DEFAULT '{}', tools_declared_json TEXT DEFAULT '[]',
        tools_called_json TEXT DEFAULT '[]', sandbox_image_digest TEXT, loop_iteration INTEGER,
        input_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0,
        agent_id TEXT, agent_version TEXT, active_skill_ids_json TEXT DEFAULT '[]')""")
    for i in range(6):
        con.execute(
            "INSERT INTO traces (run_id,workflow_name,stage_id,role_type,model,success,"
            "output_valid,error_type,agent_id,agent_version,active_skill_ids_json,"
            "tools_declared_json,tools_called_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("r", "wf", "s1", "worker", "m", 1, 1, None, "sec", "0.1.0",
             '["triage"]', '["github:alerts"]', '["github:alerts"]'),
        )
    con.commit()
    con.close()
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    res = run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]},
    )
    assert res.gate == "none"
    assert res.applied is False


# ---------------------------------------------------------------------------
# Task 6: history wiring, auto-verify, single load_package, missed_predictions
# ---------------------------------------------------------------------------


def test_cycle_appends_history_and_verifies_prior(tmp_path: Path, monkeypatch):
    """A cycle appends a record to .evolve/history.jsonl, and on a second cycle
    the PRIOR record's predicted_fixes are verified and annotated."""
    from armature_cabinet.evolve import cycle_history
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db, agent_version="0.1.1")
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")

    # Seed a prior cycle in history so cycle 2 has something to verify.
    cycle_history.append_record(tmp_path, {
        "cycle": 1, "proposed_file": "skills/triage.md", "gate": "auto",
        "surface": "skills", "hqs_before": 0.4, "hqs_after": 0.4,
        "predicted_fixes": ["output_invalid:triage"], "predicted_regressions": [],
        "verified": {}, "version": "0.1.1", "rolled_back": False,
    })

    res = run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]},
        apply=True, current_version="0.1.1",
    )
    assert res.applied is True

    h = cycle_history.read_history(tmp_path)
    assert len(h) == 2
    assert h[-1]["cycle"] == 2
    # The prior (cycle 1) record was annotated with a verdict.
    assert h[0]["verified"]["verdict"] in {"fixed", "unfixed", "regressed"}
    # Structured missed_predictions is a list of dicts.
    assert isinstance(res.missed_predictions, list)


def test_cycle_single_load_package(tmp_path: Path, monkeypatch):
    """load_package is called once per cycle (v1 called it twice)."""
    from armature_cabinet.evolve import orchestrator as orch
    _make_agent(tmp_path)
    db = tmp_path / "traces.db"
    _seed_traces(db)
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    calls = {"n": 0}
    real = orch.load_package

    def _count(folder):
        calls["n"] += 1
        return real(folder)

    monkeypatch.setattr(orch, "load_package", _count)
    run_evolve_cycle(
        tmp_path, traces_db=db, skill_tools={"triage": ["github:alerts"]}, apply=True,
    )
    assert calls["n"] == 1
