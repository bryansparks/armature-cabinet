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
