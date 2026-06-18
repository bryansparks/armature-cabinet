# armature-cabinet Milestone 1 — Solidify the Baseline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the v0.1 compiler trustworthy — fail fast with clean messages, surface author mistakes, stop dropping authored content — while keeping it pure (folder in → dict out) and the e2e north-star green.

**Architecture:** Thin frontend. `loader` reads a cabinet folder into an `AgentPackage`. New `validate` checks logical rules into a `ValidationResult` (errors+warnings). `compiler` folds the package into `{role, skill_library}` plus an advisory `*.safety.yaml`. `cli` writes files, prints clean errors (catching a new `CabinetError`), and gains a `validate` subcommand. `errors` holds the single exception type.

**Tech Stack:** Python ≥3.11, pyyaml, armature-agents≥0.3.5, pytest, hatchling, argparse. No new runtime deps.

## Global Constraints

Copied verbatim from the approved spec; every task inherits these.
- Runtime deps limited to `armature-agents>=0.3.5` + `pyyaml>=6.0`; dev `pytest>=8.0`. No new runtime deps.
- `requires-python = ">=3.11"`.
- Bundle always validates as `CompiledAgent`; every `role.skills` id is a key in `skill_library`; every `SkillDef` has `content`.
- `role.type ∈ {worker, orchestrator, judge, researcher}`; cabinet `kind` maps to it (default `worker`) and rides as `x_kind`.
- No fields invented outside `extra="allow"` objects; extra metadata only on `Role` and `SkillDef`, prefixed `x_`.
- Soft/hard guardrail split preserved; `*.safety.yaml` stays advisory. No hard enforcement smuggled into the bundle.
- `cabinet.yaml` = source manifest; `agent.yaml` = compiled output. Naming unchanged.
- One-directional: this package compiles; core consumes. No core edits, no folder parsing in core, no network/registry fetching.
- Compiler stays pure: folder in → dict out, no side effects beyond the CLI writing files.

---

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `src/armature_cabinet/errors.py` | `CabinetError` exception (expected authoring mistakes) | NEW |
| `src/armature_cabinet/model.py` | `Skill`, `AgentPackage` dataclasses | unchanged |
| `src/armature_cabinet/loader.py` | read folder → `AgentPackage`; raise `CabinetError` on structural errors; key `context` by path relative to agent root | MODIFY |
| `src/armature_cabinet/validate.py` | `ValidationResult` + `validate_package(pkg, include)` — logical rules | NEW |
| `src/armature_cabinet/compiler.py` | `compose_description` (carry identity/mandate content), `_skill_entry` (carry `x_context` + `x_<extra>`), `compile_agent` (omit `x_schema_version` when null) | MODIFY |
| `src/armature_cabinet/cli.py` | `build` (validate + clean errors), new `validate` subcommand; catch `CabinetError` | MODIFY |
| `src/armature_cabinet/__init__.py` | export `validate_package`, `CabinetError` | MODIFY |
| `tests/test_validate.py` | validation rules + `validate` command | NEW |
| `tests/test_e2e.py` | north-star round-trip through real `armature` (slow/optional) | NEW |
| `tests/test_compile.py` | extend with field-carry tests | MODIFY |
| `pyproject.toml` | register `slow` pytest marker | MODIFY |
| `.gitignore` | ignore build artifacts + the original archives/orphan copies | NEW |

---

## Task 1: Repo housekeeping (git init + .gitignore + baseline commit)

**Files:**
- Create: `.gitignore`
- Modify: `pyproject.toml` (add pytest marker registration)
- Test: none (setup task)

**Interfaces:**
- Produces: a git repo with the verified v0.1 baseline committed, `slow` marker registered, original archives kept on disk but untracked.

- [ ] **Step 1: Initialize git**

Run:
```bash
git init
git config user.name >/dev/null 2>&1 || git config user.name "Bryan Sparks"
git config user.email >/dev/null 2>&1 || git config user.email "bryan@example.com"
```
Expected: `Initialized empty Git repository`

- [ ] **Step 2: Create `.gitignore`**

Create `.gitignore`:
```gitignore
# build artifacts
dist/
__pycache__/
*.egg-info/
.pytest_cache/

# original archives + orphan loose copies at repo root
# (the user's originals from the zip download; kept on disk, NOT tracked)
/armature-cabinet.zip
/files (5).zip
/compiler.py
/agent.yaml
```

- [ ] **Step 3: Register the `slow` pytest marker in `pyproject.toml`**

Append to `pyproject.toml`:
```toml

[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with -m 'not slow')",
]
```

- [ ] **Step 4: Verify baseline still green**

Run: `python3 -m pytest -q`
Expected: `5 passed`

- [ ] **Step 5: Commit the baseline**

Run:
```bash
git add .gitignore pyproject.toml README.md src tests examples
git commit -m "chore: baseline v0.1 (solidify starting point)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```
Expected: commit created. Confirm the archives/orphan copies are **not** staged (gitignored).

---

## Task 2: `CabinetError` + loader raises it; context keyed by path

**Files:**
- Create: `src/armature_cabinet/errors.py`
- Modify: `src/armature_cabinet/loader.py`
- Modify: `src/armature_cabinet/__init__.py`
- Test: `tests/test_validate.py` (structural-error + context-key cases)

**Interfaces:**
- Produces: `CabinetError(Exception)`; `load_package` raises `CabinetError` (not `FileNotFoundError`/`NotADirectoryError`/`yaml.YAMLError`) on missing dir, missing `cabinet.yaml`, malformed YAML; `split_frontmatter(text, *, source="")`; `AgentPackage.context` keyed by path relative to the agent root (e.g. `context/severity-rubric.md`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validate.py`:
```python
from pathlib import Path

import pytest

from armature_cabinet.errors import CabinetError
from armature_cabinet.loader import load_package

FIX = Path(__file__).parent / "fixtures" / "security-triage"


def _write(folder, files):
    for name, text in files.items():
        p = folder / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def test_missing_folder_raises_cabinet_error():
    with pytest.raises(CabinetError):
        load_package("/tmp/does-not-exist-xyz-abc")


def test_missing_cabinet_yaml_raises_cabinet_error(tmp_path):
    (tmp_path / "soul.md").write_text("---\nrole: R\n---\nbody\n", encoding="utf-8")
    with pytest.raises(CabinetError):
        load_package(tmp_path)


def test_malformed_frontmatter_raises_cabinet_error(tmp_path):
    _write(tmp_path, {
        "cabinet.yaml": "id: a\nname: A\nkind: partner\n",
        "soul.md": "---\nrole: [unterminated\n---\nbody\n",
    })
    with pytest.raises(CabinetError):
        load_package(tmp_path)


def test_context_keyed_by_path_relative_to_root():
    pkg = load_package(FIX)
    assert "context/severity-rubric.md" in pkg.context
    assert "context/finding-schema.md" in pkg.context
    assert pkg.context["context/severity-rubric.md"].strip()  # non-empty body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'armature_cabinet.errors'` and context key is `severity-rubric.md` (filename), not the path.

- [ ] **Step 3: Create `errors.py`**

Create `src/armature_cabinet/errors.py`:
```python
"""Errors raised for expected authoring mistakes (not bugs in this package)."""
from __future__ import annotations


class CabinetError(Exception):
    """A cabinet agent folder is missing, unreadable, or malformed.

    Raised at load time so the CLI can print a clean message instead of a
    traceback. Distinct from logical validation problems, which are returned
    (not raised) by ``validate_package``.
    """
```

- [ ] **Step 4: Rewrite `loader.py`**

Replace the full contents of `src/armature_cabinet/loader.py` with:
```python
"""Read a cabinet agent folder from disk into an AgentPackage."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

import yaml

from .errors import CabinetError
from .model import AgentPackage, Skill

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)

# fields consumed explicitly off a skill's frontmatter; the rest fall into extra
_SKILL_KNOWN = {"id", "name", "when", "tools", "context", "cost_tier", "version"}


def split_frontmatter(text: str, *, source: str = "") -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body) for a markdown file with YAML frontmatter.

    Raises ``CabinetError`` (naming ``source``) if the frontmatter is not valid YAML.
    """
    m = _FM.match(text)
    if m:
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError as e:
            where = f" in {source}" if source else ""
            raise CabinetError(f"Malformed YAML frontmatter{where}: {e}") from e
        return meta, m.group(2).strip()
    return {}, text.strip()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_skill(path: Path) -> Skill:
    meta, body = split_frontmatter(_read(path), source=str(path))
    sid = meta.get("id") or meta.get("name") or path.stem
    extra = {k: v for k, v in meta.items() if k not in _SKILL_KNOWN}
    return Skill(
        id=sid,
        body=body,
        name=meta.get("name"),
        when=meta.get("when"),
        tools=list(meta.get("tools") or []),
        context=list(meta.get("context") or []),
        cost_tier=meta.get("cost_tier"),
        version=meta.get("version"),
        extra=extra,
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        return yaml.safe_load(_read(path)) or {}
    except yaml.YAMLError as e:
        raise CabinetError(f"Malformed YAML in {path}: {e}") from e


def load_package(folder: str | Path) -> AgentPackage:
    root = Path(folder)
    if not root.is_dir():
        raise CabinetError(f"Not a cabinet agent folder: {root}")

    manifest_path = root / "cabinet.yaml"
    if not manifest_path.exists():
        raise CabinetError(f"Missing cabinet.yaml manifest in {root}")
    manifest = _load_yaml(manifest_path)

    soul_meta, soul_body = ({}, "")
    if (root / "soul.md").exists():
        soul_meta, soul_body = split_frontmatter(_read(root / "soul.md"), source="soul.md")

    mandate_meta, mandate_body = ({}, "")
    if (root / "mandate.md").exists():
        mandate_meta, mandate_body = split_frontmatter(_read(root / "mandate.md"), source="mandate.md")

    brakes: dict[str, Any] = {}
    if (root / "brakes.md").exists():
        brakes, _ = split_frontmatter(_read(root / "brakes.md"), source="brakes.md")

    trust: dict[str, Any] = {}
    if (root / "trust.yaml").exists():
        trust = _load_yaml(root / "trust.yaml")

    skills: list[Skill] = []
    skills_dir = root / "skills"
    if skills_dir.is_dir():
        for sp in sorted(skills_dir.glob("*.md")):
            skills.append(_load_skill(sp))

    context: dict[str, str] = {}
    context_dir = root / "context"
    if context_dir.is_dir():
        for cp in sorted(context_dir.glob("*.md")):
            # key by path relative to the agent root so skill `context:` refs
            # (e.g. "context/severity-rubric.md") resolve directly.
            context[cp.relative_to(root).as_posix()] = _read(cp).strip()

    return AgentPackage(
        manifest=manifest,
        soul_meta=soul_meta,
        soul_body=soul_body,
        mandate_meta=mandate_meta,
        mandate_body=mandate_body,
        skills=skills,
        brakes=brakes,
        trust=trust,
        context=context,
    )
```

- [ ] **Step 5: Export `CabinetError` from the package**

In `src/armature_cabinet/__init__.py`, add the import so the top of the file reads:
```python
"""armature-cabinet — compile cabinet agent folders into Armature agent bundles."""
from .errors import CabinetError
from .loader import load_package
from .compiler import compile_agent, compile_safety_fragment, compose_description

__all__ = [
    "CabinetError",
    "load_package",
    "compile_agent",
    "compile_safety_fragment",
    "compose_description",
]
__version__ = "0.1.0"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_validate.py tests/test_compile.py -q`
Expected: PASS (new tests + existing 5).

- [ ] **Step 7: Commit**

```bash
git add src/armature_cabinet/errors.py src/armature_cabinet/loader.py src/armature_cabinet/__init__.py tests/test_validate.py
git commit -m "feat(loader): raise CabinetError on structural errors; key context by path" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: `validate.py` — logical validation rules

**Files:**
- Create: `src/armature_cabinet/validate.py`
- Modify: `src/armature_cabinet/__init__.py`
- Test: `tests/test_validate.py` (append rule tests)

**Interfaces:**
- Consumes: `AgentPackage` (from `model`), its `.manifest`, `.skills` (each `.id`, `.context`), `.context` (dict keyed by relative path), `include: list[str] | None`.
- Produces: `ValidationResult(errors: list[str], warnings: list[str])` with `.ok` property; `validate_package(pkg, include=None) -> ValidationResult`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validate.py`:
```python
from armature_cabinet.validate import validate_package


def _valid_files():
    return {
        "cabinet.yaml": "id: a\nname: A\nkind: partner\nschema_version: '0.1.0'\n",
        "soul.md": "---\nrole: R\n---\nbody\n",
        "skills/s.md": "---\nid: s\n---\nbody\n",
    }


def test_valid_package_has_no_errors(tmp_path):
    _write(tmp_path, _valid_files())
    r = validate_package(load_package(tmp_path))
    assert r.ok, r.errors


def test_missing_id_is_error(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "name: A\nkind: partner\nschema_version: '0.1.0'\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert any("missing required 'id'" in e for e in r.errors)


def test_missing_name_warns_but_ok(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "id: a\nkind: partner\nschema_version: '0.1.0'\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert r.ok
    assert any("'name'" in w for w in r.warnings)


def test_invalid_kind_is_error(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "id: a\nname: A\nkind: weird\nschema_version: '0.1.0'\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert any("invalid kind" in e for e in r.errors)


def test_missing_kind_warns(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "id: a\nname: A\nschema_version: '0.1.0'\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert r.ok
    assert any("'kind'" in w for w in r.warnings)


def test_missing_schema_version_warns(tmp_path):
    files = _valid_files()
    files["cabinet.yaml"] = "id: a\nname: A\nkind: partner\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert r.ok
    assert any("schema_version" in w for w in r.warnings)


def test_duplicate_skill_id_is_error(tmp_path):
    files = _valid_files()
    files["skills/y.md"] = "---\nid: s\n---\nbody\n"  # same id as s.md
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert any("duplicate" in e for e in r.errors)


def test_bogus_include_skill_is_error(tmp_path):
    _write(tmp_path, _valid_files())
    r = validate_package(load_package(tmp_path), include=["nope"])
    assert any("nope" in e for e in r.errors)


def test_dangling_context_ref_is_error(tmp_path):
    files = _valid_files()
    files["skills/s.md"] = "---\nid: s\ncontext:\n  - context/missing.md\n---\nbody\n"
    _write(tmp_path, files)
    r = validate_package(load_package(tmp_path))
    assert any("context/missing.md" in e for e in r.errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'armature_cabinet.validate'`.

- [ ] **Step 3: Create `validate.py`**

Create `src/armature_cabinet/validate.py`:
```python
"""Validate a loaded AgentPackage: logical rules returned as errors + warnings.

Structural problems (missing folder/cabinet.yaml, malformed YAML) are raised as
``CabinetError`` by the loader. The rules here are logical authoring mistakes
that produce a degraded bundle if ignored; they are *returned*, not raised, so
the CLI can print them all at once.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from .model import AgentPackage

_VALID_KINDS = {"partner", "clone"}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_package(pkg: AgentPackage, include: list[str] | None = None) -> ValidationResult:
    r = ValidationResult()
    man = pkg.manifest

    if not man.get("id"):
        r.errors.append("cabinet.yaml: missing required 'id'")
    if not man.get("name"):
        r.warnings.append("cabinet.yaml: missing 'name' (defaulting to id)")
    kind = man.get("kind")
    if kind is None:
        r.warnings.append("cabinet.yaml: missing 'kind' (defaulting to 'partner')")
    elif kind not in _VALID_KINDS:
        r.errors.append(
            f"cabinet.yaml: invalid kind {kind!r} (expected one of {sorted(_VALID_KINDS)})"
        )
    if not man.get("schema_version"):
        r.warnings.append("cabinet.yaml: missing 'schema_version'")

    seen: set[str] = set()
    for s in pkg.skills:
        if not s.id:
            r.errors.append("skill: missing 'id'")
        elif s.id in seen:
            r.errors.append(f"duplicate skill id {s.id!r}")
        else:
            seen.add(s.id)
        for ref in s.context:
            if ref not in pkg.context:
                r.errors.append(f"skill {s.id!r}: context ref {ref!r} not found")

    if include:
        have = {s.id for s in pkg.skills}
        for want in include:
            if want not in have:
                r.errors.append(f"--skill {want!r}: not present in package")

    return r
```

- [ ] **Step 4: Export `validate_package`**

In `src/armature_cabinet/__init__.py` add `from .validate import validate_package` after the loader import, and add `"validate_package"` to `__all__`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_validate.py -q`
Expected: PASS (all rule tests).

- [ ] **Step 6: Commit**

```bash
git add src/armature_cabinet/validate.py src/armature_cabinet/__init__.py tests/test_validate.py
git commit -m "feat(validate): validate_package returns errors+warnings for logical rules" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: `compose_description` carries identity + mandate content; omit null `x_schema_version`

**Files:**
- Modify: `src/armature_cabinet/compiler.py` (`compose_description`, `compile_agent`)
- Test: `tests/test_compile.py` (append)

**Interfaces:**
- Produces: `compose_description` now folds `soul.expertise`, `soul.temperament`, `mandate.success_looks_like` into `role.description`; `compile_agent` omits `x_schema_version` when `schema_version` is absent.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_compile.py`:
```python
def test_description_carries_identity_and_mandate_content():
    desc = compile_agent(load_package(FIX))["role"]["description"]
    assert "Expertise:" in desc
    assert "Temperament:" in desc
    assert "Success looks like:" in desc


def test_x_schema_version_omitted_when_absent(tmp_path):
    (tmp_path / "cabinet.yaml").write_text(
        "id: a\nname: A\nkind: partner\n", encoding="utf-8"
    )
    (tmp_path / "soul.md").write_text("---\nrole: R\n---\nbody\n", encoding="utf-8")
    b = compile_agent(load_package(tmp_path))
    assert "x_schema_version" not in b["role"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_compile.py::test_description_carries_identity_and_mandate_content tests/test_compile.py::test_x_schema_version_omitted_when_absent -q`
Expected: FAIL — `Expertise:` absent; `x_schema_version` present as `null`.

- [ ] **Step 3: Edit `compose_description` in `compiler.py`**

In `src/armature_cabinet/compiler.py`, edit `compose_description` so that after the `soul_body` block and before the `standards` block, it adds expertise/temperament, and the mandate block gains `success_looks_like`. Replace the function with:
```python
def compose_description(pkg: AgentPackage) -> str:
    """Fold soul + mandate + the behavioral parts of brakes/trust into one prose block."""
    parts: list[str] = []

    role_line = pkg.soul_meta.get("role")
    if role_line:
        parts.append(f"Your role: {role_line}.")
    if pkg.soul_body:
        parts.append(pkg.soul_body)

    expertise = pkg.soul_meta.get("expertise")
    if expertise:
        parts.append("Expertise:\n" + _bullets(expertise))

    temperament = pkg.soul_meta.get("temperament")
    if temperament:
        parts.append(f"Temperament: {temperament}")

    standards = pkg.soul_meta.get("standards")
    if standards:
        parts.append("Standards you hold to:\n" + _bullets(standards))

    # refusals (soul) + read-only / forbidden + halt-and-ask (brakes) => "you will not / you stop"
    refusals = list(pkg.soul_meta.get("refusals") or [])
    forbidden = list(pkg.brakes.get("forbidden_actions") or [])
    if forbidden:
        refusals.append("never take these actions: " + ", ".join(forbidden))
    if refusals:
        parts.append("You will not:\n" + _bullets(refusals))

    halt = pkg.brakes.get("halt_and_ask_when")
    if halt:
        parts.append("Stop and hand back to a human when:\n" + _bullets(halt))

    goal = pkg.mandate_meta.get("goal")
    oos = pkg.mandate_meta.get("out_of_scope")
    success = pkg.mandate_meta.get("success_looks_like")
    if goal or oos or success:
        mandate = []
        if goal:
            mandate.append(f"Your mandate: {goal}")
        if success:
            mandate.append("Success looks like:\n" + _bullets(success))
        if oos:
            mandate.append("Out of scope: " + ", ".join(oos))
        parts.append("\n".join(mandate))

    # trust => behavioral output requirements
    trust_reqs = []
    if pkg.trust.get("show_work") in ("required", "on_request"):
        trust_reqs.append("show your reasoning, not just conclusions")
    if pkg.trust.get("cite_sources") == "required":
        trust_reqs.append("cite the evidence behind every claim")
    if pkg.trust.get("uncertainty") == "must_flag":
        trust_reqs.append("state your confidence and what would change it")
    if trust_reqs:
        parts.append("When you respond, always:\n" + _bullets(trust_reqs))

    return "\n\n".join(p for p in parts if p).strip()
```

- [ ] **Step 4: Edit `compile_agent` to omit null `x_schema_version`**

In `src/armature_cabinet/compiler.py`, replace the `role` dict construction in `compile_agent` with:
```python
    role: dict[str, Any] = {
        "name": pkg.name,
        "type": _role_type(pkg),
        "description": compose_description(pkg),
        "tools": tools,
        "skills": [s.id for s in skills],
        # metadata along for the ride (Role has extra="allow")
        "x_kind": pkg.kind,
        "x_source": pkg.id,
    }
    schema_version = pkg.manifest.get("schema_version")
    if schema_version is not None:
        role["x_schema_version"] = schema_version
```
(Leave the `skill_library` line unchanged for now — Task 5 changes `_skill_entry`.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_compile.py -q`
Expected: PASS (all 7 tests; the 5 originals still pass — `"Out of scope"`, `"cite the evidence"`, `"Stop and hand back to a human"` remain).

- [ ] **Step 6: Commit**

```bash
git add src/armature_cabinet/compiler.py tests/test_compile.py
git commit -m "feat(compiler): carry expertise/temperament/success_looks_like; omit null x_schema_version" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: `_skill_entry` carries `x_context` + `x_<extra>`

**Files:**
- Modify: `src/armature_cabinet/compiler.py` (`_skill_entry`, `compile_agent` call site)
- Test: `tests/test_compile.py` (append)

**Interfaces:**
- Consumes: `AgentPackage.context` (dict keyed by relative path) and `Skill.extra` (unknown frontmatter).
- Produces: each `skill_library` entry may carry `x_context: {<ref>: <body>}` and `x_<key>` for every key in `Skill.extra`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_compile.py`:
```python
def test_skill_context_resolved_to_x_context():
    b = compile_agent(load_package(FIX))
    entry = b["skill_library"]["appsec.rank-findings"]
    assert "x_context" in entry
    assert "context/severity-rubric.md" in entry["x_context"]
    assert entry["x_context"]["context/severity-rubric.md"].strip()  # body present


def test_skill_extra_passed_through_as_x():
    b = compile_agent(load_package(FIX))
    # rank-findings.md frontmatter has `outputs: Finding[]`
    assert b["skill_library"]["appsec.rank-findings"]["x_outputs"] == "Finding[]"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_compile.py::test_skill_context_resolved_to_x_context tests/test_compile.py::test_skill_extra_passed_through_as_x -q`
Expected: FAIL — `x_context` and `x_outputs` keys absent.

- [ ] **Step 3: Edit `_skill_entry` and its call site**

In `src/armature_cabinet/compiler.py`, replace `_skill_entry` with a version that takes `pkg`, and update `compile_agent`'s `skill_library` line. Replace the function:
```python
def _skill_entry(s: Skill, pkg: AgentPackage) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": s.id,
        "description": s.name or (s.when or s.id),
        "content": s.body,
    }
    # thick metadata preserved via Armature's extra="allow"; x_ prefix keeps it clear
    if s.when:
        entry["x_when"] = s.when
    if s.tools:
        entry["x_tools"] = s.tools
    if s.cost_tier:
        entry["x_cost_tier"] = s.cost_tier
    if s.version:
        entry["x_version"] = s.version
    # resolved context refs -> their bodies (SkillDef allows extra)
    resolved = {ref: pkg.context[ref] for ref in s.context if ref in pkg.context}
    if resolved:
        entry["x_context"] = resolved
    # pass through any other skill frontmatter via extra="allow"
    for key, val in s.extra.items():
        entry[f"x_{key}"] = val
    return entry
```
Then in `compile_agent`, change the `skill_library` line to:
```python
    skill_library = {s.id: _skill_entry(s, pkg) for s in skills}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_compile.py -q`
Expected: PASS (all 9 tests). Existing `test_thick_metadata_preserved` still passes (`x_cost_tier`, `x_tools` unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/armature_cabinet/compiler.py tests/test_compile.py
git commit -m "feat(compiler): emit x_context (resolved refs) and pass skill extra as x_<key>" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: CLI — `build` validates + clean errors; `validate` subcommand

**Files:**
- Modify: `src/armature_cabinet/cli.py`
- Test: `tests/test_validate.py` (append CLI tests)

**Interfaces:**
- Consumes: `validate_package`, `CabinetError`, `compile_agent`, `load_package`.
- Produces: `main(["build", ...])` returns 1 on validation errors or `CabinetError` (clean stderr, no traceback); `main(["validate", ...])` returns 0 clean / 1 on errors. New `validate` subcommand.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_validate.py`:
```python
from armature_cabinet.cli import main


def test_build_missing_folder_returns_1_no_traceback(capsys):
    rc = main(["build", "/tmp/does-not-exist-xyz-abc"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error:" in err
    assert "Traceback" not in err


def test_build_bogus_skill_returns_1(capsys):
    rc = main(["build", str(FIX), "-o", "/tmp/out-bogus", "--skill", "nope"])
    assert rc == 1
    assert "nope" in capsys.readouterr().err


def test_validate_clean_returns_0(capsys):
    rc = main(["validate", str(FIX)])
    assert rc == 0
    assert "ok" in capsys.readouterr().out.lower()


def test_validate_dup_id_returns_1(tmp_path, capsys):
    _write(tmp_path, {
        "cabinet.yaml": "id: a\nname: A\nkind: partner\nschema_version: '0.1.0'\n",
        "soul.md": "---\nrole: R\n---\nbody\n",
        "skills/x.md": "---\nid: dup\n---\nb\n",
        "skills/y.md": "---\nid: dup\n---\nb\n",
    })
    rc = main(["validate", str(tmp_path)])
    assert rc == 1
    assert "duplicate" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_validate.py -q -k "build or validate"`
Expected: FAIL — `build` raises `CabinetError` (uncaught → exit code is None/exception) and no `validate` subcommand exists.

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
    pkg = load_package(args.folder)
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
    pkg = load_package(args.folder)
    include = args.skill or None
    r = validate_package(pkg, include)
    # exercise the compiler in-memory to surface composition problems too
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
    b.add_argument("--no-safety", action="store_true", help="skip the advisory safety fragment")
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("validate",
                       help="load + validate + compile in memory; writes no files")
    v.add_argument("folder", help="path to the cabinet agent folder")
    v.add_argument("--skill", action="append",
                   help="check only this skill id (repeatable); default checks all")
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_validate.py -q`
Expected: PASS (all validate + CLI tests).

- [ ] **Step 5: Reinstall the console script and smoke-test**

Run:
```bash
python3 -m pip install -e ".[dev]" -q
armature-cabinet validate tests/fixtures/security-triage
armature-cabinet build tests/fixtures/security-triage -o /tmp/out-m1
armature-cabinet build /tmp/nope-xyz 2>&1 | head -1
```
Expected: `validate` prints `ok: security-triage (partner)`, exit 0; `build` succeeds; the missing-folder line prints `error: Not a cabinet agent folder: /tmp/nope-xyz`.

- [ ] **Step 6: Commit**

```bash
git add src/armature_cabinet/cli.py tests/test_validate.py
git commit -m "feat(cli): build validates + clean errors; add validate subcommand" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: North-star e2e round-trip test

**Files:**
- Create: `tests/test_e2e.py`
- Test: `tests/test_e2e.py`

**Interfaces:**
- Consumes: `armature.spec.loader.load_spec` (from the installed `armature-agents`); `examples/workflow.yml`.

- [ ] **Step 1: Write the test**

Create `tests/test_e2e.py`:
```python
"""North-star acceptance: a compiled bundle must round-trip through real armature.

Skipped entirely if ``armature-agents`` is not importable. Marked ``slow`` so CI
can deselect with ``-m 'not slow'`` (it imports litellm transitively).
"""
from pathlib import Path

import pytest

armature = pytest.importorskip("armature")
try:
    from armature.spec.loader import load_spec
except Exception:  # pragma: no cover - env-dependent
    pytest.skip("armature.spec.loader not available", allow_module_level=True)

pytestmark = pytest.mark.slow

WORKFLOW = Path(__file__).parent.parent / "examples" / "workflow.yml"


def test_bundle_roundtrips_through_armature():
    spec = load_spec(str(WORKFLOW))
    stage = next(s for s in spec.stages if s.id == "triage")
    assert stage.agent is None, "stage.agent should be cleared after resolution"
    assert stage.role.name == "Security Triage Partner"
    assert stage.role.type.value == "worker"
    assert len(stage.role.skills) == 3
    assert {"appsec.rank-findings"} <= set(spec.skill_library)
```

- [ ] **Step 2: Run the e2e test**

Run: `python3 -m pytest tests/test_e2e.py -q`
Expected: PASS (1 test). If it SKIPS, `armature-agents` isn't importable in the env — install it (`pip install armature-agents==0.3.5`) and rerun.

- [ ] **Step 3: Confirm fast run deselects it**

Run: `python3 -m pytest -q -m "not slow"`
Expected: all non-slow tests pass; e2e is deselected.

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e.py
git commit -m "test: north-star e2e round-trip through armature (slow)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Regenerate committed examples + final verification

**Files:**
- Modify: `examples/security-triage/agent.yaml` (regenerated artifact)
- Test: full suite

**Interfaces:** none new.

- [ ] **Step 1: Regenerate the committed example to match the new mapping**

Run:
```bash
armature-cabinet build tests/fixtures/security-triage -o examples/security-triage
```
Expected: rewrites `examples/security-triage/agent.yaml` (the safety fragment is unchanged). The new `agent.yaml` now contains `x_context`, `x_outputs`, and the `Expertise:`/`Temperament:`/`Success looks like:` prose.

- [ ] **Step 2: Spot-check the regenerated bundle carries the new fields**

Run:
```bash
grep -E "Expertise:|Temperament:|Success looks like:|x_context|x_outputs" examples/security-triage/agent.yaml
```
Expected: at least one line for each of `Expertise:`, `Temperament:`, `Success looks like:`, `x_context`, `x_outputs`.

- [ ] **Step 3: Run the entire suite including e2e**

Run: `python3 -m pytest -q`
Expected: all tests pass (unit + validate + compile + e2e).

- [ ] **Step 4: Re-confirm the e2e round-trip with the regenerated example**

Run:
```bash
python3 - <<'PY'
from armature.spec.loader import load_spec
spec = load_spec("examples/workflow.yml")
stage = next(s for s in spec.stages if s.id == "triage")
assert stage.agent is None and stage.role.name == "Security Triage Partner"
print("e2e ok against regenerated bundle")
PY
```
Expected: `e2e ok against regenerated bundle`.

- [ ] **Step 5: Commit the regenerated artifact**

```bash
git add examples/security-triage/agent.yaml
git commit -m "chore(examples): regenerate security-triage bundle for new mapping" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 6: Final repo status check**

Run:
```bash
git log --oneline
git status
```
Expected: a clean working tree (archives/orphan copies untracked, as designed) and the 8 task commits on top of the baseline.