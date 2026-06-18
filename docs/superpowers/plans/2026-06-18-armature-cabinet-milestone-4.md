# armature-cabinet Milestone 4 — Packaging & CI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ruff lint + a GitHub Actions workflow (lint / test / build-wheel) and make the code lint-clean — on every push to `main` and every PR. M4 touches no compiler code.

**Architecture:** Add `ruff` to the `dev` extra + a `[tool.ruff]` config; hoist three mid-file imports in `tests/test_validate.py` to the top so `ruff check` passes; add `.github/workflows/ci.yml` with three independent jobs (lint, test, build). The implementer runs the exact CI commands locally to de-risk, then the first pushed run on GitHub is the real validation.

**Tech Stack:** ruff, GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`), `python -m build` (hatchling backend already configured). No new runtime deps.

## Global Constraints

Copied verbatim from the approved M4 spec; every task inherits these.
- Runtime deps `armature-agents>=0.3.5` + `pyyaml>=6.0`; **ruff is dev-only** (in `[dev]`), not a runtime dep. `requires-python = ">=3.11"`.
- Bundle validates as `CompiledAgent`; `role.type ∈ {worker, orchestrator, judge, researcher}`; `x_` metadata only on `Role`/`SkillDef`; soft/hard guardrail split; `cabinet.yaml`/`agent.yaml` naming; one-directional; no core edits, no network fetching.
- **M4 does not modify `src/armature_cabinet/`.** `git diff <M4-base>..HEAD -- src/armature_cabinet/` must be empty.
- The compiler stays pure; CI does not change runtime behavior. Existing 47 tests must keep passing.

---

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `pyproject.toml` | add `ruff>=0.5` to `[dev]`; add `[tool.ruff]` + `[tool.ruff.lint]` | MODIFY |
| `tests/test_validate.py` | hoist 3 mid-file imports to the top (lint-clean) | MODIFY |
| `.github/workflows/ci.yml` | lint / test / build jobs on push+PR | NEW |
| `src/armature_cabinet/**` | **unchanged** | untouched |

---

## Task 1: Commit M4 spec + plan docs

**Files:**
- Create: `docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-4-design.md` (already written)
- Create: `docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-4.md` (this file)
- Test: none (setup)

**Interfaces:**
- Produces: a git commit of the M4 spec + plan; the post-commit HEAD is the **M4 base** for the final review + the `src/`-untouched proof.

- [ ] **Step 1: Verify the docs exist**

Run:
```bash
ls docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-4-design.md docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-4.md
```
Expected: both files listed.

- [ ] **Step 2: Confirm baseline still green**

Run: `python3 -m pytest -q`
Expected: `47 passed`.

- [ ] **Step 3: Commit the docs**

Run:
```bash
git add docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-4-design.md docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-4.md
git commit -m "docs: milestone-4 design + implementation plan" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git rev-parse HEAD
```
Expected: commit created; **record the printed HEAD sha** — this is the M4 base.

---

## Task 2: Ruff config + dev dep + hoist `test_validate.py` imports (lint-clean)

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/test_validate.py`
- Test: `ruff check src tests` (the lint is the test) + `pytest` (no regression)

**Interfaces:**
- Produces: a `[tool.ruff]` config + `ruff` in `[dev]`; `tests/test_validate.py` with all imports at the top; `ruff check src tests` passes with no findings. Task 3's CI lint job runs `ruff check src tests` against this config.

- [ ] **Step 1: Add `ruff` to the `dev` extra in `pyproject.toml`**

In `pyproject.toml`, change:
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0"]
```
to:
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.5"]
```

- [ ] **Step 2: Add the ruff config to `pyproject.toml`**

Append to `pyproject.toml` (after the existing `[tool.pytest.ini_options]` block):
```toml

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "W"]
```

- [ ] **Step 3: Hoist the three mid-file imports in `tests/test_validate.py` to the top**

The file currently has its imports split: a top block (`from pathlib import Path`, `import pytest`, `from armature_cabinet.errors import CabinetError`, `from armature_cabinet.loader import load_package`) plus three mid-file imports (`from armature_cabinet.validate import validate_package`, `from armature_cabinet.cli import main`, `import yaml`) that were appended across M1/M3.

Replace the top-of-file import block (the first 6 lines) with this single consolidated block:
```python
from pathlib import Path

import pytest
import yaml

from armature_cabinet.cli import main
from armature_cabinet.errors import CabinetError
from armature_cabinet.loader import load_package
from armature_cabinet.validate import validate_package
```

Then **delete** the three now-duplicate mid-file import statements (each appears once, mid-file, surrounded by blank lines — remove the import line and the extra blank lines it introduced so top-level definitions keep two blank lines between them):
- `from armature_cabinet.validate import validate_package`
- `from armature_cabinet.cli import main`
- `import yaml`

Leave every test function body untouched — only imports move.

- [ ] **Step 4: Install ruff and run the lint**

Run:
```bash
python3 -m pip install -e ".[dev]" -q
ruff check src tests
```
Expected: `ruff check` prints `All checks passed!` (no findings). If ruff reports findings, fix them (do not widen the `select` set to silence them) and re-run until clean.

- [ ] **Step 5: Confirm the hoist didn't break tests**

Run: `python3 -m pytest -q`
Expected: `47 passed`.

- [ ] **Step 6: Confirm `src/` is untouched**

Run: `git diff --stat <M4-base>..HEAD -- src/armature_cabinet/`
Expected: empty (no output). The only changed files should be `pyproject.toml` and `tests/test_validate.py`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/test_validate.py
git commit -m "feat(lint): add ruff config + dev dep; hoist test_validate imports (lint-clean)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: GitHub Actions workflow (`ci.yml`) + local verification

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: run the three jobs' commands locally

**Interfaces:**
- Consumes: the `[tool.ruff]` config from Task 2; `pytest` (full suite, incl `slow` e2e); `python -m build` (hatchling backend).
- Produces: `.github/workflows/ci.yml` with three independent jobs (lint, test, build) on `push` to `main` + `pull_request`, verified locally.

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install ruff
      - run: ruff check src tests

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -e ".[dev]"
      - run: pytest

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install build
      - run: python -m build
      - name: Verify wheel + sdist and import the wheel
        run: |
          set -e
          ls -1 dist/*.whl dist/*.tar.gz
          python -m venv /tmp/wt
          /tmp/wt/bin/pip install --no-deps dist/*.whl
          /tmp/wt/bin/pip install pyyaml
          /tmp/wt/bin/python -c "import armature_cabinet; print('wheel import ok', armature_cabinet.__version__)"
```

- [ ] **Step 2: Verify the lint command locally**

Run: `ruff check src tests`
Expected: `All checks passed!`

- [ ] **Step 3: Verify the test command locally**

Run:
```bash
python3 -m pip install -e ".[dev]" -q
python3 -m pytest -q
```
Expected: `47 passed` (the e2e runs; `armature-agents` is installed via `.[dev]`).

- [ ] **Step 4: Verify the build command locally**

Run:
```bash
python3 -m pip install build -q
rm -rf dist build
python3 -m build
ls -1 dist/*.whl dist/*.tar.gz
python3 -m venv /tmp/wt-local
/tmp/wt-local/bin/pip install --no-deps dist/*.whl
/tmp/wt-local/bin/pip install pyyaml
/tmp/wt-local/bin/python -c "import armature_cabinet; print('wheel import ok', armature_cabinet.__version__)"
rm -rf /tmp/wt-local
```
Expected: a `dist/armature_cabinet-0.1.0-py3-none-any.whl` and a `dist/*.tar.gz` are produced, and `wheel import ok 0.1.0` prints.

- [ ] **Step 5: Clean build artifacts and confirm `src/` untouched**

Run:
```bash
rm -rf dist build
git status -s
git diff --stat <M4-base>..HEAD -- src/armature_cabinet/
```
Expected: only `.github/workflows/ci.yml` is new (untracked); `dist/`/`build/` are gitignored so they don't show; the `src/` diff is empty. (If `dist/` or `build/` show as untracked, confirm `.gitignore` has `dist/` — it does from M1.)

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint/test/build workflow (push + PR)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 7: Final repo check**

Run:
```bash
git log --oneline | head -5
git status -s
```
Expected: the 3 M4 commits on top of the M4 docs commit, and a clean working tree.