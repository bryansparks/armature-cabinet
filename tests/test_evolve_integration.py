# tests/test_evolve_integration.py
"""End-to-end integration test (Task 12) — the evolve loop against the REAL
``gmail-reader`` reference agent + a curated synthetic trace fixture.

Fixture-driven and deterministic: no live LLM (ARMATURE_CABINET_LLM_STUB=1), no real
armature runs. Exercises the full pipeline:

    trace_reader -> router -> surface_gate -> proposer (stubbed LLM)
      -> patch_applier -> versioning -> (verifier next cycle)

Asserts:
  - R1 routes to ``skills/draft-reply.md`` (OUTPUT_INVALID, skill-attributable).
  - A version snapshot is written and round-trips the real folder's subdirs
    (``skills/`` + ``context/``) — the T8 subdir round-trip.
  - ``latest`` advances to the new version on the first cycle (current_hqs=None
    auto-promotes) but does NOT advance when HQS regresses (data-driven
    ``hqs_promote_min`` from ``routing_rules.yaml``).
  - The cycle is reproducible (a second fresh copy produces the same outcome).

Marked ``slow`` so it can be deselected in fast runs: ``pytest -m 'not slow'``.
"""
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
import yaml

from armature_cabinet.cli import main
from armature_cabinet.evolve.versioning import (
    ThresholdPromotionPolicy,
    promote as evolve_promote,
    read_latest,
)

pytestmark = pytest.mark.slow

# The reference agent folder, relative to the repo root.
_AGENT_SRC = Path(__file__).parent.parent / "agents" / "gmail-reader"


def _seed(db: Path, *, agent_version: str = "0.1.0",
          all_failing: bool = False) -> None:
    """Seed a synthetic trace DB that triggers R1 (OUTPUT_INVALID on draft-reply).

    By default (``all_failing=False``): 5 runs, 4 fail OUTPUT_INVALID on the
    ``draft-reply`` skill + 1 healthy on ``triage-inbox``. The attribution
    columns (``agent_id``, ``agent_version``, ``active_skill_ids_json``) are
    populated so the trace reader uses the enriched (non-heuristic) path and
    routes R1 to ``skills/draft-reply.md``. HQS for this mix is ~0.43.

    When ``all_failing=True``: 5 runs ALL failing OUTPUT_INVALID on
    ``draft-reply`` (no healthy run). HQS drops to ~0.30, which is below the
    cycle-1 HQS minus ``hqs_promote_min`` — so the HQS gate must block
    promotion on a second cycle.
    """
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
    # 4 failing runs: OUTPUT_INVALID on draft-reply (tools called, invalid output).
    n_fail = 5 if all_failing else 4
    for _ in range(n_fail):
        con.execute(
            "INSERT INTO traces (run_id, workflow_name, stage_id, role_type, model, "
            "success, output_valid, error_type, agent_id, agent_version, "
            "active_skill_ids_json, tools_declared_json, tools_called_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("r", "wf", "reply", "worker", "m", 0, 0, "ParseError",
             "gmail-reader", agent_version, '["draft-reply"]',
             '["gmail:draft.create"]', '["gmail:draft.create"]'),
        )
    if not all_failing:
        # 1 healthy run on triage-inbox (tools declared + called -> healthy skill).
        con.execute(
            "INSERT INTO traces (run_id, workflow_name, stage_id, role_type, model, "
            "success, output_valid, agent_id, agent_version, active_skill_ids_json, "
            "tools_declared_json, tools_called_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("r", "wf", "triage", "worker", "m", 1, 1, "gmail-reader", agent_version,
             '["triage-inbox"]', '["gmail:messages.list"]', '["gmail:messages.list"]'),
        )
    con.commit()
    con.close()


def _run_cycle(agent: Path, db: Path, monkeypatch) -> int:
    """Drive the real CLI entry against a temp copy of the gmail-reader agent."""
    monkeypatch.setenv("ARMATURE_CABINET_LLM_STUB", "1")
    return main([
        "evolve", str(agent),
        "--traces-db", str(db),
        "--apply",
        "--skill-tools", "draft-reply=gmail:draft.create",
        "--skill-tools", "triage-inbox=gmail:messages.list",
    ])


def _bump_manifest(agent: Path, new_version: str) -> None:
    """Bump the ``version`` field in the agent's cabinet.yaml.

    Simulates the operator advancing the live manifest to the promoted
    version between cycles, so a subsequent cycle produces a distinct
    bumped version (and the trace reader filters traces by the new version).
    """
    cyaml = agent / "cabinet.yaml"
    data = yaml.safe_load(cyaml.read_text(encoding="utf-8"))
    data["version"] = new_version
    cyaml.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False, width=100),
        encoding="utf-8",
    )


def test_evolve_cycle_routes_r1_and_versions(tmp_path: Path, monkeypatch):
    # Copy the REAL reference agent into tmp_path (round-trips subdirs skills/ + context/).
    agent = tmp_path / "gmail-reader"
    shutil.copytree(_AGENT_SRC, agent)
    db = tmp_path / "traces.db"
    _seed(db)

    rc = _run_cycle(agent, db, monkeypatch)
    assert rc == 0

    # R1 routed to skills/draft-reply.md and the stub patched it.
    text = (agent / "skills" / "draft-reply.md").read_text(encoding="utf-8")
    assert "valid JSON" in text

    # A version snapshot was written.
    versions_dir = agent / "versions"
    assert versions_dir.exists()
    snapshots = [v for v in versions_dir.iterdir() if v.name not in ("latest.txt",)
                 and v.is_dir()]
    assert snapshots, "no version snapshot written"
    version_name = snapshots[0].name
    assert version_name == "0.1.1"  # bumped from 0.1.0

    # T8 subdir round-trip: the snapshot contains skills/ + context/ subdirs.
    snap = snapshots[0]
    assert (snap / "skills" / "draft-reply.md").exists()
    assert (snap / "context").is_dir()
    assert any((snap / "context").iterdir())  # context files round-tripped

    # latest advanced to the new version (first cycle: current_hqs=None auto-promotes).
    assert read_latest(agent) == version_name

    # latest does NOT advance when HQS regresses (data-driven hqs_promote_min).
    # A second version with a lower HQS must not promote.
    from armature_cabinet.evolve.versioning import write_version
    write_version(agent, version="0.1.2", hqs=0.01,
                  predicted_fixes=["output_invalid:stub"])
    from armature_cabinet.evolve.router import load_rules
    rules_hqs_min = float(load_rules()["hqs_promote_min"])
    promoted = evolve_promote(
        agent, "0.1.2",
        policy=ThresholdPromotionPolicy(min_gain=rules_hqs_min),
        current_hqs=0.5, new_hqs=0.01,  # regression: new < current
    )
    assert promoted is False
    assert read_latest(agent) == version_name  # latest unchanged

    # The cycle is reproducible: a second fresh copy produces the same outcome.
    agent2 = tmp_path / "gmail-reader-2"
    shutil.copytree(_AGENT_SRC, agent2)
    db2 = tmp_path / "traces2.db"
    _seed(db2)
    rc2 = _run_cycle(agent2, db2, monkeypatch)
    assert rc2 == 0
    text2 = (agent2 / "skills" / "draft-reply.md").read_text(encoding="utf-8")
    assert "valid JSON" in text2
    assert read_latest(agent2) == "0.1.1"
    # Deterministic: patched content matches the first run.
    assert text2 == text


def test_evolve_hqs_gate_blocks_promote_on_regression(tmp_path: Path, monkeypatch):
    """Two --apply cycles through the real CLI/orchestrator path prove the HQS
    gate works end-to-end on the CLI path.

    Cycle 1: no prior version -> current_hqs=None -> ThresholdPromotionPolicy
    auto-promotes; latest advances to 0.1.1.

    Cycle 2: the prior promoted version's HQS (~0.43) is threaded into
    promote() from the CLI (read from .proposal.json). A fresh trace DB with
    a LOWER HQS (~0.30, all-failing) is seeded. ThresholdPromotionPolicy
    returns False (new - current < min_gain), so latest does NOT advance and
    promoted is False. This is the regression that would have occurred had the
    CLI not threaded prior-version HQS into promote().
    """
    agent = tmp_path / "gmail-reader"
    shutil.copytree(_AGENT_SRC, agent)

    # Cycle 1: 4 fail + 1 healthy -> HQS ~0.43, current_hqs=None -> promotes.
    db1 = tmp_path / "traces1.db"
    _seed(db1)  # agent_version="0.1.0"
    rc = _run_cycle(agent, db1, monkeypatch)
    assert rc == 0
    assert read_latest(agent) == "0.1.1"  # first cycle auto-promotes

    # The promoted version's .proposal.json carries the HQS the CLI threads
    # into the next cycle's promote() call.
    proposal = json.loads(
        (agent / "versions" / "0.1.1" / ".proposal.json").read_text(encoding="utf-8")
    )
    prior_hqs = proposal["hqs"]
    assert prior_hqs is not None and prior_hqs > 0.4  # ~0.43

    # Advance the live manifest to the promoted version so cycle 2 bumps to a
    # distinct version (0.1.2) and the trace reader filters by the new version.
    _bump_manifest(agent, "0.1.1")

    # Cycle 2: all 5 traces failing -> HQS ~0.30, below prior_hqs - min_gain.
    # The CLI reads prior_hqs from versions/0.1.1/.proposal.json and passes
    # current_hqs=prior_hqs into run_evolve_cycle -> promote().
    db2 = tmp_path / "traces2.db"
    _seed(db2, agent_version="0.1.1", all_failing=True)
    rc2 = _run_cycle(agent, db2, monkeypatch)
    assert rc2 == 0

    # The new version 0.1.2 snapshot was written (apply succeeded)...
    assert (agent / "versions" / "0.1.2").is_dir()
    # ...but the HQS gate blocked promotion: latest stays 0.1.1.
    assert read_latest(agent) == "0.1.1"
    # The cycle wrote 0.1.2's .proposal.json with the lower HQS.
    proposal2 = json.loads(
        (agent / "versions" / "0.1.2" / ".proposal.json").read_text(encoding="utf-8")
    )
    new_hqs = proposal2["hqs"]
    assert new_hqs < prior_hqs  # regression
    from armature_cabinet.evolve.router import load_rules
    min_gain = float(load_rules()["hqs_promote_min"])
    assert (new_hqs - prior_hqs) < min_gain  # gate correctly blocks
