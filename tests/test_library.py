import yaml

from armature_cabinet.library import list_agents, build_all
from armature_cabinet.scaffold import build_folder


def _lib(tmp_path):
    """A library with two agents + a non-agent subdir."""
    lib = tmp_path / "agents"
    lib.mkdir()
    build_folder({"id": "alpha", "kind": "partner", "role": "Alpha", "skills": []}, lib)
    build_folder({"id": "beta", "kind": "partner", "role": "Beta", "skills": []}, lib)
    (lib / "not-an-agent").mkdir()
    (lib / "not-an-agent" / "readme.txt").write_text("ignore me")
    return lib


def test_list_agents_enumerates_and_skips_non_agents(tmp_path):
    rows = list_agents(_lib(tmp_path))
    assert [r["id"] for r in rows] == ["alpha", "beta"]  # sorted; non-agent skipped
    assert rows[0]["name"] == "alpha" and rows[0]["kind"] == "partner"
    assert rows[0]["skills"] == 0 and rows[0]["valid"] is True


def test_list_agents_reports_invalid_without_raising(tmp_path):
    lib = tmp_path / "agents"
    lib.mkdir()
    (lib / "broken").mkdir()
    (lib / "broken" / "cabinet.yaml").write_text(
        "id: broken\nname: Broken\nkind: partner\nschema_version: '0.1.0'\n")
    (lib / "broken" / "soul.md").write_text("---\nrole: R\n---\nbody\n")
    (lib / "broken" / "skills").mkdir()
    (lib / "broken" / "skills" / "a.md").write_text("---\nid: dup\n---\nb\n")
    (lib / "broken" / "skills" / "b.md").write_text("---\nid: dup\n---\nb\n")
    rows = list_agents(lib)
    assert len(rows) == 1 and rows[0]["id"] == "broken"
    assert rows[0]["valid"] is False
    assert any("duplicate" in e for e in rows[0]["errors"])


def test_build_all_compiles_each_agent(tmp_path):
    out = tmp_path / "dist"
    bundles, errors = build_all(_lib(tmp_path), out)
    assert not errors and len(bundles) == 2
    for b in bundles:
        assert b.exists()
        bundle = yaml.safe_load(b.read_text())
        assert "role" in bundle and "skill_library" in bundle


def test_build_all_skips_non_agent_and_continues_on_failure(tmp_path):
    lib = tmp_path / "agents"
    lib.mkdir()
    build_folder({"id": "good", "kind": "partner", "role": "G", "skills": []}, lib)
    (lib / "bad").mkdir()
    (lib / "bad" / "cabinet.yaml").write_text("id: bad\nname: Bad\nkind: weird\n")  # invalid kind
    (lib / "bad" / "soul.md").write_text("---\nrole: R\n---\nbody\n")
    out = tmp_path / "dist"
    bundles, errors = build_all(lib, out)
    assert len(bundles) == 1 and bundles[0].name == "agent.yaml"  # good compiled
    assert len(errors) == 1 and "bad" in errors[0]
    assert not (out / "bad").exists()  # bad not compiled
