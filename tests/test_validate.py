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