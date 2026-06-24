# src/armature_cabinet/evolve/trace_reader.py
"""Read Armature run traces for a Cabinet agent. Direct sqlite read of
~/.armature/traces.db — a file read, NOT an armature code import (boundary preserved).

Degrades gracefully when the attribution columns are absent (pre-enrichment traces):
sets summary.heuristic = True and routes stage-level.
"""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any

from .types import AgentTraceSummary, SkillStats

DEFAULT_DB = Path.home() / ".armature" / "traces.db"

# symptoms we model, derived from the error_type / output_valid columns
_SYM_INVALID = "OUTPUT_INVALID"
_SYM_REFUSAL = "REFUSAL_OR_FALSE_HALT"
_SYM_LOW_SKILL = "LOW_SKILL_ACTIVATION"


def _has_column(con: sqlite3.Connection, col: str) -> bool:
    cols = {row[1] for row in con.execute("PRAGMA table_info(traces)")}
    return col in cols


def read_summary(db_path: Path | str, *, agent_id: str, agent_version: str | None,
                 skill_tools: dict[str, list[str]] | None = None,
                 min_traces: int = 1) -> AgentTraceSummary | None:
    skill_tools = skill_tools or {}
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        enriched = _has_column(con, "agent_id")
        select = "SELECT * FROM traces"
        if enriched:
            select += " WHERE agent_id = ?"
            params: tuple[Any, ...] = (agent_id,)
            if agent_version is not None:
                select += " AND agent_version = ?"
                params = (*params, agent_version)
            rows = con.execute(select, params).fetchall()
        else:
            rows = con.execute(select).fetchall()
    finally:
        con.close()

    if len(rows) < min_traces:
        return None

    n = len(rows)
    per_skill: dict[str, SkillStats] = {}
    symptom_counts: dict[str, int] = {}
    successes = 0
    valid = 0
    escalations = 0
    quorums: list[float] = []
    latencies: list[float] = []
    evidence: list[int] = []

    for r in rows:
        rid = r["id"]
        evidence.append(rid)
        ok = bool(r["success"])
        ov = bool(r["output_valid"]) if "output_valid" in r.keys() else True
        successes += int(ok)
        valid += int(ov)
        esc = r["escalation_count"] if "escalation_count" in r.keys() else 0
        escalations += esc
        if r["quorum_score"] is not None:
            quorums.append(float(r["quorum_score"]))
        latencies.append(float(r["latency_ms"] or 0.0))

        tools_called = json.loads(r["tools_called_json"] or "[]")
        active = json.loads(r["active_skill_ids_json"] or "[]") if enriched else []
        for sid in active:
            stats = per_skill.setdefault(sid, SkillStats(sid))
            stats.tools_declared = list(skill_tools.get(sid, []))
            stats.tools_called = list(set(stats.tools_called) | set(tools_called))
            if not ok:
                stats.fail_count += 1
            stats.escalation += esc

        err = r["error_type"] if "error_type" in r.keys() else None
        if not ov:
            symptom_counts[_SYM_INVALID] = symptom_counts.get(_SYM_INVALID, 0) + 1
        if err == "Refusal" or (err and "halt" in err.lower()):
            symptom_counts[_SYM_REFUSAL] = symptom_counts.get(_SYM_REFUSAL, 0) + 1
        # LOW_SKILL_ACTIVATION: a skill attached but none of its tools called
        for sid in active:
            if skill_tools.get(sid) and not set(skill_tools[sid]) & set(tools_called):
                symptom_counts[_SYM_LOW_SKILL] = symptom_counts.get(_SYM_LOW_SKILL, 0) + 1

    avg_quorum = sum(quorums) / len(quorums) if quorums else 0.5
    latency_score = max(0.0, 1.0 - (sum(latencies) / n) / 5000.0)
    hfr = sum(1 for r in rows if (r["escalation_count"] if "escalation_count" in r.keys() else 0) == 0) / n
    hqs = 0.35 * (valid / n) + 0.25 * (successes / n) + 0.20 * avg_quorum + 0.10 * latency_score + 0.10 * hfr

    # per-skill output_valid_rate: approximation = stage valid where skill was active
    # (precise per-skill validity needs per-skill error tagging; v1 uses stage-level)
    for sid, st in per_skill.items():
        st.output_valid_rate = max(0.0, 1.0 - (st.fail_count / max(1, n)))

    dominant = sorted(symptom_counts.items(), key=lambda kv: -kv[1])
    healthy = [sid for sid, st in per_skill.items() if st.fail_count == 0 and st.fired]

    return AgentTraceSummary(
        agent_id=agent_id, agent_version=agent_version, n_traces=n,
        output_valid_rate=valid / n, success_rate=successes / n,
        quorum=avg_quorum, escalation_rate=escalations / n, hqs=hqs,
        per_skill=per_skill, dominant_symptoms=dominant,
        healthy_skills=healthy, evidence_row_ids=evidence, heuristic=not enriched,
    )
