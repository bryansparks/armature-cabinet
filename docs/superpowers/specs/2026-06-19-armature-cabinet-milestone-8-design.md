# armature-cabinet — Milestone 8 Design: team workflow generation + `armature run` handoff

**Date:** 2026-06-19
**Status:** Draft — pending user review
**Scope decision (confirmed):** M8 = `armature-cabinet team` — assemble a library of agents into a team workflow (sequential pipeline) and hand off to `armature run` (`--dry-run` validates, `--run` executes). Compiler unchanged; cabinet shells out to the `armature` CLI (does not import its runner).

## Goal

Close the phase-2 loop — **author (M6) → adjacent-agents library (M7) → run a team via armature (M8)**. M8 generates an Armature workflow spec (`workflow.yml`) wiring selected library agents into a sequential-pipeline team, then launches (or prints) the `armature run` command. The generated workflow + a dry-run through real Armature is the north-star: a team of cabinet-authored agents, validated by Armature's runner.

## Baseline (M1–M7 complete)

- `armature-cabinet` has `build`/`build --all`/`validate`/`list`/`new`; `library.py` (`list_agents`/`build_all`). 65 tests, ruff clean, e2e + CI green.
- Armature 0.3.5 ships the `armature` CLI with `run [--dry-run] <spec>` + `validate`. `armature run --dry-run examples/workflow.yml` already validates a 2-stage team of cabinet bundles (proven in the M8 brainstorm). The `examples/workflow.yml` is the shape template: `name`/`version`/`model_tiers`/`role_type_defaults`/`agent_library` (each agent → bundle path) / `stages` (id/agent/output_mode/depends_on).

## Design

### `team.py` (new)

- `generate_workflow(agent_ids: list[str], bundles_dir: Path, name: str) -> dict` — **pure**: returns the Armature workflow spec dict. `agent_ids` is the ordered selection. `bundles_dir` resolved absolute. Structure:
  ```yaml
  name: <name>
  version: "1.0"
  model_tiers:
    small: { provider: anthropic, model: claude-haiku-4-5-20251001 }
  role_type_defaults:
    worker: small
  agent_library:
    <id>: { path: <absolute bundles_dir>/<id>/agent.yaml }   # absolute, so armature resolves regardless of wf location
    ...
  stages:
    - id: <id0>; agent: <id0>; output_mode: text; depends_on: []
    - id: <id1>; agent: <id1>; output_mode: text; depends_on: [<id0>]
    ...   # sequential pipeline: stage[i].depends_on = [stage[i-1].id]
  ```
  No I/O, no LLM, deterministic.
- `run_workflow(wf_path: Path, dry_run: bool) -> int` — subprocess to the `armature` CLI: `armature run [--dry-run] <wf_path>`. Returns the runner's exit code. If `shutil.which("armature")` is None, raises `CabinetError("armature CLI not found; install armature-agents to run a team")` (so `main` surfaces a clean error). Does not import armature's runner — only shells out (preserves the one-directional boundary).

### CLI — `armature-cabinet team <library> [--agent id]... [--bundles DIR] [--out WF] [--name NAME] [--dry-run | --run]`

Flow:
1. `list_agents(library)` → rows.
2. **Selection:** if `--agent id` given (repeatable), filter to those ids in the given order; error (exit 1, clean message) if a requested id isn't in the library. Default: all agents, alphabetical by id. → `ordered_ids`.
3. **Bundle check:** for each id, require `<bundles>/<id>/agent.yaml` (default `--bundles dist`). If any missing, print a clean error listing the missing + suggest `armature-cabinet build --all <library> --bundles <bundles>`; exit 1 (do not generate). The defaults align: `build --all <lib>` writes `dist`; `team <lib>` reads `dist`.
4. `name` = `--name` or `<library-dir-name>-team`.
5. `generate_workflow(ordered_ids, bundles, name)` → dump to `--out` (default `team.yml`).
6. Print `wrote <wf>` + the two commands: `armature run --dry-run <wf>` (validate) and `armature run <wf>` (execute).
7. **Hand off:** `--dry-run` and `--run` are mutually exclusive (both → error). `--dry-run` → `run_workflow(wf, dry_run=True)`, print the armature output, exit its code. `--run` → `run_workflow(wf, dry_run=False)`, exit its code (needs a provider/API key — Armature's runtime concern). Default (neither) → just print the commands (decoupled; no subprocess).

`cli.py` gains the `team` subcommand; `__init__.py` exports `generate_workflow`, `run_workflow`.

### Decisions (from the approved design)
- **Default DAG:** sequential pipeline (`stage[i].depends_on = [stage[i-1].id]`); first stage `depends_on: []`. Editable in the generated file.
- **Bundles required pre-built:** `team` references `<bundles>/<id>/agent.yaml`; errors if missing (no auto-build). Run `build --all` first.
- **Run handoff via subprocess** to the `armature` CLI (not importing armature's runner). `--run`/`--dry-run` opt-in; default prints commands. Absolute bundle paths in the workflow so armature resolves them regardless of the wf file location.
- **Model tier:** default `small: {provider: anthropic, model: claude-haiku-4-5-20251001}` (matches `examples/workflow.yml`); editable. Not flag-configurable in v1 (YAGNI).
- **`--dry-run`/`--run` mutually exclusive.**

## Global Constraints (unchanged contract + M8 specifics)

- Runtime deps `armature-agents>=0.3.5`, `pyyaml>=6.0`, `rich>=13.0`, `questionary>=2.0`. ruff dev-only. `requires-python = ">=3.11"`.
- **M8 does not modify the compiler:** `loader`/`compiler`/`validate`/`select`/`scaffold`/`prompts`/`library`/`errors`/`model` untouched. Only `team.py` (new), `cli.py` (`team` subcommand), `__init__.py` (export), `tests/test_team.py` (new) change. `git diff <M8-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,scaffold,prompts,library,errors,model}.py` must be empty.
- `generate_workflow` is pure (no I/O/LLM); `run_workflow` only shells out to `armature` (no import of armature's runner). No network/LLM in cabinet. The one-directional boundary holds (cabinet generates + launches; armature runs).
- The generated workflow must be a valid Armature spec (the integration test proves it via `armature run --dry-run`). No `x_`/guardrail/contract regressions (cabinet's compiler is untouched).

## Testing

- **`tests/test_team.py`**:
  - `generate_workflow(["a", "b"], <tmp>/dist, "lib-team")` → dict with name `"lib-team"`, `version "1.0"`, `model_tiers.small`, `role_type_defaults.worker`, `agent_library` = `{a: {path: <abs>/dist/a/agent.yaml}, b: {path: <abs>/dist/b/agent.yaml}}`, `stages` = `[{id:a, agent:a, depends_on:[]}, {id:b, agent:b, depends_on:[a]}]`.
  - single-agent → one stage `depends_on:[]`.
  - CLI `team <lib> --bundles <dist> --out <wf>` (after `build_all(<lib>, <dist>)`) → rc 0, `<wf>` exists + parses with the expected `agent_library`/`stages`.
  - CLI `team` with a missing bundle → rc 1, clean `error:` mentioning the missing id + `build --all`, no wf written.
  - CLI `team <lib> --agent x --agent y` → stages in the given order (`x` then `y`); `--agent` id not in library → rc 1.
  - `run_workflow` raises `CabinetError` when `armature` is not on PATH (monkeypatch `shutil.which` → None).
  - `--dry-run` + `--run` together → rc 1 (mutually exclusive).
- **Integration (the M8 north-star):** build the `tests/fixtures` agents to a tmp `dist` (`build_all`), then `main(["team", "<fixtures>", "--bundles", <tmp_dist>, "--out", <tmp>/team.yml, "--dry-run"])` → `armature run --dry-run <team.yml>` validates (rc 0, "valid (2 stages)"). Skips gracefully if `armature` not on PATH (`shutil.which` guard). This is the real assemble + armature-validates-a-team loop.
- Existing 65 tests + ruff + e2e stay green.

## Success criteria

- `armature-cabinet build tests/fixtures --all -o /tmp/m8` then `armature-cabinet team tests/fixtures --bundles /tmp/m8 --out /tmp/m8/team.yml --dry-run` → `armature run --dry-run /tmp/m8/team.yml` validates the 2-stage team (rc 0).
- `test_team.py` covers structure/selection/missing-bundle/missing-armature/mutual-exclusion + the integration dry-run. 65 → ~72 tests pass; ruff clean; e2e green.
- No compiler module changed.

## Non-goals (M8)

- A GUI/editor for the team DAG; auto-building bundles (`--build`); inter-agent dependency inference from skill/context overlap; a real (non-dry-run) CI run (needs API keys); importing armature's runner (we shell out); team-level metadata/manifest; a `--model`/`--provider` flag (the generated file is editable).