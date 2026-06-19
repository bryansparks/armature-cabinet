# armature-cabinet Milestone 7 — Agent library management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `armature-cabinet list <dir>` (enumerate agents) and `armature-cabinet build <dir> --all` (bulk-compile every agent in a library directory), with per-agent continue-on-failure.

**Architecture:** A new `library.py` (`list_agents` + `build_all`, reusing the unchanged compile/validate) + CLI additions (`--all` on `build`, a `list` subcommand with a rich table). The compiler is unchanged.

**Tech Stack:** Python ≥3.11, pyyaml, rich (table for `list`), pytest. Existing deps.

## Global Constraints

Copied verbatim from the approved M7 spec; every task inherits these.
- Runtime deps `armature-agents>=0.3.5`, `pyyaml>=6.0`, `rich>=13.0`, `questionary>=2.0`. ruff dev-only. `requires-python = ">=3.11"`.
- **M7 does not modify the compiler:** `loader.py`/`compiler.py`/`validate.py`/`select.py`/`scaffold.py`/`prompts.py`/`errors.py`/`model.py` untouched. Only `library.py` (new), `cli.py` (`--all` + `list`), `__init__.py` (export), `tests/test_library.py` (new) change. `git diff <M7-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,scaffold,prompts,errors,model}.py` must be empty.
- `list_agents`/`build_all` reuse the existing compile/validate; they never raise out (load/validate failures captured per-agent). `build_all` continues on per-agent failure. No LLM, no network.
- Existing 57 tests + ruff + e2e stay green.

---

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `src/armature_cabinet/library.py` | `list_agents(library_dir)` + `build_all(library_dir, out_dir, no_safety)` — enumerate + bulk-compile | NEW |
| `src/armature_cabinet/cli.py` | add `--all` to `build` + `list` subcommand (rich table) | MODIFY |
| `src/armature_cabinet/__init__.py` | export `list_agents`, `build_all` | MODIFY |
| `tests/test_library.py` | function tests + CLI tests (enumerate/skip/broken-continue/exit codes) | NEW |
| compiler modules | **unchanged** | untouched |

---

## Task 1: Commit M7 spec + plan docs

**Files:** Create the M7 spec + plan (already written). Test: none (setup).

- [ ] **Step 1: Verify the docs exist**

Run:
```bash
ls docs/superpowers/specs/2026-06-19-armature-cabinet-milestone-7-design.md docs/superpowers/plans/2026-06-19-armature-cabinet-milestone-7.md
```
Expected: both listed.

- [ ] **Step 2: Confirm baseline green + lint clean**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `57 passed`; ruff clean.

- [ ] **Step 3: Commit the docs**

Run:
```bash
git add docs/superpowers/specs/2026-06-19-armature-cabinet-milestone-7-design.md docs/superpowers/plans/2026-06-19-armature-cabinet-milestone-7.md
git commit -m "docs: milestone-7 design + implementation plan" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git rev-parse HEAD
```
Expected: commit created; **record the printed HEAD sha** — this is the M7 base.

---

## Task 2: `library.py` + `test_library.py` (function tests)

**Files:**
- Create: `src/armature_cabinet/library.py`
- Modify: `src/armature_cabinet/__init__.py` (export `list_agents`, `build_all`)
- Test: `tests/test_library.py` (function-level tests; CLI tests appended in Task 3)

**Interfaces:**
- Consumes: `load_package`, `validate_package`, `compile_agent`, `compile_safety_fragment` (unchanged); `scaffold.build_folder` (for tests to make agents).
- Produces: `list_agents(library_dir) -> list[dict]` and `build_all(library_dir, out_dir, no_safety=False) -> tuple[list[Path], list[str]]`. Task 3's CLI calls these.

- [ ] **Step 1: Write the failing function tests**

Create `tests/test_library.py`:
```python
import yaml
from pathlib import Path

from armature_cabinet import load_package, validate_package
from armature_cabinet.library import list_agents, build_all
from armature_cabinet.scaffold import build_folder


def _lib(tmp_path):
    """A library with two agents + a non-agent subdir."""
    lib = tmp_path / "agents"
    lib.mkdir()
    build_folder({"id": "alpha", "kind": "partner", "role": "Alpha", "skills": []}, lib)
    build_folder({"id": "beta", "kind": "partner", "role": "Beta", "skills": []}, lib)
    (lib / "not-an-agent").mkdir()
    (lib / "not-an-agent" / "readme.txt").write_text("ignore me")
    return lib


def test_list_agents_enumerates_and_skips_non_agents(tmp_path):
    rows = list_agents(_lib(tmp_path))
    assert [r["id"] for r in rows] == ["alpha", "beta"]  # sorted; non-agent skipped
    assert rows[0]["name"] == "alpha" and rows[0]["kind"] == "partner"
    assert rows[0]["skills"] == 0 and rows[0]["valid"] is True


def test_list_agents_reports_invalid_without_raising(tmp_path):
    lib = tmp_path / "agents"
    lib.mkdir()
    (lib / "broken").mkdir()
    (lib / "broken" / "cabinet.yaml").write_text(
        "id: broken\nname: Broken\nkind: partner\nschema_version: '0.1.0'\n")
    (lib / "broken" / "soul.md").write_text("---\nrole: R\n---\nbody\n")
    (lib / "broken" / "skills").mkdir()
    (lib / "broken" / "skills" / "a.md").write_text("---\nid: dup\n---\nb\n")
    (lib / "broken" / "skills" / "b.md").write_text("---\nid: dup\n---\nb\n")
    rows = list_agents(lib)
    assert len(rows) == 1 and rows[0]["id"] == "broken"
    assert rows[0]["valid"] is False
    assert any("duplicate" in e for e in rows[0]["errors"])


def test_build_all_compiles_each_agent(tmp_path):
    out = tmp_path / "dist"
    bundles, errors = build_all(_lib(tmp_path), out)
    assert not errors and len(bundles) == 2
    for b in bundles:
        assert b.exists()
        bundle = yaml.safe_load(b.read_text())
        assert "role" in bundle and "skill_library" in bundle


def test_build_all_skips_non_agent_and_continues_on_failure(tmp_path):
    lib = tmp_path / "agents"
    lib.mkdir()
    build_folder({"id": "good", "kind": "partner", "role": "G", "skills": []}, lib)
    (lib / "bad").mkdir()
    (lib / "bad" / "cabinet.yaml").write_text("id: bad\nname: Bad\nkind: weird\n")  # invalid kind
    (lib / "bad" / "soul.md").write_text("---\nrole: R\n---\nbody\n")
    out = tmp_path / "dist"
    bundles, errors = build_all(lib, out)
    assert len(bundles) == 1 and bundles[0].name == "agent.yaml"  # good compiled
    assert len(errors) == 1 and "bad" in errors[0]
    assert not (out / "bad").exists()  # bad not compiled
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_library.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'armature_cabinet.library'`.

- [ ] **Step 3: Create `src/armature_cabinet/library.py`**

```python
"""Agent library management: enumerate + bulk-compile a directory of agents."""
from __future__ import annotations
from pathlib import Path

import yaml

from .loader import load_package
from .validate import validate_package
from .compiler import compile_agent, compile_safety_fragment

_YAML = dict(sort_keys=False, default_flow_style=False, width=100)


def _agent_dirs(library_dir):
    """Subdirectories of library_dir that contain cabinet.yaml, sorted by name."""
    root = Path(library_dir)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a library directory: {root}")
    return [d for d in sorted(root.iterdir()) if d.is_dir() and (d / "cabinet.yaml").exists()]


def list_agents(library_dir) -> list[dict]:
    """Enumerate agents in library_dir; return [{id,name,kind,skills,valid,errors}] sorted by id.

    Never raises: load/validate failures are captured per-agent as valid=False + errors.
    """
    rows: list[dict] = []
    for d in _agent_dirs(library_dir):
        row = {"id": d.name, "name": d.name, "kind": "?", "skills": 0, "valid": False, "errors": []}
        try:
            pkg = load_package(d)
            r = validate_package(pkg)
            row.update({"name": pkg.name, "kind": pkg.kind, "skills": len(pkg.skills),
                        "valid": r.ok, "errors": list(r.errors)})
        except Exception as e:  # CabinetError or other load failure -> not fatal
            row["errors"] = [str(e)]
        rows.append(row)
    rows.sort(key=lambda r: r["id"])
    return rows


def build_all(library_dir, out_dir, no_safety=False) -> tuple[list[Path], list[str]]:
    """Compile every agent in library_dir to <out_dir>/<id>/.

    Returns (compiled bundle paths, per-agent error messages). Continues on
    per-agent failure (compiles as many as possible); does not abort on the first.
    """
    out = Path(out_dir)
    bundles: list[Path] = []
    errors: list[str] = []
    for d in _agent_dirs(library_dir):
        try:
            pkg = load_package(d)
            r = validate_package(pkg)
            if not r.ok:
                errors.append(f"{d.name}: " + "; ".join(r.errors))
                continue
            bundle = compile_agent(pkg)
            bdir = out / pkg.id
            bdir.mkdir(parents=True, exist_ok=True)
            (bdir / "agent.yaml").write_text(yaml.safe_dump(bundle, **_YAML), encoding="utf-8")
            if not no_safety:
                frag = compile_safety_fragment(pkg)
                if len(frag) > 1:
                    (bdir / f"{pkg.id}.safety.yaml").write_text(
                        yaml.safe_dump(frag, **_YAML), encoding="utf-8")
            bundles.append(bdir / "agent.yaml")
        except Exception as e:  # CabinetError or other failure -> report, keep going
            errors.append(f"{d.name}: {e}")
    return bundles, errors
```

- [ ] **Step 4: Export `list_agents`, `build_all` from `__init__.py`**

Add to `src/armature_cabinet/__init__.py`: `from .library import list_agents, build_all` (after the scaffold import) and add `"list_agents"`, `"build_all"` to `__all__`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_library.py -q`
Expected: `4 passed`.

- [ ] **Step 6: Run the full suite + lint**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `61 passed` (57 + 4); ruff clean.

- [ ] **Step 7: Confirm compiler untouched**

Run: `git diff --stat <M7-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,scaffold,prompts,errors,model}.py`
Expected: empty.

- [ ] **Step 8: Commit**

```bash
git add src/armature_cabinet/library.py src/armature_cabinet/__init__.py tests/test_library.py
git commit -m "feat(library): list_agents + build_all (enumerate + bulk-compile a library)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: CLI `--all` + `list` subcommand + CLI tests

**Files:**
- Modify: `src/armature_cabinet/cli.py` (add `--all` to `build`, `list` subcommand, `from .library import ...`)
- Modify: `tests/test_library.py` (append CLI tests)
- Test: `tests/test_library.py`

**Interfaces:**
- Consumes: `list_agents`, `build_all` from Task 2.
- Produces: `armature-cabinet list <dir>` (rich table; exit 0 all-valid / 1 any-invalid) and `armature-cabinet build <dir> --all [--out DIR] [--no-safety]` (compile every agent; continue-on-failure; exit 0/1).

- [ ] **Step 1: Write the failing CLI tests**

Append to `tests/test_library.py`:
```python
from armature_cabinet.cli import main


def test_cli_list_exits_0_when_all_valid(tmp_path, capsys):
    lib = _lib(tmp_path)
    rc = main(["list", str(lib)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "alpha" in out and "beta" in out


def test_cli_build_all_compiles(tmp_path):
    lib = _lib(tmp_path)
    out = tmp_path / "dist"
    rc = main(["build", str(lib), "--all", "-o", str(out)])
    assert rc == 0
    assert (out / "alpha" / "agent.yaml").exists()
    assert (out / "beta" / "agent.yaml").exists()


def test_cli_build_all_nonzero_on_failure(tmp_path):
    lib = tmp_path / "agents"
    lib.mkdir()
    build_folder({"id": "good", "kind": "partner", "role": "G", "skills": []}, lib)
    (lib / "bad").mkdir()
    (lib / "bad" / "cabinet.yaml").write_text("id: bad\nkind: weird\n")
    out = tmp_path / "dist"
    rc = main(["build", str(lib), "--all", "-o", str(out)])
    assert rc == 1
    assert (out / "good" / "agent.yaml").exists()  # good still compiled
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_library.py -q -k "cli"`
Expected: FAIL — `--all` unknown / `list` not a subcommand (argparse SystemExit).

- [ ] **Step 3: Add the CLI wiring to `cli.py`**

In `src/armature_cabinet/cli.py`:

(a) Add to the top imports (after `from .scaffold import build_folder`):
```python
from .library import list_agents, build_all
```

(b) Add a `_cmd_build_all` helper + branch at the top of `cmd_build`. Insert this function before `cmd_build`:
```python
def _cmd_build_all(args: argparse.Namespace) -> int:
    out_dir = Path(args.out) if args.out else Path("dist")
    bundles, errors = build_all(args.folder, out_dir, no_safety=args.no_safety)
    for bp in bundles:
        print(f"compiled -> {bp}")
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    tail = f"compiled {len(bundles)} agent(s)"
    if errors:
        tail += f", {len(errors)} error(s)"
    print(tail)
    return 1 if errors else 0
```
And at the very top of `cmd_build`, add:
```python
    if getattr(args, "all", False):
        return _cmd_build_all(args)
```

(c) Add a `cmd_list` function (after `cmd_new`):
```python
def cmd_list(args: argparse.Namespace) -> int:
    from rich.console import Console
    from rich.table import Table

    rows = list_agents(args.folder)
    if not rows:
        print("(no agents found)")
        return 0
    table = Table(title=str(args.folder))
    for col in ["ID", "NAME", "KIND", "SKILLS", "VALID"]:
        table.add_column(col)
    for r in rows:
        table.add_row(r["id"], r["name"], r["kind"], str(r["skills"]),
                      "ok" if r["valid"] else f"FAIL ({len(r['errors'])})")
    Console().print(table)
    return 0 if all(r["valid"] for r in rows) else 1
```

(d) Add the `--all` flag to the `build` subparser and a `list` subparser in `main`. On the existing `build` subparser (`b`), after its existing args, add:
```python
    b.add_argument("--all", action="store_true",
                   help="compile every agent folder in the given library directory")
```
And add a `list` subparser (after the `new` subparser block, before `args = parser.parse_args(argv)`):
```python
    lst = sub.add_parser("list", help="enumerate agents in a library directory")
    lst.add_argument("folder", help="path to the library directory")
    lst.set_defaults(func=cmd_list)
```

- [ ] **Step 4: Run the CLI tests**

Run: `python3 -m pytest tests/test_library.py -q -k "cli"`
Expected: `3 passed`.

- [ ] **Step 5: Run the full suite + lint**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `64 passed` (61 + 3); ruff clean.

- [ ] **Step 6: Reinstall + smoke-test the CLI**

Run:
```bash
python3 -m pip install -e ".[dev]" -q
armature-cabinet list examples
armature-cabinet build examples --all -o /tmp/m7-lib
ls /tmp/m7-lib
armature-cabinet build examples --all -o /tmp/m7-lib 2>&1 | tail -1
```
Expected: `list examples` prints a rich table with `security-triage` + `incident-comms` (both `ok`), exit 0; `build --all` compiles both → `/tmp/m7-lib/security-triage/agent.yaml` + `/tmp/m7-lib/incident-comms/agent.yaml`; the last line prints `compiled 2 agent(s)`. (Re-running overwrites the same outputs — `bdir.mkdir(exist_ok=True)` + write_text overwrites; no `FileExistsError` for build_all.)

- [ ] **Step 7: Confirm compiler untouched**

Run: `git diff --stat <M7-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,scaffold,prompts,errors,model}.py`
Expected: empty.

- [ ] **Step 8: Commit**

```bash
git add src/armature_cabinet/cli.py tests/test_library.py
git commit -m "feat(cli): build --all + list (agent library management)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 9: Final repo check**

Run:
```bash
git log --oneline | head -5
git status -s
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: the 3 M7 commits on top of the M7 docs commit, clean tree, `64 passed`, ruff clean.