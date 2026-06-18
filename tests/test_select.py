from pathlib import Path

from armature_cabinet import load_package
from armature_cabinet.select import select_skills, tokenize

SEC = Path(__file__).parent / "fixtures" / "security-triage"
COMMS = Path(__file__).parent / "fixtures" / "incident-comms"


def test_tokenize_lowercases_strips_punctuation_drops_stopwords():
    toks = tokenize("A set of RAW security signals, needs to be gated!")
    assert {"security", "signals", "raw", "gated"} <= toks
    # function words and single chars dropped
    for dropped in ("a", "of", "needs", "to", "be", "set"):
        assert dropped not in toks


def test_select_ranks_by_overlap_on_security_fixture():
    ids = select_skills(load_package(SEC), "prioritize open Dependabot alerts")
    assert ids == ["appsec.triage-dependabot-alerts", "appsec.triage-secret-scanning"]
    assert "appsec.rank-findings" not in ids


def test_select_no_match_returns_empty():
    assert select_skills(load_package(SEC), "quantum entanglement simulation") == []


def test_select_on_comms_fixture():
    ids = select_skills(load_package(COMMS), "draft a status update for executives")
    assert ids == ["comms.draft-status-update"]
    assert "comms.cadence-plan" not in ids


def test_select_empty_or_stopword_only_task_returns_empty():
    assert select_skills(load_package(SEC), "") == []
    assert select_skills(load_package(SEC), "the a of to") == []


def test_select_ties_broken_by_source_order(tmp_path):
    (tmp_path / "cabinet.yaml").write_text(
        "id: tie\nname: Tie\nkind: partner\nschema_version: '0.1.0'\n", encoding="utf-8")
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "a.md").write_text(
        "---\nid: a\nwhen: alpha beta\n---\nb\n", encoding="utf-8")
    (tmp_path / "skills" / "b.md").write_text(
        "---\nid: b\nwhen: alpha gamma\n---\nb\n", encoding="utf-8")
    pkg = load_package(tmp_path)
    assert select_skills(pkg, "alpha") == ["a", "b"]
