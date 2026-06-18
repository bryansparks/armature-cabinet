from pathlib import Path

from armature_cabinet import load_package, compile_agent, compile_safety_fragment

FIX = Path(__file__).parent / "fixtures" / "incident-comms"


def test_loads_comms_package():
    pkg = load_package(FIX)
    assert pkg.id == "incident-comms"
    assert pkg.kind == "partner"
    assert len(pkg.skills) == 2


def test_compiles_comms_bundle():
    b = compile_agent(load_package(FIX))
    assert b["role"]["name"] == "Incident Comms Partner"
    assert b["role"]["type"] == "worker"
    assert len(b["role"]["skills"]) == 2
    assert set(b["skill_library"]) == set(b["role"]["skills"])
    desc = b["role"]["description"]
    assert "Out of scope" in desc
    assert "cite the evidence" in desc
    assert "Stop and hand back to a human" in desc
    assert "Expertise:" in desc
    assert "Temperament:" in desc
    assert "Success looks like:" in desc


def test_comms_tools_are_non_github():
    b = compile_agent(load_package(FIX))
    tools = b["role"]["tools"]
    assert tools  # non-empty
    assert not any(t.startswith("github:") for t in tools), tools
    assert "slack:conversations.history" in tools
    assert "pagerduty:incidents.get" in tools


def test_comms_skill_context_resolved():
    b = compile_agent(load_package(FIX))
    entry = b["skill_library"]["comms.draft-status-update"]
    assert "x_context" in entry
    assert "context/audience-rubric.md" in entry["x_context"]
    assert entry["x_context"]["context/audience-rubric.md"].strip()


def test_comms_skill_outputs_passed_through():
    b = compile_agent(load_package(FIX))
    assert b["skill_library"]["comms.cadence-plan"]["x_outputs"] == "CadencePlan"
    assert b["skill_library"]["comms.draft-status-update"]["x_outputs"] == "StatusUpdate[]"


def test_comms_safety_fragment_is_advisory():
    f = compile_safety_fragment(load_package(FIX))
    blocked = {r["tool"] for r in f.get("safety", [])}
    assert "slack:post" in blocked and "email:send" in blocked
    assert f["contracts"]["max_iterations"] == 8
    assert "_note" in f