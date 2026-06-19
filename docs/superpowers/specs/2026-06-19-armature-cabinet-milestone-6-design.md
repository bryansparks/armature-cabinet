# armature-cabinet — Milestone 6 Design: authoring wizard (`new`)

**Date:** 2026-06-19
**Status:** Draft — pending user review
**Scope decision (confirmed):** M6 = an interactive `armature-cabinet new` wizard that builds a complete, valid cabinet agent folder. Shape = **rich + questionary** interactive CLI. Deps declared in core `dependencies`.

## Goal

Let a human interactively define an agent "in all its glory" — identity, soul, mandate, brakes, trust, and a repeatable set of skills (with context refs) — and have the wizard write a complete cabinet folder that passes `validate` and is ready to `build`. This is the entry point of the new phase (M6 author → M7 library → M8 team/run). The compiler itself is unchanged; the wizard is a new authoring surface that writes source folders.

## Baseline (M1–M5 complete)

- Compiler: `load_package` → `validate_package` → `compile_agent`/`compile_safety_fragment`; CLI `build`/`validate` with `--skill`/`--when`. 47 tests, ruff-clean, e2e green, CI green.
- Validation rules + compile mapping are stable (documented in `docs/writing-a-cabinet-agent.md`). The wizard must produce folders that satisfy `validate_package` and compile cleanly.
- `rich` (>=13) and `questionary` (>=2) are already installed transitively (via `armature-agents` for rich); M6 declares them explicitly.

## Design

### Command + output

`armature-cabinet new [id] [--out DIR]`
- `id`: agent id / folder name. Optional positional; prompted (questionary text, required, non-empty) if omitted.
- `--out DIR`: parent directory to write into; default `.`. The folder is written to `<out>/<id>/`.
- Flow: `collect_answers(id)` → `build_folder(answers, out_dir)` → `validate_package(load_package(folder))` → on errors, print them and ask "fix or write anyway?"; on clean, offer to `build` the bundle (`armature-cabinet build <folder> -o <out>/<id>`). Print a summary + next steps (build / wire into a workflow / `armature run`).

### Architecture (separation: pure scaffold + interactive prompts)

- **`src/armature_cabinet/scaffold.py`** — `build_folder(answers: dict, out_dir: Path) -> Path`. **Pure** (answers dict → files; no prompting, no reading, only writing the folder). This is the unit-testable core. Also a helper `slugify(name) -> str` for skill filenames.
- **`src/armature_cabinet/prompts.py`** — `collect_answers(id: str | None) -> dict`. Interactive only; uses `questionary` (text/confirm/select/checkbox) + `rich` (styled section headers + per-field hints). Each prompt shows a one-line hint drawn from the guide's field reference (the wizard teaches the schema as you author — dual-audience).
- **`src/armature_cabinet/cli.py`** — adds a `new` subcommand wiring the above. `loader`/`compiler`/`validate`/`select`/`errors`/`model` are **unchanged**.
- **`__init__.py`** — export `build_folder` (+ `slugify`) for direct/test use.

### The answers dict (the contract between `prompts.py` and `scaffold.py`)

```python
{
  "id": str,                       # required, non-empty
  "name": str,                      # default = id
  "kind": "partner" | "clone",     # default "partner"
  "summary": str,                   # optional, ""
  "schema_version": str,            # default "0.1.0"
  "role": str,                      # required
  "expertise": list[str],           # []
  "temperament": str,              # optional, ""
  "standards": list[str],          # []
  "refusals": list[str],           # []
  "soul_body": str,                 # multiline, optional, ""
  "armature_role_type": str | None, # optional override (worker|orchestrator|judge|researcher)
  "goal": str,                      # optional, ""
  "success_looks_like": list[str],  # []
  "out_of_scope": list[str],        # []
  "mandate_body": str,             # optional, ""
  "brakes": {                       # None if the block is declined
     "cost_ceiling_usd": float | None,
     "max_iterations": int | None,
     "forbidden_actions": list[str],
     "halt_and_ask_when": list[str],
     "body": str,                   # optional
  } | None,
  "trust": {                        # None if the block is declined
     "show_work": "required" | "on_request" | None,
     "cite_sources": "required" | None,
     "uncertainty": "must_flag" | None,
     "escalate_when": list[str],
  } | None,
  "skills": [                       # repeatable; may be []
     {"id": str, "name": str | None, "when": str, "tools": list[str],
      "context": list[str], "cost_tier": str | None, "version": str,
      "outputs": str | None, "body": str},
  ],
}
```

### `build_folder` file-writing rules (scaffold.py — pure, deterministic)

Writes to `<out>/<id>/`:
- **`cabinet.yaml`** — `schema_version`, `id`, `name`, `kind`, `summary` (if non-empty), `blocks: {soul: soul.md, mandate: mandate.md}`, `blocks_extra: {brakes: brakes.md, trust: trust.yaml, skills: skills/, context: context/}` (only the blocks actually produced — e.g. omit `brakes`/`trust` from `blocks_extra` if those blocks were declined). *(These paths are declarative — the loader uses canonical filenames — but written to match the fixture convention.)*
- **`soul.md`** — frontmatter: `type: <kind>`, `role`, `expertise` (list, if any), `temperament` (if non-empty), `standards` (list, if any), `refusals` (list, if any), `armature_role_type` (if set); then `---` and `soul_body` (if non-empty).
- **`mandate.md`** — frontmatter: `goal`, `success_looks_like` (list, if any), `out_of_scope` (list, if any); then `---` and `mandate_body` (if non-empty). Only written if any mandate field is non-empty; if `goal`/`success`/`oos`/`body` are all empty, omit `mandate.md` and drop it from `blocks`.
- **`brakes.md`** — only if `answers["brakes"]` is not None. Frontmatter: `cost_ceiling_usd`, `max_iterations`, `forbidden_actions` (list), `halt_and_ask_when` (list); then `---` and `body` (if non-empty). Omit empty fields.
- **`trust.yaml`** — only if `answers["trust"]` is not None. YAML: `show_work`/`cite_sources`/`uncertainty` (only if set), `escalate_when` (list, if any). Omit empty fields.
- **`skills/<slug>.md`** — one per skill in `answers["skills"]`. `slug = slugify(skill["name"] or skill["id"].rsplit('.', 1)[-1] or skill["id"])`. Frontmatter: `id`, `version`, `name` (if set), `when` (if non-empty), `tools` (list, if any), `context` (list, if any), `cost_tier` (if set), `outputs` (if set); then `---` and `body`.
- **`context/<basename>.md`** — for each unique `context` ref across all skills, create a stub file at the referenced path (e.g. ref `context/severity-rubric.md` → file `context/severity-rubric.md`) with a header + a `<!-- TODO: fill in ... -->` placeholder. (The ref resolves → `validate` passes; the user fills it later.)
- **`README.md`** — one-line description: `# <name>\n\n<summary>` (or `# <id>` if summary empty).
- Creates `skills/` and `context/` dirs only if needed. Trailing newlines on every file. Writes via the existing `_dump` style (yaml.safe_dump for yaml; plain write for md).

### The prompts (`prompts.py` — interactive, questionary + rich)

A `rich` section header per block, then questionary prompts:
1. **Identity** — `id` (text, required, validate non-empty), `name` (text, default=id), `kind` (select partner/clone, default partner), `summary` (text, optional), `schema_version` (text, default "0.1.0").
2. **Soul** — `role` (text, required), `expertise` (checkbox/repeat-add list), `temperament` (text, optional), `standards` (list), `refusals` (list), `soul_body` (multiline text — enter lines, blank line ends; optional), `armature_role_type` (select worker/orchestrator/judge/researcher/"skip (default from kind)").
3. **Mandate** — `goal` (text, optional), `success_looks_like` (list), `out_of_scope` (list), `mandate_body` (multiline, optional).
4. **Brakes** — confirm "Add hard brakes/limits?"; if yes: `cost_ceiling_usd` (text→float, optional), `max_iterations` (text→int, optional), `forbidden_actions` (list), `halt_and_ask_when` (list), `body` (multiline, optional). If no, `brakes=None`.
5. **Trust** — confirm "Add response discipline (trust)?"; if yes: `show_work` (select required/on_request/none), `cite_sources` (select required/none), `uncertainty` (select must_flag/none), `escalate_when` (list). If no, `trust=None`.
6. **Skills** — "Add a skill?" loop. Per skill: `id` (text, required), `name` (text, default = id's last segment), `when` (text, required), `tools` (list), `context` refs (list, e.g. `context/severity-rubric.md`), `cost_tier` (select T1/T2/T3/skip), `version` (text, default "0.1.0"), `outputs` (text, optional), `body` (multiline procedure). Then "Add another skill?".

Each prompt displays a one-line hint (what the field is + what it compiles to), pulled from the guide's field reference. Empty/optional fields default to "" / [] / None; required fields re-prompt on empty.

### Dependencies

Add to `pyproject.toml` `dependencies`: `"rich>=13.0"`, `"questionary>=2.0"`. (Both already installed transitively; declaring makes the wizard robust and not reliant on armature-agents's dep set.) Runtime deps become `armature-agents>=0.3.5`, `pyyaml>=6.0`, `rich>=13.0`, `questionary>=2.0`.

### Testing

- **`tests/test_scaffold.py`** (the thorough, deterministic layer) — feed `build_folder` several answers dicts (a full one matching `incident-comms`; a minimal one with only id/kind/role; one with brakes+trust; one with 0 skills; one with skills referencing context) and assert: every expected file exists; `load_package(folder)` + `validate_package` → clean (ok); `compile_agent` produces the expected `role`/`skills`/`x_context`; `slugify` correctness; stub context files created for refs; omitted blocks produce no file.
- **`tests/test_wizard_cli.py`** (smoke) — monkeypatch `armature_cabinet.prompts.collect_answers` (the interactive collector) to return a scripted answers dict, invoke `main(["new", "<id>", "--out", <tmp>])`, and assert the CLI writes a valid folder (passes `validate` + compiles) and prints the expected summary. This tests the `cli.new` wiring deterministically without a real TTY. (Interactive E2E stays manual; `collect_answers` itself is exercised by hand.)
- Existing 47 tests + ruff + e2e stay green.

## Global Constraints (unchanged contract + M6 specifics)

- **M6 does not modify the compiler:** `loader.py`, `compiler.py`, `validate.py`, `select.py`, `errors.py`, `model.py` are untouched. Only `cli.py` (adds `new`), new `scaffold.py` + `prompts.py`, `__init__.py` (export), `pyproject.toml` (deps) change. `git diff <M6-base>..HEAD -- src/armature_cabinet/{loader,compiler,validate,select,errors,model}.py` must be empty.
- **Purity of `scaffold`:** `build_folder` is pure (answers dict → files; no prompting, no reading). `prompts.py` is the only interactive surface. The wizard does **not** add an LLM (interactive-only for v1; AI-generation is a later mode).
- Bundle validates as `CompiledAgent`; the wizard's output folder must pass `validate_package` and compile. The `x_`-metadata / soft-hard-guardrail / `cabinet.yaml`-source / one-directional rules still hold.
- Runtime deps gain `rich>=13.0` + `questionary>=2.0` (declared). `requires-python = ">=3.11"` unchanged. No network/LLM in the wizard.

## Success criteria

- `armature-cabinet new <id>` interactively produces a complete `<id>/` folder; the folder passes `armature-cabinet validate <id>` (exit 0) and `build` compiles it.
- A minimal run (id + kind + role only, no brakes/trust/skills) still yields a valid folder (0-skill bundle is valid, per M1).
- `test_scaffold.py` covers full/minimal/brakes+trust/0-skill/context-refs cases; `test_wizard_cli.py` smoke-tests the CLI.
- No compiler module changed; 47 existing + the new scaffold/smoke tests (≈55 total) all pass; ruff clean; e2e green.

## Non-goals (M6)

- AI-generation mode (LLM drafts prose from a domain) — later.
- The dropped richness metadata (maturity/owner/tags/tool_resolution/runtime_hints) — comes with NEXT-STEPS #1.
- Library management (`build --all`/`list`) — M7.
- Team workflow generation + `armature run` handoff — M8.
- Non-interactive `--set key=value` scripting mode; a full textual TUI.