# armature-cabinet Milestone 8 — Team workflow generation + `armature run` handoff — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `armature-cabinet team <library>` — assemble a library of agents into a sequential-pipeline team workflow and hand off to `armature run` (`--dry-run` validates, `--run` executes).

**Architecture:** A new `team.py` (`generate_workflow` pure + `run_workflow` subprocess to the `armature` CLI) + a `team` CLI subcommand (selection → bundle-check → generate → dump → print/run). Compiler unchanged; cabinet shells out to `armature` (does not import its runner).

**Tech Stack:** Python ≥3.11, pyyaml, stdlib `subprocess`/`shutil`, pytest. The `armature` CLI (from `armature-agents`, a runtime dep) for `--dry-run`/`--run`.

## Global Constraints

Copied verbatim from the approved M8 spec; every task inherits these.
- Runtime deps `armature-agents>=0.3.5`, `pyyaml>=6.0`, `rich>=13.0`, `questionary>=2.0`. ruff dev-only. `requires-python = ">=3.11"`.
- **M8 does not modify the compiler:** `loader`/`compiler`/`validate`/`select`/`scaffold`/`prompts`/`library`/`errors`/`model` untouched. Only `team.py` (new), `cli.py` (`team` subcommand), `__init__.py` (export), `tests/test_team.py` (new) change. `git diff <M8-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,scaffold,prompts,library,errors,model}.py` must be empty.
- `generate_workflow` is pure (no I/O/LLM); `run_workflow` only shells out to `armature` (no import of armature's runner). `--dry-run`/`--run` mutually exclusive. Absolute bundle paths in the generated workflow.
- The generated workflow must be a valid Armature spec (the integration test proves it via `armature run --dry-run`).
- Existing 65 tests + ruff + e2e stay green.

---

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `src/armature_cabinet/team.py` | `generate_workflow(agent_ids, bundles_dir, name) -> dict` (pure) + `run_workflow(wf_path, dry_run) -> int` (subprocess to armature) | NEW |
| `src/armature_cabinet/cli.py` | add `team` subcommand (`cmd_team`) | MODIFY |
| `src/armature_cabinet/__init__.py` | export `generate_workflow`, `run_workflow` | MODIFY |
| `tests/test_team.py` | function tests + CLI tests + integration dry-run | NEW |
| compiler/library/wizard modules | **unchanged** | untouched |

---

## Task 1: Commit M8 spec + plan docs

**Files:** Create the M8 spec + plan (already written). Test: none (setup).

- [ ] **Step 1: Verify the docs exist**

Run:
```bash
ls docs/superpowers/specs/2026-06-19-armature-cabinet-milestone-8-design.md docs/superpowers/plans/2026-06-19-armature-cabinet-milestone-8.md
```
Expected: both listed.

- [ ] **Step 2: Confirm baseline green + lint clean**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `65 passed`; ruff clean.

- [ ] **Step 3: Commit the docs**

Run:
```bash
git add docs/superpowers/specs/2026-06-19-armature-cabinet-milestone-8-design.md docs/superpowers/plans/2026-06-19-armature-cabinet-milestone-8.md
git commit -m "docs: milestone-8 design + implementation plan" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git rev-parse HEAD
```
Expected: commit created; **record the printed HEAD sha** — this is the M8 base.

---

## Task 2: `team.py` + `test_team.py` (function tests)

**Files:**
- Create: `src/armature_cabinet/team.py`
- Modify: `src/armature_cabinet/__init__.py` (export `generate_workflow`, `run_workflow`)
- Test: `tests/test_team.py` (function tests; CLI tests appended in Task 3)

**Interfaces:**
- Produces: `generate_workflow(agent_ids: list[str], bundles_dir: Path, name: str) -> dict` (pure) and `run_workflow(wf_path: Path, dry_run: bool) -> int` (subprocess; raises `CabinetError` if `armature` not on PATH). Task 3's CLI calls these.

- [ ] **Step 1: Write the failing function tests**

Create `tests/test_team.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_team.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'armature_cabinet.team'`.

- [ ] **Step 3: Create `src/armature_cabinet/team.py`**

```python
"""Team workflow generation + armature run handoff."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

from .errors import CabinetError

_MODEL_TIERS = {"small": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"}}


def generate_workflow(agent_ids: list[str], bundles_dir: Path, name: str) -> dict:
    """Pure: build an Armature workflow spec dict from an ordered agent id list.

    Agents form a sequential pipeline (stage[i].depends_on = [stage[i-1].id]).
    Bundle paths are absolute so armature resolves them regardless of the wf location.
    """
    bdir = Path(bundles_dir).resolve()
    agent_library = {aid: {"path": str(bdir / aid / "agent.yaml")} for aid in agent_ids}
    stages = []
    for i, aid in enumerate(agent_ids):
        stages.append({
            "id": aid,
            "agent": aid,
            "output_mode": "text",
            "depends_on": [agent_ids[i - 1]] if i > 0 else [],
        })
    return {
        "name": name,
        "version": "1.0",
        "model_tiers": _MODEL_TIERS,
        "role_type_defaults": {"worker": "small"},
        "agent_library": agent_library,
        "stages": stages,
    }


def run_workflow(wf_path: Path, dry_run: bool) -> int:
    """Shell out to `armature run [--dry-run] <wf>`. Returns the runner exit code.

    Raises CabinetError if the armature CLI is not on PATH. Does not import
    armature's runner — only shells out (one-directional boundary preserved).
    """
    if shutil.which("armature") is None:
        raise CabinetError("armature CLI not found; install armature-agents to run a team")
    cmd = ["armature", "run"]
    if dry_run:
        cmd.append("--dry-run")
    cmd.append(str(wf_path))
    return subprocess.run(cmd).returncode
```

- [ ] **Step 4: Export `generate_workflow`, `run_workflow` from `__init__.py`**

Add to `src/armature_cabinet/__init__.py`: `from .team import generate_workflow, run_workflow` (after the library import) and add `"generate_workflow"`, `"run_workflow"` to `__all__`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_team.py -q`
Expected: `3 passed`.

- [ ] **Step 6: Run the full suite + lint**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `68 passed` (65 + 3); ruff clean.

- [ ] **Step 7: Confirm compiler/library untouched**

Run: `git diff --stat <M8-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,scaffold,prompts,library,errors,model}.py`
Expected: empty.

- [ ] **Step 8: Commit**

```bash
git add src/armature_cabinet/team.py src/armature_cabinet/__init__.py tests/test_team.py
git commit -m "feat(team): generate_workflow (pure) + run_workflow (armature handoff) + tests" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: CLI `team` subcommand + CLI tests + integration dry-run

**Files:**
- Modify: `src/armature_cabinet/cli.py` (add `cmd_team` + `team` subparser + top import)
- Modify: `tests/test_team.py` (append CLI tests + integration test)
- Test: `tests/test_team.py`

**Interfaces:**
- Consumes: `generate_workflow`, `run_workflow` from Task 2; `list_agents` from `library` (already imported in cli via M7); `_dump` (existing cli helper).
- Produces: `armature-cabinet team <library> [--agent id]... [--bundles DIR] [--out WF] [--name NAME] [--dry-run | --run]`.

- [ ] **Step 1: Write the failing CLI tests**

Append to `tests/test_team.py`:
```python
import shutil
import yaml

from armature_cabinet.cli import main
from armature_cabinet.library import build_all
from armature_cabinet.scaffold import build_folder

FIX = Path(__file__).parent / "fixtures"


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


def test_cli_team_dry_run_validates_via_armature(tmp_path):
    if not shutil.which("armature"):
        pytest.skip("armature CLI not on PATH")
    dist = tmp_path / "dist"
    build_all(FIX, dist)  # fixtures: security-triage + incident-comms
    wf = tmp_path / "team.yml"
    rc = main(["team", str(FIX), "--bundles", str(dist), "--out", str(wf), "--dry-run"])
    assert rc == 0  # armature run --dry-run validates the 2-stage team
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_team.py -q -k "cli"`
Expected: FAIL — `team` not a known subcommand (argparse SystemExit).

- [ ] **Step 3: Add the CLI wiring to `cli.py`**

In `src/armature_cabinet/cli.py`:

(a) Add to the top imports (after `from .library import list_agents, build_all`):
```python
from .team import generate_workflow, run_workflow
```

(b) Add the `cmd_team` function (after `cmd_list`):
```python
def cmd_team(args: argparse.Namespace) -> int:
    if args.dry_run and args.run:
        print("error: --dry-run and --run are mutually exclusive", file=sys.stderr)
        return 1
    rows = list_agents(args.folder)
    by_id = {r["id"]: r for r in rows}
    if args.agent:
        ordered = []
        for a in args.agent:
            if a not in by_id:
                print(f"error: agent '{a}' not found in library {args.folder}", file=sys.stderr)
                return 1
            ordered.append(a)
    else:
        ordered = sorted(by_id)
    if not ordered:
        print(f"error: no agents found in library {args.folder}", file=sys.stderr)
        return 1
    bundles = Path(args.bundles)
    missing = [a for a in ordered if not (bundles / a / "agent.yaml").exists()]
    if missing:
        print(f"error: missing compiled bundle(s) for: {', '.join(missing)}", file=sys.stderr)
        print(f"       run: armature-cabinet build --all {args.folder} --bundles {bundles}",
              file=sys.stderr)
        return 1
    name = args.name or f"{Path(args.folder).name}-team"
    wf_dict = generate_workflow(ordered, bundles, name)
    out = Path(args.out)
    _dump(wf_dict, out)
    print(f"wrote {out}")
    print(f"  validate: armature run --dry-run {out}")
    print(f"  execute:  armature run {out}")
    if args.dry_run or args.run:
        return run_workflow(out, dry_run=args.dry_run)
    return 0
```

(c) Add the `team` subparser in `main` (after the `list` subparser block, before `args = parser.parse_args(argv)`):
```python
    t = sub.add_parser("team",
                       help="generate a team workflow from a library of agents (hand off to armature run)")
    t.add_argument("folder", help="path to the library directory")
    t.add_argument("--agent", action="append",
                   help="agent id to include, in this order (repeatable; default: all, alphabetical)")
    t.add_argument("--bundles", default="dist",
                   help="directory of compiled bundles (default: dist)")
    t.add_argument("--out", default="team.yml", help="output workflow path (default: team.yml)")
    t.add_argument("--name", help="workflow name (default: <library-dir>-team)")
    t.add_argument("--dry-run", action="store_true",
                   help="validate via armature run --dry-run (no API key needed)")
    t.add_argument("--run", action="store_true",
                   help="execute via armature run (needs a provider/API key)")
    t.set_defaults(func=cmd_team)
```

- [ ] **Step 4: Run the CLI tests**

Run: `python3 -m pytest tests/test_team.py -q -k "cli"`
Expected: `6 passed` (the integration dry-run test runs since `armature` is on PATH in the dev env).

- [ ] **Step 5: Run the full suite + lint**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `74 passed` (68 + 6); ruff clean.

- [ ] **Step 6: Reinstall + smoke-test the CLI**

Run:
```bash
python3 -m pip install -e ".[dev]" -q
armature-cabinet build tests/fixtures --all -o /tmp/m8
armature-cabinet team tests/fixtures --bundles /tmp/m8 --out /tmp/m8/team.yml --dry-run
cat /tmp/m8/team.yml | head -20
```
Expected: `build --all` compiles `security-triage` + `incident-comms` → `/tmp/m8/<id>/agent.yaml`; `team ... --dry-run` prints `wrote /tmp/m8/team.yml` then `armature run --dry-run` output (`Spec 'fixtures-team' is valid (2 stages)` or similar); the `team.yml` shows `agent_library` with both agents + a 2-stage pipeline.

- [ ] **Step 7: Confirm compiler/library untouched**

Run: `git diff --stat <M8-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,scaffold,prompts,library,errors,model}.py`
Expected: empty.

- [ ] **Step 8: Commit**

```bash
git add src/armature_cabinet/cli.py tests/test_team.py
git commit -m "feat(cli): team — generate a team workflow + hand off to armature run" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 9: Final repo check**

Run:
```bash
git log --oneline | head -5
git status -s
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: the 3 M8 commits on top of the M8 docs commit, clean tree, `74 passed`, ruff clean.