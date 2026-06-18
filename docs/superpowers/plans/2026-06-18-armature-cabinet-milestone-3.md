# armature-cabinet Milestone 3 — `when`-based skill selection (woodshop) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compile-time `--when "<task>"` selection mode that picks the skills whose `when` overlaps the task and feeds their ids to the existing `compile_agent(include=...)` path — the woodshop model — with the compiler staying pure (no LLM, no network).

**Architecture:** One new pure module (`select.py`: `select_skills` + `tokenize`) produces a ranked id list; the CLI gains a `--when` flag (mutually exclusive with `--skill`) that calls it and passes the result as `include`. `compile_agent`, `validate_package`, `loader`, `compiler`, `errors`, `model` are unchanged.

**Tech Stack:** Python ≥3.11 stdlib only (`re`), pyyaml, armature-agents≥0.3.5, pytest. No new deps.

## Global Constraints

Copied verbatim from the approved M3 spec; every task inherits these.
- Runtime deps `armature-agents>=0.3.5` + `pyyaml>=6.0`; no new deps. `requires-python = ">=3.11"`.
- Bundle validates as `CompiledAgent`; every `role.skills` id is a key in `skill_library`; every `SkillDef` has `content`. (A 0-skill `--when`-no-match bundle is valid — both hold vacuously.)
- `role.type ∈ {worker, orchestrator, judge, researcher}`; cabinet `kind` → `x_kind` (default worker).
- No fields invented outside `extra="allow"` objects; extra metadata only on `Role`/`SkillDef`, `x_`-prefixed.
- Soft/hard guardrail split preserved; `*.safety.yaml` advisory; no hard enforcement in the bundle.
- `cabinet.yaml` = source manifest; `agent.yaml` = compiled output. Naming unchanged.
- One-directional: this package compiles; core consumes. No core edits, no folder parsing in core, no network/registry fetching.
- **Purity:** `select_skills`/`tokenize` are pure (no I/O, no network, no LLM, deterministic — same inputs → same output). The compiler stays pure; only the CLI writes files.
- Existing 35 tests must keep passing.

---

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `src/armature_cabinet/select.py` | `tokenize(text)` + `select_skills(pkg, task) -> list[str]` — pure keyword-overlap matcher | NEW |
| `src/armature_cabinet/__init__.py` | export `select_skills` | MODIFY |
| `src/armature_cabinet/cli.py` | `--when` flag on build+validate, mutual exclusion with `--skill`, no-match warning, validate preview | MODIFY (full replace) |
| `tests/test_select.py` | tokenizer + scoring/ranking + no-match + tie-break, both fixtures | NEW |
| `tests/test_validate.py` | CLI `--when` cases (subset build, mutual exclusion, no-match, validate preview) | MODIFY (append) |
| `src/armature_cabinet/compiler.py`, `validate.py`, `loader.py`, `errors.py`, `model.py` | **unchanged** | untouched |

---

## Task 1: Commit M3 spec + plan docs

**Files:**
- Create: `docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-3-design.md` (already written)
- Create: `docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-3.md` (this file)
- Test: none (setup)

**Interfaces:**
- Produces: a git commit of the M3 spec + plan; the post-commit HEAD is the **M3 base** for the final review's diff range.

- [ ] **Step 1: Verify the docs exist**

Run:
```bash
ls docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-3-design.md docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-3.md
```
Expected: both files listed.

- [ ] **Step 2: Confirm baseline still green**

Run: `python3 -m pytest -q`
Expected: `35 passed`.

- [ ] **Step 3: Commit the docs**

Run:
```bash
git add docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-3-design.md docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-3.md
git commit -m "docs: milestone-3 design + implementation plan" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git rev-parse HEAD
```
Expected: commit created; **record the printed HEAD sha** — this is the M3 base for the final whole-branch review.

---

## Task 2: `select.py` — pure keyword-overlap matcher + tests

**Files:**
- Create: `src/armature_cabinet/select.py`
- Modify: `src/armature_cabinet/__init__.py`
- Test: `tests/test_select.py`

**Interfaces:**
- Consumes: `AgentPackage` (from `.model`) — its `.skills` list, each `Skill.id` and `Skill.when`.
- Produces: `tokenize(text: str) -> set[str]` and `select_skills(pkg: AgentPackage, task: str) -> list[str]` (ranked skill ids). Task 3's CLI imports `select_skills` from `.select`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_select.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_select.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'armature_cabinet.select'`.

- [ ] **Step 3: Create `select.py`**

Create `src/armature_cabinet/select.py`:
```python
"""Select skills whose ``when`` overlaps a task string (the woodshop model).

Pure and deterministic: no I/O, no network, no LLM. Returns ranked skill ids
that ``compile_agent(include=...)`` consumes.
"""
from __future__ import annotations
import re

from .model import AgentPackage

# Function words only — never domain/content nouns. Tunable.
_STOPWORDS = frozenset({
    "a", "an", "the", "this", "that", "these", "those",
    "for", "to", "of", "in", "on", "at", "by", "from", "into", "with", "without",
    "and", "or", "but", "as", "than", "then", "so",
    "is", "are", "be", "been", "being", "was", "were",
    "has", "have", "had", "do", "does", "did",
    "can", "could", "should", "would", "may", "might", "will", "shall",
    "it", "its", "they", "their", "them", "we", "you", "your",
    "what", "which", "who", "whom", "when", "where", "why", "how",
    "needs", "need", "needed", "requires", "require", "required", "requiring",
    "set", "get", "go", "use", "using", "used",
})

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> set[str]:
    """Lowercase, split on non-alphanumeric, drop stopwords and single-char tokens."""
    return {t for t in _TOKEN.findall(text.lower())
            if len(t) > 1 and t not in _STOPWORDS}


def select_skills(pkg: AgentPackage, task: str) -> list[str]:
    """Ids of skills whose ``when`` shares >=1 content keyword with ``task``,
    ranked by overlap count desc; ties broken by source order in ``pkg.skills``.
    Skills with no ``when`` are never selected.
    """
    task_toks = tokenize(task)
    if not task_toks:
        return []
    ranked: list[tuple[int, int, str]] = []  # (score, source_index, id)
    for idx, s in enumerate(pkg.skills):
        if not s.when:
            continue
        score = len(task_toks & tokenize(s.when))
        if score >= 1:
            ranked.append((score, idx, s.id))
    ranked.sort(key=lambda t: (-t[0], t[1]))
    return [sid for _, _, sid in ranked]
```

- [ ] **Step 4: Export `select_skills` from the package**

Replace the full contents of `src/armature_cabinet/__init__.py` with:
```python
"""armature-cabinet — compile cabinet agent folders into Armature agent bundles."""
from .errors import CabinetError
from .loader import load_package
from .compiler import compile_agent, compile_safety_fragment, compose_description
from .validate import validate_package
from .select import select_skills

__all__ = [
    "CabinetError",
    "load_package",
    "compile_agent",
    "compile_safety_fragment",
    "compose_description",
    "validate_package",
    "select_skills",
]
__version__ = "0.1.0"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_select.py -q`
Expected: `6 passed`.

- [ ] **Step 6: Run the full suite**

Run: `python3 -m pytest -q`
Expected: `41 passed` (35 + 6). No regression.

- [ ] **Step 7: Commit**

```bash
git add src/armature_cabinet/select.py src/armature_cabinet/__init__.py tests/test_select.py
git commit -m "feat(select): pure keyword-overlap skill selector (woodshop seed)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: CLI `--when` wiring + tests

**Files:**
- Modify: `src/armature_cabinet/cli.py` (full replace)
- Modify: `tests/test_validate.py` (append CLI `--when` cases)
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: `select_skills(pkg, task) -> list[str]` from Task 2; `compile_agent(pkg, include=...)`, `validate_package(pkg, include)`, `CabinetError` (all unchanged).
- Produces: `armature-cabinet build|validate <folder> [--when "<task>"] [--skill ID ...]`; `--when` and `--skill` mutually exclusive (exit 1); no-match → warning + 0-skill bundle + exit 0; `validate --when` previews the ranked selection.

- [ ] **Step 1: Write the failing CLI tests**

Append to `tests/test_validate.py`:
```python
import yaml


def test_build_with_when_selects_matching_skills(tmp_path):
    out = tmp_path / "out"
    rc = main(["build", str(FIX), "--when",
               "prioritize open Dependabot alerts", "-o", str(out)])
    assert rc == 0
    bundle = yaml.safe_load((out / "agent.yaml").read_text())
    assert bundle["role"]["skills"] == [
        "appsec.triage-dependabot-alerts", "appsec.triage-secret-scanning"]


def test_build_when_and_skill_mutually_exclusive(capsys):
    rc = main(["build", str(FIX), "--when", "alerts", "--skill", "appsec.rank-findings"])
    assert rc == 1
    assert "mutually exclusive" in capsys.readouterr().err.lower()


def test_build_when_no_match_warns_and_builds_zero_skills(tmp_path, capsys):
    out = tmp_path / "out"
    rc = main(["build", str(FIX), "--when", "quantum entanglement", "-o", str(out)])
    assert rc == 0
    assert "no skills matched" in capsys.readouterr().err.lower()
    bundle = yaml.safe_load((out / "agent.yaml").read_text())
    assert bundle["role"]["skills"] == []
    assert bundle["skill_library"] == {}


def test_validate_when_previews_matched_skills(capsys):
    rc = main(["validate", str(FIX), "--when",
               "prioritize open Dependabot alerts"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "matched 2 skill(s)" in out
    assert "appsec.triage-dependabot-alerts" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validate.py -q -k "when"`
Expected: FAIL — `--when` is not a known argument (argparse errors / `SystemExit`), and `select_skills` is not wired into the CLI.

- [ ] **Step 3: Rewrite `cli.py`**

Replace the full contents of `src/armature_cabinet/cli.py` with:
```python
"""`armature-cabinet build|validate <folder>` — compile / check a cabinet agent."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

import yaml

from .errors import CabinetError
from .loader import load_package
from .compiler import compile_agent, compile_safety_fragment
from .validate import validate_package
from .select import select_skills


def _dump(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False, width=100)


def _report(r) -> None:
    for w in r.warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in r.errors:
        print(f"error: {e}", file=sys.stderr)


def cmd_build(args: argparse.Namespace) -> int:
    if args.when is not None and args.skill:
        print("error: --when and --skill are mutually exclusive (pick one selection mode)",
              file=sys.stderr)
        return 1
    pkg = load_package(args.folder)
    if args.when is not None:
        include = select_skills(pkg, args.when)
        if not include:
            print(f'warning: no skills matched task: "{args.when}"; building with 0 skills',
                  file=sys.stderr)
    else:
        include = args.skill or None

    r = validate_package(pkg, include)
    _report(r)
    if not r.ok:
        return 1

    bundle = compile_agent(pkg, include=include)
    out_dir = Path(args.out) if args.out else Path("dist") / pkg.id
    bundle_path = out_dir / "agent.yaml"
    _dump(bundle, bundle_path)

    msg = [f"compiled '{pkg.id}' ({pkg.kind})", f"  bundle  -> {bundle_path}"]
    msg.append(f"  role    -> {len(bundle['role']['skills'])} skill(s), "
               f"{len(bundle['role']['tools'])} tool(s)")

    if not args.no_safety:
        fragment = compile_safety_fragment(pkg)
        if len(fragment) > 1:  # more than just the _note
            frag_path = out_dir / f"{pkg.id}.safety.yaml"
            _dump(fragment, frag_path)
            msg.append(f"  safety  -> {frag_path}  (advisory; merge into your workflow)")

    print("\n".join(msg))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    if args.when is not None and args.skill:
        print("error: --when and --skill are mutually exclusive (pick one selection mode)",
              file=sys.stderr)
        return 1
    pkg = load_package(args.folder)
    if args.when is not None:
        include = select_skills(pkg, args.when)
        if include:
            print(f"matched {len(include)} skill(s): {', '.join(include)}")
        else:
            print(f'warning: no skills matched task: "{args.when}"', file=sys.stderr)
    else:
        include = args.skill or None

    r = validate_package(pkg, include)
    compile_agent(pkg, include=include)
    _report(r)
    if r.ok:
        print(f"ok: {pkg.id} ({pkg.kind})")
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="armature-cabinet")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="compile a cabinet agent folder into an Armature bundle")
    b.add_argument("folder", help="path to the cabinet agent folder (containing cabinet.yaml)")
    b.add_argument("-o", "--out", help="output directory (default: dist/<id>/)")
    b.add_argument("--skill", action="append",
                   help="attach only this skill id (repeatable); default attaches all")
    b.add_argument("--when", help="attach skills whose 'when' overlaps this task string")
    b.add_argument("--no-safety", action="store_true", help="skip the advisory safety fragment")
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("validate",
                       help="load + validate + compile in memory; writes no files")
    v.add_argument("folder", help="path to the cabinet agent folder")
    v.add_argument("--skill", action="append",
                   help="check only this skill id (repeatable); default checks all")
    v.add_argument("--when", help="preview skills whose 'when' overlaps this task string")
    v.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except CabinetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the new CLI tests**

Run: `python3 -m pytest tests/test_validate.py -q -k "when"`
Expected: `4 passed`.

- [ ] **Step 5: Run the full suite**

Run: `python3 -m pytest -q`
Expected: `45 passed` (41 + 4). No regression; the e2e (no `--when`) is untouched.

- [ ] **Step 6: Reinstall the console script and smoke-test**

Run:
```bash
python3 -m pip install -e ".[dev]" -q
armature-cabinet validate tests/fixtures/security-triage --when "prioritize open Dependabot alerts"
armature-cabinet build tests/fixtures/security-triage --when "prioritize open Dependabot alerts" -o /tmp/woodshop
armature-cabinet build tests/fixtures/security-triage --when "quantum entanglement" -o /tmp/woodshop-nomatch 2>&1 | tail -2
armature-cabinet build tests/fixtures/security-triage --when "alerts" --skill appsec.rank-findings 2>&1 | tail -1
```
Expected:
- `validate --when` prints `matched 2 skill(s): appsec.triage-dependabot-alerts, appsec.triage-secret-scanning` then `ok: security-triage (partner)`.
- `build --when` succeeds; `/tmp/woodshop/agent.yaml` carries the 2 matched skills.
- `build --when <no-match>` prints the `warning: no skills matched ...` line and builds a 0-skill bundle.
- `build --when ... --skill ...` prints `error: --when and --skill are mutually exclusive ...` and exits non-zero.

- [ ] **Step 7: Commit**

```bash
git add src/armature_cabinet/cli.py tests/test_validate.py
git commit -m "feat(cli): --when selection mode (woodshop), mutually exclusive with --skill" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 8: Final repo check**

Run:
```bash
git log --oneline | head -5
git status -s
python3 -m pytest -q 2>&1 | tail -2
```
Expected: the 3 M3 commits on top of the M3 docs commit, a clean working tree, and `45 passed`.