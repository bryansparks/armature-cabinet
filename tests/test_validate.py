from pathlib import Path

import pytest

from armature_cabinet.errors import CabinetError
from armature_cabinet.loader import load_package

FIX = Path(__file__).parent / "fixtures" / "security-triage"


def _write(folder, files):
    for name, text in files.items():
        p = folder / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def test_missing_folder_raises_cabinet_error():
    with pytest.raises(CabinetError):
        load_package("/tmp/does-not-exist-xyz-abc")


def test_missing_cabinet_yaml_raises_cabinet_error(tmp_path):
    (tmp_path / "soul.md").write_text("---\nrole: R\n---\nbody\n", encoding="utf-8")
    with pytest.raises(CabinetError):
        load_package(tmp_path)


def test_malformed_frontmatter_raises_cabinet_error(tmp_path):
    _write(tmp_path, {
        "cabinet.yaml": "id: a\nname: A\nkind: partner\n",
        "soul.md": "---\nrole: [unterminated\n---\nbody\n",
    })
    with pytest.raises(CabinetError):
        load_package(tmp_path)


def test_context_keyed_by_path_relative_to_root():
    pkg = load_package(FIX)
    assert "context/severity-rubric.md" in pkg.context
    assert "context/finding-schema.md" in pkg.context
    assert pkg.context["context/severity-rubric.md"].strip()  # non-empty body


from armature_cabinet.validate import validate_package


def _valid_files():
    return {
        "cabinet.yaml": "id: a\nname: A\nkind: partner\nschema_version: '0.1.0'\n",
        "soul.md": "---\nrole: R\n---\nbody\n",
        "skills/s.md": "---\nid: s\n---\nbody\n",
    }


def test_valid_package_has_no_errors(tmp_path):
    _write(tmp_path, _valid_files())
    r = validate_package(load_package(tmp_path))
    assert r.ok, r.errors


def test_missing_id_is_error(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "name: A\nkind: partner\nschema_version: '0.1.0'\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert any("missing required 'id'" in e for e in r.errors)


def test_missing_name_warns_but_ok(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "id: a\nkind: partner\nschema_version: '0.1.0'\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert r.ok
    assert any("'name'" in w for w in r.warnings)


def test_invalid_kind_is_error(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "id: a\nname: A\nkind: weird\nschema_version: '0.1.0'\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert any("invalid kind" in e for e in r.errors)


def test_missing_kind_warns(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "id: a\nname: A\nschema_version: '0.1.0'\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert r.ok
    assert any("'kind'" in w for w in r.warnings)


def test_missing_schema_version_warns(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "id: a\nname: A\nkind: partner\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert r.ok
    assert any("schema_version" in w for w in r.warnings)


def test_duplicate_skill_id_is_error(tmp_path):
    files = _valid_files()
    files["skills/y.md"] = "---\nid: s\n---\nbody\n"  # same id as s.md
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert any("duplicate" in e for e in r.errors)


def test_bogus_include_skill_is_error(tmp_path):
    _write(tmp_path, _valid_files())
    r = validate_package(load_package(tmp_path), include=["nope"])
    assert any("nope" in e for e in r.errors)


def test_dangling_context_ref_is_error(tmp_path):
    files = _valid_files()
    files["skills/s.md"] = "---\nid: s\ncontext:\n  - context/missing.md\n---\nbody\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert any("context/missing.md" in e for e in r.errors)


from armature_cabinet.cli import main


def test_build_missing_folder_returns_1_no_traceback(capsys):
    rc = main(["build", "/tmp/does-not-exist-xyz-abc"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "Traceback" not in err


def test_build_bogus_skill_returns_1(capsys):
    rc = main(["build", str(FIX), "-o", "/tmp/out-bogus", "--skill", "nope"])
    assert rc == 1
    assert "nope" in capsys.readouterr().err


def test_validate_clean_returns_0(capsys):
    rc = main(["validate", str(FIX)])
    assert rc == 0
    assert "ok" in capsys.readouterr().out.lower()


def test_validate_dup_id_returns_1(tmp_path, capsys):
    _write(tmp_path, {
        "cabinet.yaml": "id: a\nname: A\nkind: partner\nschema_version: '0.1.0'\n",
        "soul.md": "---\nrole: R\n---\nbody\n",
        "skills/x.md": "---\nid: dup\n---\nb\n",
        "skills/y.md": "---\nid: dup\n---\nb\n",
    })
    rc = main(["validate", str(tmp_path)])
    assert rc == 1
    assert "duplicate" in capsys.readouterr().err


def test_non_str_id_is_error(tmp_path):
    _write(tmp_path, {
        "cabinet.yaml": "id:\n  - 1\n  - 2\nname: A\nkind: partner\nschema_version: '0.1.0'\n",
        "soul.md": "---\nrole: R\n---\nbody\n",
        "skills/s.md": "---\nid: s\n---\nbody\n",
    })
    r = validate_package(load_package(tmp_path))
    assert any("non-empty string" in e for e in r.errors)


import yaml


def test_build_with_when_selects_matching_skills(tmp_path):
    out = tmp_path / "out"
    rc = main(["build", str(FIX), "--when",
               "prioritize open Dependabot alerts", "-o", str(out)])
    assert rc == 0
    bundle = yaml.safe_load((out / "agent.yaml").read_text())
    assert bundle["role"]["skills"] == [
        "appsec.triage-dependabot-alerts", "appsec.triage-secret-scanning"]


def test_build_when_and_skill_mutually_exclusive(capsys):
    rc = main(["build", str(FIX), "--when", "alerts", "--skill", "appsec.rank-findings"])
    assert rc == 1
    assert "mutually exclusive" in capsys.readouterr().err.lower()


def test_build_when_no_match_warns_and_builds_zero_skills(tmp_path, capsys):
    out = tmp_path / "out"
    rc = main(["build", str(FIX), "--when", "quantum entanglement", "-o", str(out)])
    assert rc == 0
    assert "no skills matched" in capsys.readouterr().err.lower()
    bundle = yaml.safe_load((out / "agent.yaml").read_text())
    assert bundle["role"]["skills"] == []
    assert bundle["skill_library"] == {}


def test_validate_when_previews_matched_skills(capsys):
    rc = main(["validate", str(FIX), "--when",
               "prioritize open Dependabot alerts"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "matched 2 skill(s)" in out
    assert "appsec.triage-dependabot-alerts" in out
