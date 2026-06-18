from pathlib import Path

from armature_cabinet import load_package, compile_agent, compile_safety_fragment

FIX = Path(__file__).parent / "fixtures" / "security-triage"


def test_loads_package():
    pkg = load_package(FIX)
    assert pkg.id == "security-triage"
    assert pkg.kind == "partner"
    assert len(pkg.skills) == 3


def test_compiles_bundle():
    b = compile_agent(load_package(FIX))
    assert b["role"]["name"] == "Security Triage Partner"
    assert b["role"]["type"] == "worker"
    assert len(b["role"]["skills"]) == 3
    assert "github:dependabot.list_alerts" in b["role"]["tools"]
    assert set(b["skill_library"]) == set(b["role"]["skills"])
    # brakes + trust folded into prose as behavioral instruction
    desc = b["role"]["description"]
    assert "Out of scope" in desc
    assert "cite the evidence" in desc
    assert "Stop and hand back to a human" in desc


def test_compile_time_skill_selection():
    b = compile_agent(load_package(FIX), include=["appsec.rank-findings"])
    assert b["role"]["skills"] == ["appsec.rank-findings"]
    assert set(b["skill_library"]) == {"appsec.rank-findings"}


def test_thick_metadata_preserved():
    b = compile_agent(load_package(FIX))
    entry = b["skill_library"]["appsec.triage-secret-scanning"]
    assert entry["x_cost_tier"] == "T1"
    assert "github:secret-scanning.list_alerts" in entry["x_tools"]


def test_safety_fragment_is_advisory_hard_enforcement():
    f = compile_safety_fragment(load_package(FIX))
    blocked = {r["tool"] for r in f.get("safety", [])}
    assert "merge_pr" in blocked and "write_to_repo" in blocked
    assert f["contracts"]["max_iterations"] == 10
    assert "_note" in f  # carries the "merge this in by hand" advisory
