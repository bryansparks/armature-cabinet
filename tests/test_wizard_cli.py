from armature_cabinet.cli import main
import armature_cabinet.prompts as prompts
from armature_cabinet import load_package, validate_package


def _full_answers():
    return {
        "id": "wiz-demo", "name": "Wiz Demo", "kind": "partner",
        "summary": "wizard smoke", "schema_version": "0.1.0",
        "role": "Demo", "expertise": [], "temperament": "", "standards": [],
        "refusals": [], "soul_body": "", "armature_role_type": None,
        "goal": "", "success_looks_like": [], "out_of_scope": [], "mandate_body": "",
        "brakes": None, "trust": None,
        "skills": [{"id": "wiz.s", "name": "s", "when": "w", "tools": [],
                     "context": [], "cost_tier": None, "version": "0.1.0",
                     "outputs": None, "body": "do"}],
    }


def test_new_writes_valid_folder(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(prompts, "collect_answers", lambda id_: _full_answers())
    rc = main(["new", "wiz-demo", "--out", str(tmp_path)])
    assert rc == 0
    root = tmp_path / "wiz-demo"
    assert (root / "cabinet.yaml").exists()
    assert (root / "skills" / "s.md").exists()
    assert validate_package(load_package(root)).ok
    out = capsys.readouterr().out
    assert "created" in out.lower() and "wiz-demo" in out
