import shutil
from pathlib import Path

import pytest
import yaml

from armature_cabinet.cli import main
from armature_cabinet.errors import CabinetError
from armature_cabinet.library import build_all
from armature_cabinet.scaffold import build_folder
from armature_cabinet.team import generate_workflow, run_workflow

FIX = Path(__file__).parent / "fixtures"


def test_generate_workflow_structure(tmp_path):
    wf = generate_workflow(["a", "b"], tmp_path / "dist", "lib-team")
    assert wf["name"] == "lib-team"
    assert wf["version"] == "1.0"
    assert wf["model_tiers"]["small"]["model"] == "claude-haiku-4-5-20251001"
    assert wf["role_type_defaults"] == {"worker": "small", "orchestrator": "small", "judge": "small", "researcher": "small"}
    assert set(wf["agent_library"]) == {"a", "b"}
    assert wf["agent_library"]["a"]["path"] == str((tmp_path / "dist" / "a" / "agent.yaml").resolve())
    stages = wf["stages"]
    assert stages[0] == {"id": "a", "agent": "a", "output_mode": "text", "depends_on": []}
    assert stages[1] == {"id": "b", "agent": "b", "output_mode": "text", "depends_on": ["a"]}


def test_generate_workflow_single_agent(tmp_path):
    wf = generate_workflow(["only"], tmp_path / "dist", "t")
    assert len(wf["stages"]) == 1
    assert wf["stages"][0]["depends_on"] == []


def test_run_workflow_raises_if_armature_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _x: None)
    with pytest.raises(CabinetError, match="armature CLI not found"):
        run_workflow(Path("/tmp/nope.yml"), dry_run=True)


def _build_lib(tmp_path):
    lib = tmp_path / "agents"
    lib.mkdir()
    build_folder({"id": "a", "kind": "partner", "role": "A", "skills": []}, lib)
    build_folder({"id": "b", "kind": "partner", "role": "B", "skills": []}, lib)
    dist = tmp_path / "dist"
    build_all(lib, dist)
    return lib, dist


def test_cli_team_writes_workflow(tmp_path):
    lib, dist = _build_lib(tmp_path)
    wf = tmp_path / "team.yml"
    rc = main(["team", str(lib), "--bundles", str(dist), "--out", str(wf)])
    assert rc == 0
    spec = yaml.safe_load(wf.read_text())
    assert set(spec["agent_library"]) == {"a", "b"}
    assert [s["id"] for s in spec["stages"]] == ["a", "b"]  # alphabetical default
    assert spec["stages"][1]["depends_on"] == ["a"]


def test_cli_team_agent_order(tmp_path):
    lib, dist = _build_lib(tmp_path)
    wf = tmp_path / "team.yml"
    rc = main(["team", str(lib), "--agent", "b", "--agent", "a",
               "--bundles", str(dist), "--out", str(wf)])
    assert rc == 0
    spec = yaml.safe_load(wf.read_text())
    assert [s["id"] for s in spec["stages"]] == ["b", "a"]  # given order


def test_cli_team_missing_bundle_errors(tmp_path):
    lib = tmp_path / "agents"
    lib.mkdir()
    build_folder({"id": "a", "kind": "partner", "role": "A", "skills": []}, lib)
    rc = main(["team", str(lib), "--bundles", str(tmp_path / "empty"),
               "--out", str(tmp_path / "t.yml")])
    assert rc == 1
    assert not (tmp_path / "t.yml").exists()  # not written on error


def test_cli_team_unknown_agent_errors(tmp_path):
    lib, dist = _build_lib(tmp_path)
    rc = main(["team", str(lib), "--agent", "nope",
               "--bundles", str(dist), "--out", str(tmp_path / "t.yml")])
    assert rc == 1


def test_cli_team_dry_run_and_run_mutually_exclusive(tmp_path):
    lib, dist = _build_lib(tmp_path)
    rc = main(["team", str(lib), "--dry-run", "--run",
               "--bundles", str(dist), "--out", str(tmp_path / "t.yml")])
    assert rc == 1


def test_cli_team_duplicate_agent_errors(tmp_path):
    lib, dist = _build_lib(tmp_path)
    rc = main(["team", str(lib), "--agent", "a", "--agent", "a",
               "--bundles", str(dist), "--out", str(tmp_path / "t.yml")])
    assert rc == 1
    assert not (tmp_path / "t.yml").exists()


def test_cli_team_dry_run_validates_via_armature(tmp_path):
    if not shutil.which("armature"):
        pytest.skip("armature CLI not on PATH")
    dist = tmp_path / "dist"
    build_all(FIX, dist)  # fixtures: security-triage + incident-comms
    wf = tmp_path / "team.yml"
    rc = main(["team", str(FIX), "--bundles", str(dist), "--out", str(wf), "--dry-run"])
    assert rc == 0  # armature run --dry-run validates the 2-stage team
