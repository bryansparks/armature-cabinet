# src/armature_cabinet/evolve/cycle_history.py
"""Per-cycle history sidecar: <folder>/.evolve/history.jsonl.

Append-only record of each evolve cycle. The keystone for v2 automation:
  - prose_cycles_without_gain  -> LoRA eligibility (decide_lora)
  - detect_oscillation         -> force review (stop auto-promoting a thrasher)
  - verify_prior + update_last_verified -> close invariant #3 (predictions checked)

Pure stdlib (json, pathlib). No armature import. The loader is allowlist-based
so .evolve/ is never compiled into a bundle — there is no ignore mechanism.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_PROSE_SURFACES = {"skills", "mandate", "skills+soul", "config"}
_HISTORY_REL = Path(".evolve") / "history.jsonl"


def _history_path(folder: Path) -> Path:
    return folder / _HISTORY_REL


def read_history(folder: Path) -> list[dict[str, Any]]:
    """All cycle records. Malformed lines are skipped (logged to stderr)."""
    path = _history_path(folder)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"cycle_history: skipping malformed line {lineno}", file=sys.stderr)
    return out


def last_record(folder: Path) -> dict[str, Any] | None:
    h = read_history(folder)
    return h[-1] if h else None


def append_record(folder: Path, record: dict[str, Any]) -> None:
    path = _history_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def prose_cycles_without_gain(history: list[dict[str, Any]]) -> int:
    """Trailing consecutive PROSE cycles where hqs_after <= hqs_before.
    Resets to 0 on a gaining cycle or a non-prose (lora/none) cycle."""
    count = 0
    for rec in reversed(history):
        if rec.get("surface") not in _PROSE_SURFACES:
            break
        before, after = rec.get("hqs_before"), rec.get("hqs_after")
        if before is None or after is None:
            break
        if after > before:
            break
        count += 1
    return count


def detect_oscillation(history: list[dict[str, Any]]) -> bool:
    """True when the last 3 records' HQS-delta signs flip twice (+,-,+ or -,+,-)."""
    if len(history) < 3:
        return False
    signs: list[int] = []
    for rec in history[-3:]:
        before, after = rec.get("hqs_before"), rec.get("hqs_after")
        if before is None or after is None:
            return False
        delta = (after or 0.0) - (before or 0.0)
        signs.append(1 if delta > 0 else (-1 if delta < 0 else 0))
    if 0 in signs:
        return False
    return signs[0] != signs[1] and signs[1] != signs[2]


def update_last_verified(folder: Path, verdict: str, vs_cycle: int) -> None:
    """Rewrite the final record's `verified` field in place (the only non-append op)."""
    path = _history_path(folder)
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return
    last = json.loads(lines[-1])
    last["verified"] = {"verdict": verdict, "vs_cycle": vs_cycle}
    lines[-1] = json.dumps(last, default=str)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
