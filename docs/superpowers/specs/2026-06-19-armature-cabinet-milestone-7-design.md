# armature-cabinet — Milestone 7 Design: agent library management

**Date:** 2026-06-19
**Status:** Draft — pending user review
**Scope decision (confirmed):** M7 = `list <dir>` (enumerate agents) + `build <dir> --all` (bulk-compile). A "library" is a directory of agent subfolders. Compiler unchanged.

## Goal

Make a folder of adjacent agents first-class: enumerate them (`list`) and bulk-compile them (`build --all`) so a multi-agent library — authored by hand or by the M6 wizard — can be inspected and compiled in one command. This is M7 of the new phase (M6 author → **M7 library** → M8 team/run).

## Baseline (M1–M6 complete)

- Compiler: `load_package`/`validate_package`/`compile_agent`/`compile_safety_fragment` + CLI `build`/`validate`/`new` with `--skill`/`--when`. 57 tests, ruff clean, e2e green, CI green.
- `examples/` holds two agent folders side by side (`security-triage`, `incident-comms`); the M6 wizard writes agent folders into a parent dir via `--out`. So a "library" is already the de-facto structure — M7 names and operates on it.

## Design

### `library.py` (new, pure-ish: reads + writes via the existing compiler)

- `list_agents(library_dir) -> list[dict]` — enumerate subdirectories of `library_dir` that contain `cabinet.yaml`; for each, `load_package` + `validate_package`; return a list of `{id, name, kind, skills (count), valid (bool), errors (list[str])}` sorted by id. A subdirectory without `cabinet.yaml` is skipped (not an agent). Load/validate failures are captured per-agent (never raise out of `list_agents`) — they appear as `valid=False` + `errors`.
- `build_all(library_dir, out_dir, no_safety=False) -> (list[Path], list[str])` — for each agent subfolder: `load_package` → `validate_package` (if errors, record + skip compile) → `compile_agent` → write `<out_dir>/<id>/agent.yaml` (+ `<out_dir>/<id>/<id>.safety.yaml` if the safety fragment has hard content and not `no_safety`). Returns (compiled bundle paths, per-agent error messages). **Continues on per-agent failure** (compiles as many as possible); does not abort on the first.
- Reuses `load_package`/`validate_package`/`compile_agent`/`compile_safety_fragment` unchanged. No compiler logic is duplicated.

### CLI

- **`armature-cabinet list <dir>`** — calls `list_agents(<dir>)`; prints a rich table (`ID | NAME | KIND | SKILLS | VALID`); exits 0 if every agent is valid, 1 if any is invalid (the `VALID` column shows `ok` / the error count).
- **`armature-cabinet build <dir> --all [--out DIR] [--no-safety]`** — calls `build_all(<dir>, <out>, no_safety)` (`--out` default `dist`); prints one line per agent (`compiled '<id>' -> <out>/<id>/agent.yaml (N skills, M tools)` or `error: '<id>' …`); prints a summary (`compiled K of N`); exits 1 if any agent failed, 0 if all ok. The single-agent `build <folder>` (no `--all`) behavior is unchanged.
- `cli.py` gains `--all` on `build` + the `list` subcommand. `__init__.py` exports `list_agents`, `build_all`.

### Decisions (from the approved design)
- **`build --all` output:** `--out DIR` default `dist` → each agent compiles to `dist/<id>/` (source in the library dir, output separate — no mixing).
- **`list` format:** rich table (rich is a core dep since M6).
- **`build --all` errors:** continue + report + non-zero exit (not fail-fast).
- **Agent detection:** a subdir is an agent iff it contains `cabinet.yaml`; others skipped.

## Global Constraints (unchanged contract + M7 specifics)

- Runtime deps `armature-agents>=0.3.5`, `pyyaml>=6.0`, `rich>=13.0`, `questionary>=2.0`. ruff dev-only. `requires-python = ">=3.11"`.
- **M7 does not modify the compiler:** `loader.py`/`compiler.py`/`validate.py`/`select.py`/`scaffold.py`/`prompts.py`/`errors.py`/`model.py` untouched. Only `library.py` (new), `cli.py` (`--all` + `list`), `__init__.py` (export), `tests/test_library.py` (new) change. `git diff <M7-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,scaffold,prompts,errors,model}.py` must be empty.
- `list_agents`/`build_all` reuse the existing compile/validate; they do not duplicate or alter it. No LLM, no network. The compiler stays pure.
- A library agent that fails load/validate is reported, not fatal to the rest. The compiled bundles still validate as `CompiledAgent`.

## Testing

- **`tests/test_library.py`** — build a tmp library with two agents via `scaffold.build_folder` (+ one non-agent subdir without `cabinet.yaml`):
  - `list_agents` returns the two agents' rows (id/name/kind/skills/valid) sorted by id; the non-agent subdir is skipped.
  - `list_agents` on a library containing a broken agent (e.g. duplicate skill id via a hand-written folder) returns `valid=False` + errors (does not raise).
  - `build_all` compiles both valid agents → `dist/<id>/agent.yaml` exists + the bundle `validate`s/compiles; the non-agent subdir is skipped.
  - `build_all` on a library with one broken agent: reports the error, compiles the other, returns `(1 path, 1 error)`.
  - CLI: `main(["list", str(lib)])` exits 0 (all valid) / 1 (any invalid) and prints the table; `main(["build", str(lib), "--all", "-o", str(out)])` compiles all and exits 0/1 accordingly.
- Existing 57 tests + ruff + e2e stay green.

## Success criteria

- `armature-cabinet list examples` enumerates `security-triage` + `incident-comms` (id/name/kind/skills/valid), exit 0.
- `armature-cabinet build examples --all -o /tmp/lib-out` compiles both → `/tmp/lib-out/security-triage/agent.yaml` + `/tmp/lib-out/incident-comms/agent.yaml`, exit 0.
- `test_library.py` covers enumerate/skip/broken-continue/CLI exit codes. 57 → ~63 tests pass; ruff clean; e2e green.
- No compiler module changed.

## Non-goals (M7)

- Team workflow generation + `armature run` handoff (M8).
- A library-level `manifest.yaml` indexing agents — `list` reads folders directly (YAGNI).
- Watching/recompiling on change; inter-agent dependency ordering; per-agent `--when`/`--skill` selection across the library.