# tests/test_evolve_trace_reader.py
import sqlite3
from pathlib import Path
from armature_cabinet.evolve.trace_reader import read_summary


def _seed(db: Path):
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE traces (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, workflow_name TEXT,
        stage_id TEXT, role_type TEXT, model TEXT, input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0, latency_ms REAL DEFAULT 0,
        success INTEGER DEFAULT 1, output_valid INTEGER DEFAULT 1, quorum_score REAL,
        timestamp TEXT, inputs_json TEXT DEFAULT '{}', outputs_json TEXT DEFAULT '{}',
        error_type TEXT, escalation_count INTEGER DEFAULT 0, spec_version TEXT DEFAULT '',
        inputs_hash TEXT DEFAULT '', policy_version TEXT DEFAULT '',
        inputs_provenance_json TEXT DEFAULT '{}', tools_declared_json TEXT DEFAULT '[]',
        tools_called_json TEXT DEFAULT '[]', sandbox_image_digest TEXT, loop_iteration INTEGER,
        agent_id TEXT, agent_version TEXT, active_skill_ids_json TEXT DEFAULT '[]')""")
    rows = [
        ("r1", "wf", "s1", "worker", "m", 1, 1, 100, 1, 0, None, "2026-06-24T10:00:00Z",
         "{}", "{}", "PostconditionFailed", 0, "1", "", "", "{}",
         '["gmail:draft.create"]', '[]', None, None,
         "gmail-reader", "0.2.0", '["draft-reply"]'),
        ("r1", "wf", "s1", "worker", "m", 1, 1, 100, 0, 0, None, "2026-06-24T10:01:00Z",
         "{}", "{}", "ParseError", 0, "1", "", "", "{}",
         '["gmail:draft.create"]', '[]', None, None,
         "gmail-reader", "0.2.0", '["draft-reply"]'),
        ("r1", "wf", "s1", "worker", "m", 1, 1, 100, 1, 1, None, "2026-06-24T10:02:00Z",
         "{}", "{}", None, 0, "1", "", "", "{}",
         '["gmail:messages.list"]', '["gmail:messages.list"]', None, None,
         "gmail-reader", "0.2.0", '["triage-inbox"]'),
    ]
    con.executemany("""INSERT INTO traces (run_id, workflow_name, stage_id, role_type, model,
        input_tokens, output_tokens, latency_ms, success, output_valid, quorum_score, timestamp,
        inputs_json, outputs_json, error_type, escalation_count, spec_version, inputs_hash,
        policy_version, inputs_provenance_json, tools_declared_json, tools_called_json,
        sandbox_image_digest, loop_iteration, agent_id, agent_version, active_skill_ids_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    con.commit()
    con.close()


def test_read_summary_aggregates_per_skill(tmp_path: Path):
    db = tmp_path / "traces.db"
    _seed(db)
    s = read_summary(db, agent_id="gmail-reader", agent_version="0.2.0",
                     skill_tools={"draft-reply": ["gmail:draft.create"],
                                  "triage-inbox": ["gmail:messages.list"]})
    assert s.agent_id == "gmail-reader"
    assert s.agent_version == "0.2.0"
    assert s.n_traces == 3
    assert "draft-reply" in s.per_skill
    assert s.per_skill["draft-reply"].fail_count == 1  # one success=False on draft-reply stage
    assert "OUTPUT_INVALID" in dict(s.dominant_symptoms)


def test_read_summary_unions_tools_called_across_rows(tmp_path: Path):
    """Regression: tools_called must UNION across rows, not overwrite per-row.

    Seeds a skill active in 3 rows where only the FIRST row calls the skill's
    declared tool. The LAST row does NOT call it. With the pre-fix per-row
    overwrite, stats.tools_called would end up as the last row's (empty) set,
    making SkillStats.fired False and dropping the skill from healthy_skills.
    The union fix preserves the earlier call.
    """
    db = tmp_path / "traces.db"
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE traces (
        id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, workflow_name TEXT,
        stage_id TEXT, role_type TEXT, model TEXT, input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0, latency_ms REAL DEFAULT 0,
        success INTEGER DEFAULT 1, output_valid INTEGER DEFAULT 1, quorum_score REAL,
        timestamp TEXT, inputs_json TEXT DEFAULT '{}', outputs_json TEXT DEFAULT '{}',
        error_type TEXT, escalation_count INTEGER DEFAULT 0, spec_version TEXT DEFAULT '',
        inputs_hash TEXT DEFAULT '', policy_version TEXT DEFAULT '',
        inputs_provenance_json TEXT DEFAULT '{}', tools_declared_json TEXT DEFAULT '[]',
        tools_called_json TEXT DEFAULT '[]', sandbox_image_digest TEXT, loop_iteration INTEGER,
        agent_id TEXT, agent_version TEXT, active_skill_ids_json TEXT DEFAULT '[]')""")
    rows = [
        # row 1: skill fires its tool, success
        ("r1", "wf", "s1", "worker", "m", 1, 1, 100, 1, 1, None, "2026-06-24T10:00:00Z",
         "{}", "{}", None, 0, "1", "", "", "{}",
         '["gmail:draft.create"]', '["gmail:draft.create"]', None, None,
         "gmail-reader", "0.2.0", '["draft-reply"]'),
        # row 2: skill active, tool NOT called, but success
        ("r1", "wf", "s1", "worker", "m", 1, 1, 100, 1, 1, None, "2026-06-24T10:01:00Z",
         "{}", "{}", None, 0, "1", "", "", "{}",
         '["gmail:draft.create"]', '[]', None, None,
         "gmail-reader", "0.2.0", '["draft-reply"]'),
        # row 3 (LAST): skill active, tool NOT called, success
        ("r1", "wf", "s1", "worker", "m", 1, 1, 100, 1, 1, None, "2026-06-24T10:02:00Z",
         "{}", "{}", None, 0, "1", "", "", "{}",
         '["gmail:draft.create"]', '[]', None, None,
         "gmail-reader", "0.2.0", '["draft-reply"]'),
    ]
    con.executemany("""INSERT INTO traces (run_id, workflow_name, stage_id, role_type, model,
        input_tokens, output_tokens, latency_ms, success, output_valid, quorum_score, timestamp,
        inputs_json, outputs_json, error_type, escalation_count, spec_version, inputs_hash,
        policy_version, inputs_provenance_json, tools_declared_json, tools_called_json,
        sandbox_image_digest, loop_iteration, agent_id, agent_version, active_skill_ids_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    con.commit(); con.close()

    s = read_summary(db, agent_id="gmail-reader", agent_version="0.2.0",
                     skill_tools={"draft-reply": ["gmail:draft.create"]})
    assert "draft-reply" in s.per_skill
    # The union preserved the row-1 call even though the last row called nothing.
    assert s.per_skill["draft-reply"].fired is True
    assert "gmail:draft.create" in s.per_skill["draft-reply"].tools_called
    # All rows succeeded and the skill fired, so it is healthy.
    assert "draft-reply" in s.healthy_skills


def test_read_summary_marks_heuristic_when_columns_absent(tmp_path: Path):
    db = tmp_path / "traces.db"
    con = sqlite3.connect(db)
    # old schema, no agent_id/agent_version/active_skill_ids_json
    con.execute("""CREATE TABLE traces (
        id INTEGER PRIMARY KEY, run_id TEXT, workflow_name TEXT, stage_id TEXT,
        role_type TEXT, model TEXT, timestamp TEXT DEFAULT '', success INTEGER DEFAULT 1,
        output_valid INTEGER DEFAULT 1, error_type TEXT, escalation_count INTEGER DEFAULT 0,
        latency_ms REAL DEFAULT 0, quorum_score REAL, inputs_json TEXT DEFAULT '{}',
        outputs_json TEXT DEFAULT '{}', tools_declared_json TEXT DEFAULT '[]',
        tools_called_json TEXT DEFAULT '[]')""")
    con.execute("INSERT INTO traces (run_id,workflow_name,stage_id,role_type,model,success,output_valid,error_type) VALUES ('r1','wf','s1','worker','m',0,0,'ParseError')")
    con.commit(); con.close()
    s = read_summary(db, agent_id="gmail-reader", agent_version="0.2.0", skill_tools={})
    assert s.heuristic is True
    assert s.n_traces == 1