from pathlib import Path

import pytest

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


def test_safety_fragment_is_advisory_only():
    f = compile_safety_fragment(load_package(FIX))
    assert "safety" not in f  # block rules moved to the bundle
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


def test_grabbed_skill_md_description_becomes_skilldef_description(tmp_path):
    """A grabbed SKILL.md (name + description + body, no id) compiles with the
    description as the SkillDef.description — not as x_description (extra)."""
    (tmp_path / "cabinet.yaml").write_text(
        "id: t\nname: T\nkind: partner\nschema_version: '0.1.0'\n")
    (tmp_path / "soul.md").write_text("---\nrole: R\n---\nbody\n")
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "grabbed.md").write_text(
        "---\nname: grabbed-skill\ndescription: A skill grabbed from the wild.\n---\nDo the thing.\n")
    b = compile_agent(load_package(tmp_path))
    entry = b["skill_library"]["grabbed-skill"]  # id falls back to name
    assert entry["description"] == "A skill grabbed from the wild."
    assert "x_description" not in entry  # description is a known field, not extra


def test_compile_emits_safety_rules():
    pkg = load_package(FIX)
    b = compile_agent(pkg)
    forbidden = list(pkg.brakes.get("forbidden_actions") or [])
    assert forbidden, "fixture should have forbidden_actions"
    rules = b.get("safety_rules")
    assert rules, "bundle should carry safety_rules when forbidden_actions is set"
    assert len(rules) == len(forbidden)
    assert {r["tool"] for r in rules} == set(forbidden)
    for r in rules:
        assert r["action"] == "block"
        assert r["condition"] is None  # None = matches every call (not the old truthy hack)


def test_compile_partner_without_forbidden_has_no_safety_rules(tmp_path):
    (tmp_path / "cabinet.yaml").write_text("id: a\nname: A\nkind: partner\n", encoding="utf-8")
    (tmp_path / "soul.md").write_text("---\nrole: R\n---\nbody\n", encoding="utf-8")
    b = compile_agent(load_package(tmp_path))
    assert "safety_rules" not in b


def test_compile_clone_no_brakes_raises(tmp_path):
    from armature_cabinet.errors import CabinetError
    root = tmp_path / "clone-agent"
    root.mkdir()
    (root / "cabinet.yaml").write_text("id: clone-agent\nname: Clone\nkind: clone\n", encoding="utf-8")
    (root / "soul.md").write_text("---\nrole: R\n---\nbody\n", encoding="utf-8")
    with pytest.raises(CabinetError, match="forbidden_actions"):
        compile_agent(load_package(root))


def test_compile_clone_with_brakes_emits_safety_rules(tmp_path):
    """A clone WITH forbidden_actions compiles and emits safety_rules — the
    symmetric positive path to test_compile_clone_no_brakes_raises."""
    root = tmp_path / "clone-with-brakes"
    root.mkdir()
    (root / "cabinet.yaml").write_text(
        "id: clone-with-brakes\nname: Clone\nkind: clone\n", encoding="utf-8")
    (root / "soul.md").write_text("---\nrole: R\n---\nbody\n", encoding="utf-8")
    (root / "brakes.md").write_text(
        "---\nforbidden_actions:\n  - send_email\n---\nHard brakes.\n",
        encoding="utf-8")
    b = compile_agent(load_package(root))
    rules = b["safety_rules"]
    assert len(rules) == 1
    assert rules[0]["tool"] == "send_email"
    assert rules[0]["condition"] is None  # None = matches every call
    assert rules[0]["action"] == "block"
    desc = b["role"]["description"]
    assert "never take these actions: send_email" in desc
