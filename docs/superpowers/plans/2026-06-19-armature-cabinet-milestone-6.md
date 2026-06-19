# armature-cabinet Milestone 6 — Authoring wizard (`new`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `armature-cabinet new [id] [--out DIR]` — an interactive (questionary + rich) wizard that builds a complete, valid cabinet agent folder, then validates it and offers to build the bundle.

**Architecture:** A pure `scaffold.py` (`build_folder(answers, out_dir) -> Path`, answers dict → files, unit-testable) + an interactive `prompts.py` (`collect_answers(id) -> dict`, questionary/rich) + a `new` subcommand in `cli.py` that wires them, validates, and offers to build. `prompts` is lazily imported inside `cmd_new`; `__init__` exports only `scaffold` — so importing the package never pulls questionary (keeps the CI build job's `--no-deps` wheel-import working). The compiler (`loader`/`compiler`/`validate`/`select`/`errors`/`model`) is unchanged.

**Tech Stack:** Python ≥3.11, pyyaml, `rich>=13.0`, `questionary>=2.0` (new core deps), pytest. armature-agents≥0.3.5.

## Global Constraints

Copied verbatim from the approved M6 spec; every task inherits these.
- Runtime deps become `armature-agents>=0.3.5`, `pyyaml>=6.0`, `rich>=13.0`, `questionary>=2.0`. `requires-python = ">=3.11"`. ruff dev-only.
- **M6 does not modify the compiler:** `loader.py`, `compiler.py`, `validate.py`, `select.py`, `errors.py`, `model.py` are untouched. `git diff <M6-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,errors,model}.py` must be empty.
- **`scaffold.build_folder` is pure** (answers dict → files; no prompting, no reading, only writing). `prompts` is the only interactive surface and the only place that imports questionary. **`__init__` exports `scaffold` only (not `prompts`)**; `cli.cmd_new` does `from .prompts import collect_answers` lazily — so `import armature_cabinet` and `armature-cabinet build/validate` never import questionary.
- The wizard's output folder must pass `validate_package` and compile (a 0-skill folder is valid, per M1). Soft/hard guardrail split, `x_`-metadata rules, `cabinet.yaml`(source)/`agent.yaml`(output) naming, one-directional boundary all hold.
- No LLM in the wizard (interactive-only for v1).
- Existing 47 tests + ruff + e2e stay green.

---

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `src/armature_cabinet/scaffold.py` | `slugify` + `build_folder(answers, out_dir)` — pure answers→files | NEW |
| `src/armature_cabinet/prompts.py` | `collect_answers(id) -> dict` — interactive questionary/rich | NEW |
| `src/armature_cabinet/cli.py` | add `new` subcommand (`cmd_new`) wiring prompts→scaffold→validate→build-offer | MODIFY |
| `src/armature_cabinet/__init__.py` | export `build_folder`, `slugify` (scaffold only, NOT prompts) | MODIFY |
| `pyproject.toml` | add `rich>=13.0`, `questionary>=2.0` to `dependencies` | MODIFY |
| `tests/test_scaffold.py` | deterministic tests of `build_folder`/`slugify` (full/minimal/omitted/no-skills/context-stub/exists) | NEW |
| `tests/test_wizard_cli.py` | monkeypatch `collect_answers` → scripted dict; assert `new` writes a valid folder | NEW |
| `src/armature_cabinet/{loader,compiler,validate,select,errors,model}.py` | **unchanged** | untouched |

---

## Task 1: Commit M6 spec + plan docs

**Files:**
- Create: `docs/superpowers/specs/2026-06-19-armature-cabinet-milestone-6-design.md` (already written)
- Create: `docs/superpowers/plans/2026-06-19-armature-cabinet-milestone-6.md` (this file)
- Test: none (setup)

**Interfaces:**
- Produces: a git commit of the M6 spec + plan; the post-commit HEAD is the **M6 base** for the no-compiler-changes proof.

- [ ] **Step 1: Verify the docs exist**

Run:
```bash
ls docs/superpowers/specs/2026-06-19-armature-cabinet-milestone-6-design.md docs/superpowers/plans/2026-06-19-armature-cabinet-milestone-6.md
```
Expected: both files listed.

- [ ] **Step 2: Confirm baseline green + lint clean**

Run:
```bash
python3 -m pip install -e ".[dev]" -q
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `47 passed`; ruff clean.

- [ ] **Step 3: Commit the docs**

Run:
```bash
git add docs/superpowers/specs/2026-06-19-armature-cabinet-milestone-6-design.md docs/superpowers/plans/2026-06-19-armature-cabinet-milestone-6.md
git commit -m "docs: milestone-6 design + implementation plan" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git rev-parse HEAD
```
Expected: commit created; **record the printed HEAD sha** — this is the M6 base.

---

## Task 2: `scaffold.py` (pure) + `test_scaffold.py`

**Files:**
- Create: `src/armature_cabinet/scaffold.py`
- Modify: `src/armature_cabinet/__init__.py` (export `build_folder`, `slugify` only — NOT prompts)
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Produces: `slugify(name: str) -> str` and `build_folder(answers: dict, out_dir: Path) -> Path` (pure: writes the agent folder; raises `FileExistsError` if the folder exists). `answers` schema is the dict in the spec. Task 3's `cmd_new` calls `build_folder`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scaffold.py`:
```python
from pathlib import Path

import pytest

from armature_cabinet import load_package, validate_package, compile_agent
from armature_cabinet.scaffold import build_folder, slugify


def _full_answers():
    return {
        "id": "demo-agent", "name": "Demo Agent", "kind": "partner",
        "summary": "A demo agent.", "schema_version": "0.1.0",
        "role": "Demo specialist", "expertise": ["alpha", "beta"],
        "temperament": "calm", "standards": ["be clear"],
        "refusals": ["never lie"], "soul_body": "You are a demo agent.",
        "armature_role_type": None,
        "goal": "Demo things well.", "success_looks_like": ["x done"],
        "out_of_scope": ["y"], "mandate_body": "Because demos.",
        "brakes": {"cost_ceiling_usd": 1.0, "max_iterations": 5,
                   "forbidden_actions": ["slack:post"], "halt_and_ask_when": ["unsure"], "body": ""},
        "trust": {"show_work": "required", "cite_sources": "required",
                  "uncertainty": "must_flag", "escalate_when": ["conf<0.6"]},
        "skills": [
            {"id": "demo.do-thing", "name": "do-thing", "when": "A thing needs doing.",
             "tools": ["tool:run"], "context": ["context/rubric.md"], "cost_tier": "T2",
             "version": "0.1.0", "outputs": "Result[]", "body": "1. Do the thing."},
        ],
    }


def test_slugify():
    assert slugify("Do The Thing!") == "do-the-thing"
    assert slugify("appsec.rank-findings") == "appsec.rank-findings"
    assert slugify("   ") == "skill"


def test_build_full_folder_validates_and_compiles(tmp_path):
    root = build_folder(_full_answers(), tmp_path)
    assert root == tmp_path / "demo-agent"
    for f in ["cabinet.yaml", "soul.md", "mandate.md", "brakes.md", "trust.yaml",
              "skills/do-thing.md", "context/rubric.md", "README.md"]:
        assert (root / f).exists(), f
    pkg = load_package(root)
    assert pkg.id == "demo-agent" and pkg.kind == "partner" and len(pkg.skills) == 1
    r = validate_package(pkg)
    assert r.ok, r.errors
    b = compile_agent(pkg)
    assert b["role"]["name"] == "Demo Agent"
    assert b["role"]["skills"] == ["demo.do-thing"]
    assert "rubric" in b["skill_library"]["demo.do-thing"]["x_context"]["context/rubric.md"]
    assert b["skill_library"]["demo.do-thing"]["x_outputs"] == "Result[]"


def test_build_minimal_folder_validates_and_compiles(tmp_path):
    root = build_folder({"id": "min", "kind": "partner", "role": "Minimal", "skills": []}, tmp_path)
    pkg = load_package(root)
    assert pkg.id == "min" and pkg.skills == []
    assert validate_package(pkg).ok
    b = compile_agent(pkg)
    assert b["role"]["skills"] == [] and b["skill_library"] == {}


def test_omitted_blocks_produce_no_file(tmp_path):
    root = build_folder({"id": "nobrakes", "kind": "partner", "role": "R",
                          "brakes": None, "trust": None, "skills": []}, tmp_path)
    assert not (root / "brakes.md").exists()
    assert not (root / "trust.yaml").exists()
    assert not (root / "mandate.md").exists()  # no mandate fields -> none written
    assert validate_package(load_package(root)).ok


def test_no_skills_creates_no_skills_or_context_dir(tmp_path):
    root = build_folder({"id": "noskills", "kind": "partner", "role": "R", "skills": []}, tmp_path)
    assert not (root / "skills").exists()
    assert not (root / "context").exists()


def test_existing_folder_raises(tmp_path):
    build_folder({"id": "x", "kind": "partner", "role": "R", "skills": []}, tmp_path)
    with pytest.raises(FileExistsError):
        build_folder({"id": "x", "kind": "partner", "role": "R", "skills": []}, tmp_path)


def test_context_stub_created_for_ref(tmp_path):
    root = build_folder({"id": "c", "kind": "partner", "role": "R",
        "skills": [{"id": "c.s", "name": "s", "when": "w", "tools": [], "context": ["context/r.md"],
                    "cost_tier": None, "version": "0.1.0", "outputs": None, "body": "b"}]}, tmp_path)
    assert "TODO" in (root / "context" / "r.md").read_text()
    assert validate_package(load_package(root)).ok
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_scaffold.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'armature_cabinet.scaffold'`.

- [ ] **Step 3: Create `src/armature_cabinet/scaffold.py`**

```python
"""Scaffold a cabinet agent folder from an answers dict (pure: no prompting)."""
from __future__ import annotations
import re
from pathlib import Path

import yaml

_FM_SEP = "---\n"


def slugify(name: str) -> str:
    """Make a safe filename from a skill name/id segment."""
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-_.")
    return s or "skill"


def _yaml_block(meta: dict) -> str:
    return _FM_SEP + yaml.safe_dump(meta, sort_keys=False, default_flow_style=False,
                                    width=100).strip() + "\n---\n"


def _listify(items) -> list[str]:
    return [str(i) for i in (items or []) if i]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


def build_folder(answers: dict, out_dir: Path) -> Path:
    """Write a complete cabinet agent folder from an answers dict. Pure (only writes files).

    Raises ``FileExistsError`` if the target folder already exists.
    """
    root = Path(out_dir) / answers["id"]
    if root.exists():
        raise FileExistsError(f"agent folder already exists: {root}")

    # cabinet.yaml
    cabinet = {
        "schema_version": answers.get("schema_version") or "0.1.0",
        "id": answers["id"],
        "name": answers.get("name") or answers["id"],
        "kind": answers.get("kind") or "partner",
    }
    if answers.get("summary"):
        cabinet["summary"] = answers["summary"]
    blocks = {"soul": "soul.md"}
    has_mandate = any([answers.get("goal"), answers.get("success_looks_like"),
                       answers.get("out_of_scope"), answers.get("mandate_body")])
    if has_mandate:
        blocks["mandate"] = "mandate.md"
    cabinet["blocks"] = blocks
    blocks_extra: dict = {}
    if answers.get("brakes") is not None:
        blocks_extra["brakes"] = "brakes.md"
    if answers.get("trust") is not None:
        blocks_extra["trust"] = "trust.yaml"
    if answers.get("skills"):
        blocks_extra["skills"] = "skills/"
        blocks_extra["context"] = "context/"
    if blocks_extra:
        cabinet["blocks_extra"] = blocks_extra
    _write(root / "cabinet.yaml", yaml.safe_dump(cabinet, sort_keys=False,
            default_flow_style=False, width=100))

    # soul.md
    soul_meta = {"type": answers.get("kind") or "partner", "role": answers["role"]}
    if answers.get("expertise"):
        soul_meta["expertise"] = _listify(answers["expertise"])
    if answers.get("temperament"):
        soul_meta["temperament"] = answers["temperament"]
    if answers.get("standards"):
        soul_meta["standards"] = _listify(answers["standards"])
    if answers.get("refusals"):
        soul_meta["refusals"] = _listify(answers["refusals"])
    if answers.get("armature_role_type"):
        soul_meta["armature_role_type"] = answers["armature_role_type"]
    soul = _yaml_block(soul_meta)
    if answers.get("soul_body"):
        soul += answers["soul_body"].strip() + "\n"
    _write(root / "soul.md", soul)

    # mandate.md (only if any mandate field is non-empty)
    if has_mandate:
        man_meta: dict = {}
        if answers.get("goal"):
            man_meta["goal"] = answers["goal"]
        if answers.get("success_looks_like"):
            man_meta["success_looks_like"] = _listify(answers["success_looks_like"])
        if answers.get("out_of_scope"):
            man_meta["out_of_scope"] = _listify(answers["out_of_scope"])
        mandate = _yaml_block(man_meta)
        if answers.get("mandate_body"):
            mandate += answers["mandate_body"].strip() + "\n"
        _write(root / "mandate.md", mandate)

    # brakes.md (only if the block was provided)
    bk = answers.get("brakes")
    if bk is not None:
        bk_meta: dict = {}
        if bk.get("cost_ceiling_usd") is not None:
            bk_meta["cost_ceiling_usd"] = bk["cost_ceiling_usd"]
        if bk.get("max_iterations") is not None:
            bk_meta["max_iterations"] = bk["max_iterations"]
        if bk.get("forbidden_actions"):
            bk_meta["forbidden_actions"] = _listify(bk["forbidden_actions"])
        if bk.get("halt_and_ask_when"):
            bk_meta["halt_and_ask_when"] = _listify(bk["halt_and_ask_when"])
        brakes = _yaml_block(bk_meta)
        if bk.get("body"):
            brakes += bk["body"].strip() + "\n"
        _write(root / "brakes.md", brakes)

    # trust.yaml (only if the block was provided)
    tr = answers.get("trust")
    if tr is not None:
        trust: dict = {}
        if tr.get("show_work"):
            trust["show_work"] = tr["show_work"]
        if tr.get("cite_sources"):
            trust["cite_sources"] = tr["cite_sources"]
        if tr.get("uncertainty"):
            trust["uncertainty"] = tr["uncertainty"]
        if tr.get("escalate_when"):
            trust["escalate_when"] = _listify(tr["escalate_when"])
        _write(root / "trust.yaml", yaml.safe_dump(trust, sort_keys=False,
                default_flow_style=False, width=100))

    # skills/*.md + collect context refs
    context_refs: set[str] = set()
    for sk in answers.get("skills") or []:
        sid = sk["id"]
        name = sk.get("name") or sid.rsplit(".", 1)[-1]
        slug = slugify(name)
        sk_meta: dict = {"id": sid, "version": sk.get("version") or "0.1.0"}
        if sk.get("name"):
            sk_meta["name"] = sk["name"]
        if sk.get("when"):
            sk_meta["when"] = sk["when"]
        if sk.get("tools"):
            sk_meta["tools"] = _listify(sk["tools"])
        if sk.get("context"):
            sk_meta["context"] = _listify(sk["context"])
            context_refs.update(_listify(sk["context"]))
        if sk.get("cost_tier"):
            sk_meta["cost_tier"] = sk["cost_tier"]
        if sk.get("outputs"):
            sk_meta["outputs"] = sk["outputs"]
        body = (sk.get("body") or "").strip()
        _write(root / "skills" / f"{slug}.md", _yaml_block(sk_meta) + (body + "\n" if body else ""))

    # context/*.md stubs for each referenced ref
    for ref in sorted(context_refs):
        cpath = root / ref
        if not cpath.exists():
            _write(cpath, f"# {cpath.stem}\n\n<!-- TODO: fill in the reference material "
                          f"referenced by a skill. -->\n")

    # README.md
    readme = f"# {cabinet['name']}\n"
    if answers.get("summary"):
        readme += f"\n{answers['summary']}\n"
    _write(root / "README.md", readme)

    return root
```

- [ ] **Step 4: Export `build_folder` + `slugify` (scaffold only, NOT prompts)**

In `src/armature_cabinet/__init__.py`, add the scaffold import + `__all__` entries. Do NOT add `prompts` (Task 3 creates it; it must stay lazily-imported by `cli`). The file becomes:
```python
"""armature-cabinet — compile cabinet agent folders into Armature agent bundles."""
from .errors import CabinetError
from .loader import load_package
from .compiler import compile_agent, compile_safety_fragment, compose_description
from .validate import validate_package
from .select import select_skills
from .scaffold import build_folder, slugify

__all__ = [
    "CabinetError",
    "load_package",
    "compile_agent",
    "compile_safety_fragment",
    "compose_description",
    "validate_package",
    "select_skills",
    "build_folder",
    "slugify",
]
__version__ = "0.1.0"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_scaffold.py -q`
Expected: `7 passed`.

- [ ] **Step 6: Run the full suite + lint**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `54 passed` (47 + 7); ruff clean.

- [ ] **Step 7: Confirm compiler modules untouched**

Run: `git diff --stat <M6-base>..HEAD -- src/armature_cabinet/loader.py src/armature_cabinet/compiler.py src/armature_cabinet/validate.py src/armature_cabinet/select.py src/armature_cabinet/errors.py src/armature_cabinet/model.py`
Expected: empty (no output).

- [ ] **Step 8: Commit**

```bash
git add src/armature_cabinet/scaffold.py src/armature_cabinet/__init__.py tests/test_scaffold.py
git commit -m "feat(scaffold): pure build_folder(answers->folder) + slugify + tests" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: `prompts.py` + `cli.py new` + deps + `test_wizard_cli.py`

**Files:**
- Create: `src/armature_cabinet/prompts.py`
- Modify: `src/armature_cabinet/cli.py` (add `cmd_new` + `new` subparser + top import of `build_folder`)
- Modify: `pyproject.toml` (add `rich>=13.0`, `questionary>=2.0` to `dependencies`)
- Test: `tests/test_wizard_cli.py`

**Interfaces:**
- Consumes: `build_folder` from Task 2; `load_package`/`validate_package`/`compile_agent`/`compile_safety_fragment`/`_dump`/`_report` (existing in `cli.py`).
- Produces: `collect_answers(id) -> dict` (interactive) and the `armature-cabinet new [id] [--out DIR]` command.

- [ ] **Step 1: Add the deps to `pyproject.toml`**

In `pyproject.toml`, change:
```toml
dependencies = [
    "armature-agents>=0.3.5",
    "pyyaml>=6.0",
]
```
to:
```toml
dependencies = [
    "armature-agents>=0.3.5",
    "pyyaml>=6.0",
    "rich>=13.0",
    "questionary>=2.0",
]
```

- [ ] **Step 2: Write the failing CLI test**

Create `tests/test_wizard_cli.py`:
```python
from armature_cabinet.cli import main
import armature_cabinet.prompts as prompts
from armature_cabinet import load_package, validate_package


def _full_answers():
    return {
        "id": "wiz-demo", "name": "Wiz Demo", "kind": "partner",
        "summary": "wizard smoke", "schema_version": "0.1.0",
        "role": "Demo", "expertise": [], "temperament": "", "standards": [],
        "refusals": [], "soul_body": "", "armature_role_type": None,
        "goal": "", "success_looks_like": [], "out_of_scope": [], "mandate_body": "",
        "brakes": None, "trust": None,
        "skills": [{"id": "wiz.s", "name": "s", "when": "w", "tools": [],
                     "context": [], "cost_tier": None, "version": "0.1.0",
                     "outputs": None, "body": "do"}],
    }


def test_new_writes_valid_folder(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(prompts, "collect_answers", lambda id_: _full_answers())
    rc = main(["new", "wiz-demo", "--out", str(tmp_path)])
    assert rc == 0
    root = tmp_path / "wiz-demo"
    assert (root / "cabinet.yaml").exists()
    assert (root / "skills" / "s.md").exists()
    assert validate_package(load_package(root)).ok
    out = capsys.readouterr().out
    assert "created" in out.lower() and "wiz-demo" in out
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_wizard_cli.py -q`
Expected: FAIL — `prompts` module missing / `new` not a known subcommand (argparse SystemExit).

- [ ] **Step 4: Create `src/armature_cabinet/prompts.py`**

```python
"""Interactive prompts that collect a cabinet agent's answers (questionary + rich).

The only module that imports questionary. Imported lazily by ``cli.cmd_new`` so
that ``import armature_cabinet`` and the build/validate commands never pull it in.
"""
from __future__ import annotations

import questionary
from rich.console import Console
from rich.panel import Panel

console = Console()

_KINDS = ["partner", "clone"]
_ROLE_TYPES = ["worker", "orchestrator", "judge", "researcher"]
_COST_TIERS = ["T1", "T2", "T3"]


def _section(title: str) -> None:
    console.print(Panel.fit(title, style="bold cyan"))


def _text(msg: str, default: str = "") -> str:
    return questionary.text(msg + ": ", default=default).ask() or ""


def _req_text(msg: str, default: str = "") -> str:
    while True:
        v = questionary.text(msg + ": ", default=default).ask()
        if v and v.strip():
            return v.strip()
        console.print("[red]Required — please enter a value.[/red]")


def _list(msg: str) -> list[str]:
    out: list[str] = []
    while True:
        v = questionary.text(f"{msg} (blank to finish): ").ask()
        if not v or not v.strip():
            break
        out.append(v.strip())
    return out


def _multiline(msg: str) -> str:
    console.print(f"{msg} (enter lines; blank line to finish):")
    lines: list[str] = []
    while True:
        v = input("... ")
        if not v.strip():
            break
        lines.append(v)
    return "\n".join(lines)


def _select(msg: str, choices: list[str], default: str | None = None) -> str:
    return questionary.select(msg, choices=choices, default=default).ask()


def _confirm(msg: str, default: bool = False) -> bool:
    return bool(questionary.confirm(msg, default=default).ask())


def collect_answers(id_: str | None = None) -> dict:
    """Walk the author through every cabinet field; return the answers dict."""
    _section("Identity")
    aid = id_ or _req_text("Agent id (folder name)")
    name = _text("Display name", default=aid)
    kind = _select("Kind", _KINDS, default="partner")
    summary = _text("One-line summary (optional)")
    schema_version = _text("schema_version", default="0.1.0")

    _section("Soul — identity")
    role = _req_text("Role (one line)")
    expertise = _list("Expertise area")
    temperament = _text("Temperament (optional)")
    standards = _list("Standard you hold to")
    refusals = _list("Refusal (you will not)")
    soul_body = _multiline("Voice / soul body (optional)")
    rtype = _select("armature_role_type override",
                    ["(skip — default from kind)"] + _ROLE_TYPES,
                    default="(skip — default from kind)")
    armature_role_type = None if rtype.startswith("(skip") else rtype

    _section("Mandate — what it's for")
    goal = _text("Goal (optional)")
    success_looks_like = _list("Success looks like")
    out_of_scope = _list("Out of scope")
    mandate_body = _multiline("Mandate body (optional)")

    brakes = None
    if _confirm("Add hard brakes/limits?"):
        _section("Brakes")
        cost = _text("cost_ceiling_usd (optional)")
        maxit = _text("max_iterations (optional)")
        forbidden = _list("Forbidden action")
        halt = _list("Halt-and-ask when")
        bbody = _multiline("Brakes body (optional)")
        brakes = {
            "cost_ceiling_usd": float(cost) if cost.strip() else None,
            "max_iterations": int(maxit) if maxit.strip() else None,
            "forbidden_actions": forbidden,
            "halt_and_ask_when": halt,
            "body": bbody,
        }

    trust = None
    if _confirm("Add response discipline (trust)?"):
        _section("Trust")
        sw = _select("show_work", ["required", "on_request", "(none)"])
        cs = _select("cite_sources", ["required", "(none)"])
        un = _select("uncertainty", ["must_flag", "(none)"])
        esc = _list("Escalate when")
        trust = {
            "show_work": None if sw == "(none)" else sw,
            "cite_sources": None if cs == "(none)" else cs,
            "uncertainty": None if un == "(none)" else un,
            "escalate_when": esc,
        }

    skills: list[dict] = []
    _section("Skills")
    while _confirm("Add a skill?", default=False):
        sid = _req_text("Skill id (e.g. appsec.rank-findings)")
        sname = _text("Short name (optional, default from id)")
        when = _req_text("when (the trigger)")
        tools = _list("Tool (e.g. github:dependabot.list_alerts)")
        context = _list("Context ref (e.g. context/severity-rubric.md)")
        ct = _select("cost_tier", ["(skip)"] + _COST_TIERS)
        version = _text("version", default="0.1.0")
        outputs = _text("outputs (optional, e.g. Finding[])")
        body = _multiline("Skill body (the procedure)")
        skills.append({
            "id": sid, "name": sname or None, "when": when, "tools": tools,
            "context": context, "cost_tier": None if ct == "(skip)" else ct,
            "version": version, "outputs": outputs or None, "body": body,
        })

    return {
        "id": aid, "name": name, "kind": kind, "summary": summary,
        "schema_version": schema_version,
        "role": role, "expertise": expertise, "temperament": temperament,
        "standards": standards, "refusals": refusals, "soul_body": soul_body,
        "armature_role_type": armature_role_type,
        "goal": goal, "success_looks_like": success_looks_like,
        "out_of_scope": out_of_scope, "mandate_body": mandate_body,
        "brakes": brakes, "trust": trust, "skills": skills,
    }
```

- [ ] **Step 5: Add `cmd_new` + the `new` subparser to `cli.py`**

In `src/armature_cabinet/cli.py`:

(a) Add to the top imports (after `from .select import select_skills`):
```python
from .scaffold import build_folder
```

(b) Add a `_confirm` helper (after the `_report` function) — keeps `questionary` lazy (only imported when a confirm is actually shown):
```python
def _confirm(msg: str, default: bool = False) -> bool:
    from questionary import confirm
    return bool(confirm(msg, default=default).ask())
```

(c) Add the `cmd_new` function (after `cmd_validate`):
```python
def cmd_new(args: argparse.Namespace) -> int:
    from .prompts import collect_answers  # lazy: questionary only needed for `new`
    from .compiler import compile_safety_fragment

    answers = collect_answers(args.id)
    out_dir = Path(args.out)
    try:
        root = build_folder(answers, out_dir)
    except FileExistsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    pkg = load_package(root)
    r = validate_package(pkg)
    _report(r)
    if not r.ok:
        print(f"created '{answers['id']}' at {root} — fix the issues above, then re-run.",
              file=sys.stderr)
        return 1

    print(f"created '{answers['id']}' at {root}")
    if _confirm("Build the bundle now (writes dist/<id>/)?"):
        bundle = compile_agent(pkg)
        bundle_dir = Path("dist") / pkg.id
        _dump(bundle, bundle_dir / "agent.yaml")
        fragment = compile_safety_fragment(pkg)
        if len(fragment) > 1:
            _dump(fragment, bundle_dir / f"{pkg.id}.safety.yaml")
        print(f"  bundle  -> {bundle_dir / 'agent.yaml'}")
    print(f"next: armature-cabinet validate {root}  |  armature-cabinet build {root}")
    return 0
```

(d) Add the `new` subparser in `main` (after the `validate` subparser block, before `args = parser.parse_args(argv)`):
```python
    n = sub.add_parser("new", help="interactively create a cabinet agent folder")
    n.add_argument("id", nargs="?", help="agent id / folder name (prompted if omitted)")
    n.add_argument("--out", default=".", help="parent directory to write the agent folder into (default: cwd)")
    n.set_defaults(func=cmd_new)
```

- [ ] **Step 6: Run the new CLI test**

Run: `python3 -m pytest tests/test_wizard_cli.py -q`
Expected: `1 passed`.

- [ ] **Step 7: Run the full suite + lint**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: `55 passed` (54 + 1); ruff clean.

- [ ] **Step 8: Reinstall + smoke-test the CLI (manual interactive run is optional; the monkeypatch test covers wiring)**

Run:
```bash
python3 -m pip install -e ".[dev]" -q
python3 -c "import armature_cabinet, armature_cabinet.cli, armature_cabinet.scaffold; print('import ok (no questionary pulled)')"
python3 -c "import armature_cabinet.scaffold; print('scaffold ok')"
armature-cabinet new --help 2>&1 | head -8
```
Expected: `import ok...`; `scaffold ok`; `new --help` shows the `new` subcommand usage (id optional, `--out`). (Do NOT run `armature-cabinet new` interactively in CI — it needs a TTY; the monkeypatch test is the automated gate. If you have a TTY, a manual `armature-cabinet new test-agent --out /tmp/wiz-smoke` smoke run is encouraged but optional.)

- [ ] **Step 9: Confirm compiler modules untouched + build job still works**

Run:
```bash
git diff --stat <M6-base>..HEAD -- src/armature_cabinet/loader.py src/armature_cabinet/compiler.py src/armature_cabinet/validate.py src/armature_cabinet/select.py src/armature_cabinet/errors.py src/armature_cabinet/model.py
python3 -m pip install build -q && rm -rf dist build && python3 -m build
python3 -m venv /tmp/wt-m6 && /tmp/wt-m6/bin/pip install --no-deps dist/*.whl && /tmp/wt-m6/bin/pip install pyyaml
/tmp/wt-m6/bin/python -c "import armature_cabinet; print('wheel import ok', armature_cabinet.__version__)"
rm -rf /tmp/wt-m6 dist build
```
Expected: the `git diff --stat` is empty; the wheel builds; `wheel import ok 0.1.0` prints (proving the new deps didn't break the `--no-deps + pyyaml` wheel import, because `prompts` is lazy and `__init__` doesn't import it).

- [ ] **Step 10: Commit**

```bash
git add src/armature_cabinet/prompts.py src/armature_cabinet/cli.py pyproject.toml tests/test_wizard_cli.py
git commit -m "feat(cli): new — interactive authoring wizard (rich + questionary)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 11: Final repo check**

Run:
```bash
git log --oneline | head -5
git status -s
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: the 3 M6 commits on top of the M6 docs commit, clean tree, `55 passed`, ruff clean.