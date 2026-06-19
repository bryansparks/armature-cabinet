import pytest

from armature_cabinet import load_package, validate_package, compile_agent
from armature_cabinet.scaffold import build_folder, slugify


def _full_answers():
    return {
        "id": "demo-agent", "name": "Demo Agent", "kind": "partner",
        "summary": "A demo agent.", "schema_version": "0.1.0",
        "role": "Demo specialist", "expertise": ["alpha", "beta"],
        "temperament": "calm", "standards": ["be clear"],
        "refusals": ["never lie"], "soul_body": "You are a demo agent.",
        "armature_role_type": None,
        "goal": "Demo things well.", "success_looks_like": ["x done"],
        "out_of_scope": ["y"], "mandate_body": "Because demos.",
        "brakes": {"cost_ceiling_usd": 1.0, "max_iterations": 5,
                   "forbidden_actions": ["slack:post"], "halt_and_ask_when": ["unsure"], "body": ""},
        "trust": {"show_work": "required", "cite_sources": "required",
                  "uncertainty": "must_flag", "escalate_when": ["conf<0.6"]},
        "skills": [
            {"id": "demo.do-thing", "name": "do-thing", "when": "A thing needs doing.",
             "tools": ["tool:run"], "context": ["context/rubric.md"], "cost_tier": "T2",
             "version": "0.1.0", "outputs": "Result[]", "body": "1. Do the thing."},
        ],
    }


def test_slugify():
    assert slugify("Do The Thing!") == "do-the-thing"
    assert slugify("appsec.rank-findings") == "appsec.rank-findings"
    assert slugify("   ") == "skill"


def test_build_full_folder_validates_and_compiles(tmp_path):
    root = build_folder(_full_answers(), tmp_path)
    assert root == tmp_path / "demo-agent"
    for f in ["cabinet.yaml", "soul.md", "mandate.md", "brakes.md", "trust.yaml",
              "skills/do-thing.md", "context/rubric.md", "README.md"]:
        assert (root / f).exists(), f
    pkg = load_package(root)
    assert pkg.id == "demo-agent" and pkg.kind == "partner" and len(pkg.skills) == 1
    r = validate_package(pkg)
    assert r.ok, r.errors
    b = compile_agent(pkg)
    assert b["role"]["name"] == "Demo Agent"
    assert b["role"]["skills"] == ["demo.do-thing"]
    assert "rubric" in b["skill_library"]["demo.do-thing"]["x_context"]["context/rubric.md"]
    assert b["skill_library"]["demo.do-thing"]["x_outputs"] == "Result[]"


def test_build_minimal_folder_validates_and_compiles(tmp_path):
    root = build_folder({"id": "min", "kind": "partner", "role": "Minimal", "skills": []}, tmp_path)
    pkg = load_package(root)
    assert pkg.id == "min" and pkg.skills == []
    assert validate_package(pkg).ok
    b = compile_agent(pkg)
    assert b["role"]["skills"] == [] and b["skill_library"] == {}


def test_omitted_blocks_produce_no_file(tmp_path):
    root = build_folder({"id": "nobrakes", "kind": "partner", "role": "R",
                          "brakes": None, "trust": None, "skills": []}, tmp_path)
    assert not (root / "brakes.md").exists()
    assert not (root / "trust.yaml").exists()
    assert not (root / "mandate.md").exists()  # no mandate fields -> none written
    assert validate_package(load_package(root)).ok


def test_no_skills_creates_no_skills_or_context_dir(tmp_path):
    root = build_folder({"id": "noskills", "kind": "partner", "role": "R", "skills": []}, tmp_path)
    assert not (root / "skills").exists()
    assert not (root / "context").exists()


def test_existing_folder_raises(tmp_path):
    build_folder({"id": "x", "kind": "partner", "role": "R", "skills": []}, tmp_path)
    with pytest.raises(FileExistsError):
        build_folder({"id": "x", "kind": "partner", "role": "R", "skills": []}, tmp_path)


def test_context_stub_created_for_ref(tmp_path):
    root = build_folder({"id": "c", "kind": "partner", "role": "R",
        "skills": [{"id": "c.s", "name": "s", "when": "w", "tools": [], "context": ["context/r.md"],
                    "cost_tier": None, "version": "0.1.0", "outputs": None, "body": "b"}]}, tmp_path)
    assert "TODO" in (root / "context" / "r.md").read_text()
    assert validate_package(load_package(root)).ok


def test_brakes_confirmed_but_empty_writes_no_brakes(tmp_path):
    root = build_folder({"id": "eb", "kind": "partner", "role": "R",
        "brakes": {"cost_ceiling_usd": None, "max_iterations": None,
                   "forbidden_actions": [], "halt_and_ask_when": [], "body": ""},
        "trust": None, "skills": []}, tmp_path)
    assert not (root / "brakes.md").exists()
    assert validate_package(load_package(root)).ok


def test_trust_all_none_writes_no_trust(tmp_path):
    root = build_folder({"id": "et", "kind": "partner", "role": "R", "brakes": None,
        "trust": {"show_work": None, "cite_sources": None, "uncertainty": None, "escalate_when": []},
        "skills": []}, tmp_path)
    assert not (root / "trust.yaml").exists()
    assert validate_package(load_package(root)).ok
