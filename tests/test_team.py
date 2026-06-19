from pathlib import Path

import pytest

from armature_cabinet.errors import CabinetError
from armature_cabinet.team import generate_workflow, run_workflow


def test_generate_workflow_structure(tmp_path):
    wf = generate_workflow(["a", "b"], tmp_path / "dist", "lib-team")
    assert wf["name"] == "lib-team"
    assert wf["version"] == "1.0"
    assert wf["model_tiers"]["small"]["model"] == "claude-haiku-4-5-20251001"
    assert wf["role_type_defaults"]["worker"] == "small"
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
