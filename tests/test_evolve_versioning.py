import shutil
from pathlib import Path

from armature_cabinet.evolve import versioning
from armature_cabinet.evolve.versioning import (
    write_version, promote, rollback, read_latest, ThresholdPromotionPolicy,
)


def _make_agent(tmp_path: Path):
    (tmp_path / "cabinet.yaml").write_text('id: a\nname: A\nkind: partner\nschema_version: "0.1.0"\nversion: "0.1.0"\n', encoding="utf-8")
    (tmp_path / "soul.md").write_text("---\nrole: worker\n---\nA.\n", encoding="utf-8")
    (tmp_path / "mandate.md").write_text("---\ngoal: g\n---\nG.\n", encoding="utf-8")


def test_write_version_snapshots_folder(tmp_path: Path):
    _make_agent(tmp_path)
    write_version(tmp_path, version="0.2.0", hqs=0.7, predicted_fixes=["output_invalid:x"])
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


def test_write_version_excludes_evolve_sidecar(tmp_path: Path):
    _make_agent(tmp_path)
    (tmp_path / ".evolve").mkdir()
    (tmp_path / ".evolve" / "history.jsonl").write_text('{"cycle":1}\n', encoding="utf-8")
    write_version(tmp_path, version="0.2.0", hqs=0.7, predicted_fixes=[])
    snap = tmp_path / "versions" / "0.2.0"
    assert not (snap / ".evolve").exists()  # sidecar not snapshotted


def test_write_version_atomic_on_failure(tmp_path: Path, monkeypatch):
    _make_agent(tmp_path)
    # Sabotage copy2 mid-snapshot to simulate a crash.
    real_copy2 = shutil.copy2

    def _boom(src, dst, *, follow_symlinks=True):
        # Let the first file copy succeed, then explode on the second.
        if "mandate.md" in str(src):
            raise OSError("simulated mid-snapshot crash")
        return real_copy2(src, dst, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(versioning.shutil, "copy2", _boom)
    try:
        write_version(tmp_path, version="0.2.0", hqs=0.7, predicted_fixes=[])
    except OSError:
        pass
    # No partial version directory is left visible...
    assert not (tmp_path / "versions" / "0.2.0").exists()
    # ...and the temp dir was cleaned up.
    assert not any(p.name.startswith(".tmp-") for p in (tmp_path / ".evolve").iterdir())


def test_rollback_preserves_evolve_sidecar(tmp_path: Path):
    _make_agent(tmp_path)
    (tmp_path / ".evolve").mkdir()
    (tmp_path / ".evolve" / "history.jsonl").write_text('{"cycle":1}\n', encoding="utf-8")
    write_version(tmp_path, version="0.1.0", hqs=0.5)
    (tmp_path / "soul.md").write_text("---\nrole: worker\n---\nBROKEN\n", encoding="utf-8")
    write_version(tmp_path, version="0.2.0", hqs=0.4)
    rollback(tmp_path, "0.1.0")
    assert (tmp_path / ".evolve" / "history.jsonl").read_text(encoding="utf-8") == '{"cycle":1}\n'
