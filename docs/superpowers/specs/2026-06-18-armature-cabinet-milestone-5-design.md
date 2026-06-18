# armature-cabinet — Milestone 5 Design: Authoring guide + README refresh

**Date:** 2026-06-18
**Status:** Draft — pending user review
**Scope decision (confirmed):** A single dedicated `docs/writing-a-cabinet-agent.md` + a README refresh.
**Key principle (confirmed):** Cabinet agents will be authored **primarily by AI tools** (like Claude), not just humans. The guide is **dual-audience**: human-readable prose *and* AI-ingestible structured reference (explicit schemas, type/required/allowed-value tables, the validation rules, complete copyable examples). M5 touches no code.

## Goal

Ship the user-facing documentation that closes the roadmap: a comprehensive authoring guide that lets a human *or* an AI author a valid cabinet agent from scratch, and a README refresh so the landing doc reflects the actual compiler (M1–M4: `validate`, `--when`, field-carries, CI, the second fixture) instead of the stale v0.1 mapping.

## Baseline (M1–M4 complete)

- Compiler: `load_package` → `validate_package` → `compile_agent`/`compile_safety_fragment`; CLI `build`/`validate` with `--skill` and `--when`. Field-carries: `soul.expertise`/`temperament`, `mandate.success_looks_like` → `role.description`; skill `context` refs → `x_context`; skill `extra` (e.g. `outputs`) → `x_<key>`; `x_schema_version` omitted when null. Validation rules: missing/non-str `id` (error), missing `name`/`kind`/`schema_version` (warnings), invalid `kind` (error), duplicate skill `id` (error), bogus `--skill` (error), dangling context ref (error). Soft/hard guardrail split. CI: lint/test/build, green.
- Two fixtures: `security-triage` (GitHub/appsec) and `incident-comms` (Slack/comms) — the latter proves the format generalizes and is the guide's worked example.
- README is the v0.1 version: its "What compiles where" table and "Compile-time skill selection" section predate M1–M4 (no `validate`, no `--when`, no field-carries, no CI, calls `--when` "a future build mode").

## Design

### 1. New: `docs/writing-a-cabinet-agent.md` — dual-audience authoring guide

Audience: a human authoring an agent **and** an AI tool (e.g. Claude) ingesting the guide to generate one. Every reference section gives **both** a plain-language explanation and a structured, machine-readable spec.

Sections:

1. **Overview** — what a cabinet agent is; source folder vs compiled bundle; the `author → compile → run` flow.
2. **Folder anatomy** — the file tree and what each file is for (cabinet.yaml, soul.md, mandate.md, brakes.md, trust.yaml, skills/*.md, context/*.md).
3. **Field reference (dual-format)** — for each file, a human description **and** a schema table: `field | type | required? | allowed values | compiles to`. Covers:
   - `cabinet.yaml`: `schema_version`, `id` (non-empty str, required), `name` (str, warns if missing), `kind` (`partner`|`clone`), `summary`, `blocks`/`blocks_extra`, `maturity`/`owner`/`tags`/`tool_resolution`/`runtime_hints` (authored but currently dropped — noted).
   - `soul.md` frontmatter: `role`, `expertise` (list), `temperament` (str), `standards` (list), `refusals` (list), optional `armature_role_type` (`worker`|`orchestrator`|`judge`|`researcher`); body = voice.
   - `mandate.md`: `goal`, `success_looks_like` (list), `out_of_scope` (list).
   - `brakes.md`: `cost_ceiling_usd`, `max_iterations`, `forbidden_actions` (list), `halt_and_ask_when` (list).
   - `trust.yaml`: `show_work` (`required`|`on_request`), `cite_sources` (`required`), `uncertainty` (`must_flag`), `escalate_when` (list).
   - `skills/*.md` frontmatter: `id` (required, unique), `version`, `name`, `when` (str), `tools` (list), `context` (list of refs into `context/`), `cost_tier`, plus any `extra` (e.g. `outputs`) → `x_<key>`; body = the procedure.
   - `context/*.md`: reference material; referenced by skills via `context:`; resolved to `x_context`.
   Each row's "compiles to" column reflects the **current** (M1–M3) mapping, not v0.1.
4. **Validation rules** — the explicit list an AI must satisfy to author a valid agent first try (the `validate_package` rules above + structural `CabinetError` cases: missing folder, missing `cabinet.yaml`, malformed YAML). State that `armature-cabinet validate <folder>` checks them before build.
5. **Authoring a new agent (walkthrough)** — step-by-step creating a new agent, using the `incident-comms` fixture as the worked example, with the actual file contents inline (copyable). Calls out the AI-authoring posture: "give an AI this guide + a domain, and it can produce a valid folder."
6. **Compiling** — `build` / `validate` / `--skill` / `--when`: what each does, the `--when` woodshop matching (keyword overlap, ranked, no-match → warn + 0-skill bundle + exit 0), `--when` vs `--skill` mutual exclusion. Example commands.
7. **Guardrails** — the soft/hard split; the advisory `*.safety.yaml` fragment; how to merge it into a workflow's `safety:`/`contracts:`.
8. **Wiring into a workflow** — `agent_library` + `stages`; the two-agent `examples/workflow.yml` (security-triage + incident-comms) as the demo.

### 2. README refresh

- **"What compiles where" table** — add the M1–M3 carries: `soul.expertise`/`temperament` → `role.description`; `mandate.success_looks_like` → `role.description`; skill `context` refs → `x_context`; skill `extra` (e.g. `outputs`) → `x_<key>`; `x_schema_version` omitted when null. Keep the existing rows that are still accurate.
- **"Compile-time skill selection" section** — rewrite to present tense: document **both `--skill` and `--when`** (the woodshop model shipped in M3), and add the `validate` command. Remove the "future build mode" language.
- **Build section** — add `validate` and `--when` examples alongside `build`.
- **Develop section** — add `ruff check`, link to CI, link to the authoring guide.
- **CI badge** at the top (CI exists now) + a one-line note that two fixtures demonstrate the format generalizes.
- Keep the intro + guardrails sections (still accurate).

### Files
- Create: `docs/writing-a-cabinet-agent.md`.
- Modify: `README.md`.
- Unchanged: all `src/`, `tests/`, `pyproject.toml`, `.github/`, `examples/`, fixtures. (Docs-only.)

## Global Constraints (unchanged, must still hold)

- Runtime deps `armature-agents>=0.3.5` + `pyyaml>=6.0`; ruff dev-only; `requires-python = ">=3.11"`.
- **M5 does not modify `src/armature_cabinet/`, tests, `pyproject.toml`, or `.github/`.** Docs-only. `git diff <M5-base>..HEAD -- src/ tests pyproject.toml .github/` must be empty.
- The guide must be **accurate** to the current compiler (M1–M4) — no stale v0.1 claims. The field reference's "compiles to" column and the validation rules must match the actual `validate_package`/`compile_*` behavior (an AI following it must produce an agent that passes `validate` and compiles to the stated bundle).
- The guardrail soft/hard split and `cabinet.yaml`/`agent.yaml` naming must be described correctly.

## Success criteria

- `docs/writing-a-cabinet-agent.md` exists, is dual-audience (prose + structured schema tables + validation rules + a complete copyable worked example), and is accurate to M1–M4.
- A reader (human or AI) following the guide can author a new cabinet agent that passes `armature-cabinet validate` and compiles to the bundle the guide describes. (Spot-check: the guide's stated rules match `validate_package`'s actual behavior.)
- README reflects the current compiler: updated mapping table, `validate` + `--when` documented present-tense, CI badge + Develop section with `ruff check`, link to the guide.
- No `src/`/tests/`pyproject.toml`/`.github/` changes across M5 commits. `ruff check` + `pytest` still pass (M5 changes no code, so this is a no-op confirmation).

## Non-goals (M5)

Autogenerated API reference, a docs website, publishing to PyPI, translating the guide, a CHANGELOG, API-stability/versioning policy, an AI-authoring *tool* (the guide is for AI ingestion; an authoring CLI/tool is a later phase).