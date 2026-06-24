from pathlib import Path

import pytest

from armature_cabinet.evolve.patch_applier import apply_patch_to_folder, PatchReject
from armature_cabinet.evolve.types import FileProposal


def _make_agent(tmp_path: Path):
    (tmp_path / "cabinet.yaml").write_text(
        'id: t\nname: T\nkind: partner\nschema_version: "0.1.0"\nversion: "0.1.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "soul.md").write_text("---\nrole: worker\n---\nI am T.\n", encoding="utf-8")
    (tmp_path / "mandate.md").write_text(
        "---\ngoal: triage\n---\nTriage alerts.\n", encoding="utf-8"
    )
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "draft-reply.md").write_text(
        "---\nid: draft-reply\n---\n\n## Output\nold output\n", encoding="utf-8"
    )


def test_apply_body_replace(tmp_path: Path):
    _make_agent(tmp_path)
    p = FileProposal(
        target_file="skills/draft-reply.md",
        surface="skills",
        gate="auto",
        rationale="r",
        body_changes=[
            {"op": "replace", "anchor": "## Output", "content": "## Output\nnew output\n"}
        ],
    )
    apply_patch_to_folder(tmp_path, p)
    text = (tmp_path / "skills" / "draft-reply.md").read_text(encoding="utf-8")
    assert "new output" in text
    assert "old output" not in text


def test_apply_frontmatter_set(tmp_path: Path):
    _make_agent(tmp_path)
    p = FileProposal(
        target_file="skills/draft-reply.md",
        surface="skills",
        gate="auto",
        rationale="r",
        frontmatter_changes={"output_type": {"set": "guided_json"}},
    )
    apply_patch_to_folder(tmp_path, p)
    text = (tmp_path / "skills" / "draft-reply.md").read_text(encoding="utf-8")
    assert "output_type: guided_json" in text


def test_rejects_when_target_missing(tmp_path: Path):
    _make_agent(tmp_path)
    p = FileProposal(
        target_file="skills/nope.md", surface="skills", gate="auto", rationale="r"
    )
    with pytest.raises(PatchReject):
        apply_patch_to_folder(tmp_path, p)


def test_rejects_when_anchor_not_found(tmp_path: Path):
    _make_agent(tmp_path)
    p = FileProposal(
        target_file="skills/draft-reply.md",
        surface="skills",
        gate="auto",
        rationale="r",
        body_changes=[{"op": "replace", "anchor": "## Nonexistent", "content": "x"}],
    )
    with pytest.raises(PatchReject):
        apply_patch_to_folder(tmp_path, p)


def _corrupting_proposal() -> FileProposal:
    """A patch that makes the folder invalid: a context ref to a missing file."""
    return FileProposal(
        target_file="skills/draft-reply.md",
        surface="skills",
        gate="auto",
        rationale="r",
        frontmatter_changes={"context": {"set": ["context/missing.md"]}},
    )


def test_rejects_when_validation_fails_after_patch(tmp_path: Path):
    """A patch that corrupts the folder must be rejected (invariant #4)."""
    _make_agent(tmp_path)
    with pytest.raises(PatchReject):
        apply_patch_to_folder(tmp_path, _corrupting_proposal())


def test_rejects_writes_nothing_on_validation_failure(tmp_path: Path):
    """On rejection the on-disk file must be unchanged (nothing written)."""
    _make_agent(tmp_path)
    original = (tmp_path / "skills" / "draft-reply.md").read_text(encoding="utf-8")
    with pytest.raises(PatchReject):
        apply_patch_to_folder(tmp_path, _corrupting_proposal())
    assert (tmp_path / "skills" / "draft-reply.md").read_text(encoding="utf-8") == original


def test_apply_frontmatter_remove(tmp_path: Path):
    _make_agent(tmp_path)
    # First add an output_type key via a set, then remove it in a second patch.
    add_p = FileProposal(
        target_file="skills/draft-reply.md",
        surface="skills",
        gate="auto",
        rationale="r",
        frontmatter_changes={"output_type": {"set": "guided_json"}},
    )
    apply_patch_to_folder(tmp_path, add_p)
    rm_p = FileProposal(
        target_file="skills/draft-reply.md",
        surface="skills",
        gate="auto",
        rationale="r",
        frontmatter_changes={"output_type": {"remove": True}},
    )
    apply_patch_to_folder(tmp_path, rm_p)
    text = (tmp_path / "skills" / "draft-reply.md").read_text(encoding="utf-8")
    assert "output_type" not in text


def test_apply_body_insert(tmp_path: Path):
    _make_agent(tmp_path)
    p = FileProposal(
        target_file="skills/draft-reply.md",
        surface="skills",
        gate="auto",
        rationale="r",
        body_changes=[
            {"op": "insert", "anchor": "## Output", "content": "## Preamble\nintro.\n\n"}
        ],
    )
    apply_patch_to_folder(tmp_path, p)
    text = (tmp_path / "skills" / "draft-reply.md").read_text(encoding="utf-8")
    assert "## Preamble" in text
    assert "## Output" in text
    # Preamble inserted before the anchor, original section preserved.
    assert text.index("## Preamble") < text.index("## Output")


def test_rejects_unknown_body_op(tmp_path: Path):
    _make_agent(tmp_path)
    p = FileProposal(
        target_file="skills/draft-reply.md",
        surface="skills",
        gate="auto",
        rationale="r",
        body_changes=[{"op": "delete", "anchor": "## Output", "content": "x"}],
    )
    with pytest.raises(PatchReject):
        apply_patch_to_folder(tmp_path, p)
