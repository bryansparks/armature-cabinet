"""LoRA handoff: decide-in-evolve, train-via-CLI. Mirrors team.run_workflow's
subprocess pattern. Cabinet never imports armature; only shells out.
"""
import shutil
import subprocess

import pytest

from armature_cabinet.evolve.lora_handoff import (
    build_adapter_command,
    decide_lora,
    handoff_to_adapter,
)
from armature_cabinet.evolve.types import AgentTraceSummary, SkillStats


def _summary(symptoms, skills):
    return AgentTraceSummary(
        agent_id="a",
        agent_version="0.2",
        n_traces=5,
        output_valid_rate=0.4,
        success_rate=0.4,
        quorum=0.5,
        escalation_rate=0.2,
        hqs=0.5,
        dominant_symptoms=symptoms,
        per_skill=skills,
    )


def test_decide_lora_when_prose_failed_and_tools_right():
    # tools_called right but outputs wrong -> LoRA-eligible
    s = _summary(
        [("LOW_SKILL_ACTIVATION", 5)],
        {
            "draft-reply": SkillStats(
                "draft-reply",
                tools_declared=["gmail:draft.create"],
                tools_called=["gmail:draft.create"],
            )
        },
    )
    rec = decide_lora(s, prose_cycles_without_gain=2, skill_id="draft-reply")
    assert rec.eligible is True
    assert rec.skill_id == "draft-reply"


def test_decide_lora_not_eligible_when_prose_still_helping():
    s = _summary(
        [("LOW_SKILL_ACTIVATION", 5)],
        {"draft-reply": SkillStats("draft-reply", tools_declared=["x"], tools_called=["x"])},
    )
    rec = decide_lora(s, prose_cycles_without_gain=0, skill_id="draft-reply")
    assert rec.eligible is False


def test_decide_lora_not_eligible_when_tools_misfiring():
    # tools declared but never called -> not eligible (text edit may fix tool wiring)
    s = _summary(
        [("LOW_SKILL_ACTIVATION", 5)],
        {
            "draft-reply": SkillStats(
                "draft-reply", tools_declared=["gmail:draft.create"], tools_called=[]
            )
        },
    )
    rec = decide_lora(s, prose_cycles_without_gain=3, skill_id="draft-reply")
    assert rec.eligible is False


def test_decide_lora_not_eligible_when_skill_absent():
    s = _summary([("LOW_SKILL_ACTIVATION", 5)], {})
    rec = decide_lora(s, prose_cycles_without_gain=5, skill_id="missing")
    assert rec.eligible is False
    assert "not in trace" in rec.rationale


def test_build_adapter_command_shape():
    cmd = build_adapter_command(
        skill_id="draft-reply", role_type="worker", min_score=0.7, continual_learning=True
    )
    assert cmd[:4] == ["armature", "adapter", "create", "draft-reply"]
    assert "--from-traces" in cmd
    assert "--min-score" in cmd and "0.7" in cmd
    assert "--continual-learning" in cmd


def test_build_adapter_command_without_continual_learning():
    cmd = build_adapter_command(
        skill_id="draft-reply", role_type="worker", min_score=0.65, continual_learning=False
    )
    assert "--continual-learning" not in cmd
    assert "0.65" in cmd


def test_handoff_raises_when_armature_missing(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(Exception):
        handoff_to_adapter(skill_id="draft-reply", role_type="worker")


def test_handoff_dry_run_does_not_shell_out(monkeypatch):
    # dry_run must build the command but never invoke subprocess.run
    monkeypatch.setattr(shutil, "which", lambda _: "/fake/armature")
    called = []

    def _fail(*a, **k):
        called.append((a, k))
        raise AssertionError("subprocess.run must not be called in dry_run")

    monkeypatch.setattr(subprocess, "run", _fail)
    result = handoff_to_adapter(
        skill_id="draft-reply", role_type="worker", dry_run=True
    )
    assert called == []
    assert result.dry_run is True
    assert result.trained is False
    assert result.command[:4] == ["armature", "adapter", "create", "draft-reply"]
    assert "--from-traces" in result.command


def test_handoff_shells_out_with_correct_command(monkeypatch):
    # Non-dry-run shells out with capture_output=True, text=True, check=False
    monkeypatch.setattr(shutil, "which", lambda _: "/fake/armature")
    captured = {}

    class _FakeCompleted:
        returncode = 0
        stdout = "trained"
        stderr = ""

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        captured["kwargs"] = kwargs
        return _FakeCompleted()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    result = handoff_to_adapter(skill_id="draft-reply", role_type="worker")
    assert result.command == captured["cmd"]
    assert "--from-traces" in result.command
    assert "--role-type" in result.command and "worker" in result.command
    assert result.returncode == 0
    assert result.trained is True
    # Mirror team.py subprocess flags (enhanced with capture/text per task spec)
    assert captured["kwargs"].get("capture_output") is True
    assert captured["kwargs"].get("text") is True
    assert captured["kwargs"].get("check") is False


def test_handoff_under_threshold_falls_back_to_prose(monkeypatch):
    # Non-zero returncode -> trained=False (orchestrator falls back to prose)
    monkeypatch.setattr(shutil, "which", lambda _: "/fake/armature")

    class _FakeCompleted:
        returncode = 1
        stdout = ""
        stderr = "under threshold"

    monkeypatch.setattr(subprocess, "run", lambda cmd, **k: _FakeCompleted())
    result = handoff_to_adapter(skill_id="draft-reply", role_type="worker")
    assert result.trained is False
    assert result.returncode == 1
