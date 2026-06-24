import json
from pathlib import Path
from armature_cabinet.evolve.versioning import (
    write_version, promote, rollback, read_latest, ThresholdPromotionPolicy,
)


def _make_agent(tmp_path: Path):
    (tmp_path / "cabinet.yaml").write_text('id: a\nname: A\nkind: partner\nschema_version: "0.1.0"\nversion: "0.1.0"\n', encoding="utf-8")
    (tmp_path / "soul.md").write_text("---\nrole: worker\n---\nA.\n", encoding="utf-8")
    (tmp_path / "mandate.md").write_text("---\ngoal: g\n---\nG.\n", encoding="utf-8")


def test_write_version_snapshots_folder(tmp_path: Path):
    _make_agent(tmp_path)
    v = write_version(tmp_path, version="0.2.0", hqs=0.7, predicted_fixes=["output_invalid:x"])
    assert (tmp_path / "versions" / "0.2.0" / "cabinet.yaml").exists()
    assert (tmp_path / "versions" / "0.2.0" / "soul.md").exists()
    assert (tmp_path / "versions" / "0.2.0" / ".proposal.json").exists()


def test_promote_advances_latest_on_hqs_gain(tmp_path: Path):
    _make_agent(tmp_path)
    write_version(tmp_path, version="0.2.0", hqs=0.5)  # baseline
    promote(tmp_path, "0.2.0", policy=ThresholdPromotionPolicy(min_gain=0.02),
            current_hqs=0.5, new_hqs=0.6)
    assert read_latest(tmp_path) == "0.2.0"


def test_promote_does_not_advance_without_gain(tmp_path: Path):
    _make_agent(tmp_path)
    write_version(tmp_path, version="0.2.0", hqs=0.5)
    promote(tmp_path, "0.2.0", policy=ThresholdPromotionPolicy(min_gain=0.02),
            current_hqs=0.6, new_hqs=0.55)  # regression
    assert read_latest(tmp_path) is None


def test_rollback_restores_prior_version(tmp_path: Path):
    _make_agent(tmp_path)
    (tmp_path / "soul.md").write_text("---\nrole: worker\n---\nA v1.\n", encoding="utf-8")
    write_version(tmp_path, version="0.1.0", hqs=0.5)
    # mutate live folder
    (tmp_path / "soul.md").write_text("---\nrole: worker\n---\nA v2 BROKEN.\n", encoding="utf-8")
    write_version(tmp_path, version="0.2.0", hqs=0.4)
    rollback(tmp_path, "0.1.0")
    assert "v1" in (tmp_path / "soul.md").read_text(encoding="utf-8")
