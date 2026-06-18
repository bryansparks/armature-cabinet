# armature-cabinet — Milestone 4 Design: Packaging & CI

**Date:** 2026-06-18
**Status:** Draft — pending user review
**Scope decisions (confirmed):**
- **Linter:** ruff (modern, fast, one tool). Lint only (`ruff check`), not format enforcement.
- **CI test scope:** full suite incl the slow north-star e2e (one test job, `pip install -e ".[dev]"` + `pytest`).

## Goal

Add basic CI to the repo: a GitHub Actions workflow that lints, runs the full test suite (including the north-star e2e through real `armature`), and builds an installable wheel — on every push to `main` and every PR. Add ruff as the linter and make the code lint-clean (resolving the lint-shaped Minors the M1–M3 reviews deferred). M4 touches no compiler code.

## Baseline (M1–M3 complete)

- `pyproject.toml`: hatchling build, `armature-cabinet` v0.1.0, `requires-python = ">=3.11"`, deps `armature-agents>=0.3.5` + `pyyaml>=6.0`, `dev = ["pytest>=8.0"]`, `[tool.pytest.ini_options]` registers the `slow` marker.
- 47 tests passing (incl one `slow`-marked e2e that imports `armature` via `pytest.importorskip`). Repo is on GitHub (`origin`, private), `main` in sync.
- Deferred lint-shaped Minors: three mid-file imports in `tests/test_validate.py` (from the M1/M3 append pattern). (The unused `Any` import was already removed in M1; trailing newlines already swept in M1/M2.)

## Design

### 1. Ruff (linter)

Add `ruff>=0.5` to the `dev` extra:
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.5"]
```

Add a `[tool.ruff]` section to `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "W"]
```
`select` catches exactly what the reviews flagged: **E402** (module-level import not at top), **F401** (unused import), **W292** (no newline at end of file), plus E7/E9 (errors) and the rest of F (pyflakes). `I` (isort) is deliberately **not** enabled — avoids import-reorder churn.

### 2. Lint-clean: hoist `tests/test_validate.py` mid-file imports

Move the three mid-file imports to the top of the file (alongside the existing `pathlib`/`pytest`/`armature_cabinet.errors`/`armature_cabinet.loader` imports):
- `from armature_cabinet.validate import validate_package` (currently mid-file)
- `from armature_cabinet.cli import main` (currently mid-file)
- `import yaml` (currently mid-file)

After hoisting, `ruff check src tests` passes with no findings. This is the targeted improvement that adding a linter motivates — it resolves the deferred Minors so the lint job is green without per-file ignores. No other source changes.

### 3. GitHub Actions — `.github/workflows/ci.yml`

Triggers: `push` to `main` + `pull_request`. All jobs run on `ubuntu-latest`, Python 3.11, with pip caching (`actions/setup-python` `cache: pip`).

- **lint** — `pip install ruff` → `ruff check src tests`. Fast; does not install the package.
- **test** — `pip install -e ".[dev]"` (pulls `armature-agents` + transitively `litellm`; pip-cached) → `pytest`. Runs all 47 tests **including** the `slow` north-star e2e (the `slow` marker does not auto-skip; CI runs the full suite). `load_spec` reads a local YAML file and needs no API keys or network, so the e2e runs clean in CI.
- **build** — `pip install build` → `python -m build` → assert `dist/*.whl` and `dist/*.tar.gz` exist → install the built wheel into a fresh venv → `python -c "import armature_cabinet; print(armature_cabinet.__version__)"`.

The three jobs are independent (no `needs:`); each fails independently.

### 4. Verification

The implementer runs the exact CI commands **locally** before committing the workflow: `ruff check src tests`, `pip install -e ".[dev]" && pytest`, `python -m build` + wheel import. This de-risks the push. The real validation is the **first GitHub Actions run after push** — at the finish, push and watch the run via `gh`; if any job fails, fix and re-push.

## Files

- Modify: `pyproject.toml` (ruff dev dep + `[tool.ruff]`), `tests/test_validate.py` (hoist 3 imports).
- Create: `.github/workflows/ci.yml`.
- Unchanged: all `src/armature_cabinet/**`.

## Global Constraints (unchanged, must still hold)

- Runtime deps `armature-agents>=0.3.5` + `pyyaml>=6.0`; **ruff is a dev-only dep** (in `[dev]`), not a runtime dep. `requires-python = ">=3.11"`.
- Bundle validates as `CompiledAgent`; `role.type ∈ {worker, orchestrator, judge, researcher}`; `x_` metadata only on `Role`/`SkillDef`; soft/hard guardrail split; `cabinet.yaml`/`agent.yaml` naming; one-directional; no core edits, no network fetching.
- **M4 does not modify `src/armature_cabinet/`.** Compiler/loader/validate/select/cli/errors/model are untouched. `git diff <M4-base>..HEAD -- src/armature_cabinet/` must be empty.
- The compiler stays pure; CI does not change runtime behavior.

## Success criteria

- `ruff check src tests` passes locally with no findings (after the import hoist).
- `pip install -e ".[dev]" && pytest` → 47 passed locally.
- `python -m build` produces a wheel that imports (`import armature_cabinet` succeeds from the installed wheel).
- `.github/workflows/ci.yml` is valid YAML; pushed; the first GitHub Actions run is green (lint + test + build all pass on `ubuntu-latest`/py3.11).
- `git diff` over `src/armature_cabinet/` is empty across all M4 commits.

## Non-goals (M4)

- README CI badge, multi-Python matrix (only the 3.11 floor), publishing to PyPI, pre-commit hooks, coverage reporting, `ruff format` enforcement, dependabot, release automation.