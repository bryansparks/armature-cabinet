# tests/test_evolve_cycle_history.py
from pathlib import Path

from armature_cabinet.evolve.cycle_history import (
    append_record, read_history, last_record,
    prose_cycles_without_gain, detect_oscillation, update_last_verified,
)


def _rec(cycle, *, surface="skills", before=0.5, after=0.5,
         fixes=None, regressions=None):
    return {
        "cycle": cycle, "proposed_file": "skills/x.md", "gate": "auto",
        "surface": surface, "hqs_before": before, "hqs_after": after,
        "predicted_fixes": fixes or [], "predicted_regressions": regressions or [],
        "verified": {}, "version": f"0.1.{cycle}", "rolled_back": False,
    }


def test_append_and_read_round_trip(tmp_path: Path):
    assert read_history(tmp_path) == []
    append_record(tmp_path, _rec(1, after=0.6))
    append_record(tmp_path, _rec(2, after=0.7))
    h = read_history(tmp_path)
    assert len(h) == 2
    assert h[0]["cycle"] == 1 and h[1]["cycle"] == 2
    assert last_record(tmp_path)["cycle"] == 2


def test_malformed_lines_are_skipped(tmp_path: Path, capsys):
    p = tmp_path / ".evolve" / "history.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text('{"cycle": 1}\nNOT JSON\n{"cycle": 2}\n', encoding="utf-8")
    h = read_history(tmp_path)
    assert [r["cycle"] for r in h] == [1, 2]
    assert "skipping malformed line" in capsys.readouterr().err


def test_prose_cycles_without_gain_counts_trailing(tmp_path: Path):
    # two flat prose cycles then a gain -> count is 0 (gain resets)
    hist = [_rec(1, before=0.5, after=0.5), _rec(2, before=0.5, after=0.5),
            _rec(3, before=0.5, after=0.6)]
    assert prose_cycles_without_gain(hist) == 0
    # two flat trailing -> 2
    hist = [_rec(1, before=0.5, after=0.6), _rec(2, before=0.5, after=0.5),
            _rec(3, before=0.5, after=0.5)]
    assert prose_cycles_without_gain(hist) == 2
    # non-prose surface resets -> 0
    hist = [_rec(1, surface="none", before=0.5, after=0.5)]
    assert prose_cycles_without_gain(hist) == 0


def test_detect_oscillation_requires_two_sign_flips():
    # +, -, + -> oscillating
    hist = [_rec(1, before=0.5, after=0.6), _rec(2, before=0.6, after=0.5),
            _rec(3, before=0.5, after=0.6)]
    assert detect_oscillation(hist) is True
    # -, +, - -> oscillating
    hist = [_rec(1, before=0.6, after=0.5), _rec(2, before=0.5, after=0.6),
            _rec(3, before=0.6, after=0.5)]
    assert detect_oscillation(hist) is True
    # monotonic increase -> not oscillating
    hist = [_rec(1, before=0.5, after=0.6), _rec(2, before=0.6, after=0.7),
            _rec(3, before=0.7, after=0.8)]
    assert detect_oscillation(hist) is False
    # fewer than 3 -> not oscillating
    assert detect_oscillation([_rec(1, before=0.5, after=0.6)]) is False


def test_update_last_verified_rewrites_final_record(tmp_path: Path):
    append_record(tmp_path, _rec(1, fixes=["output_invalid:x"]))
    append_record(tmp_path, _rec(2, fixes=["output_invalid:y"]))
    update_last_verified(tmp_path, verdict="unfixed", vs_cycle=1)
    h = read_history(tmp_path)
    assert h[-1]["verified"] == {"verdict": "unfixed", "vs_cycle": 1}
    # earlier record untouched
    assert h[0]["verified"] == {}
