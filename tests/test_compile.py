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


def test_description_carries_identity_and_mandate_content():
    desc = compile_agent(load_package(FIX))["role"]["description"]
    assert "Expertise:" in desc
    assert "Temperament:" in desc
    assert "Success looks like:" in desc


def test_x_schema_version_omitted_when_absent(tmp_path):
    (tmp_path / "cabinet.yaml").write_text(
        "id: a\nname: A\nkind: partner\n", encoding="utf-8"
    )
    (tmp_path / "soul.md").write_text("---\nrole: R\n---\nbody\n", encoding="utf-8")
    b = compile_agent(load_package(tmp_path))
    assert "x_schema_version" not in b["role"]


def test_skill_context_resolved_to_x_context():
    b = compile_agent(load_package(FIX))
    entry = b["skill_library"]["appsec.rank-findings"]
    assert "x_context" in entry
    assert "context/severity-rubric.md" in entry["x_context"]
    assert entry["x_context"]["context/severity-rubric.md"].strip()  # body present


def test_skill_extra_passed_through_as_x():
    b = compile_agent(load_package(FIX))
    # rank-findings.md frontmatter has `outputs: Finding[]`
    assert b["skill_library"]["appsec.rank-findings"]["x_outputs"] == "Finding[]"
