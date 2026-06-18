# armature-cabinet — Milestone 1 Design: Solidify the Baseline

**Date:** 2026-06-18
**Status:** Draft — pending user review
**Scope decision (confirmed):** Solidify only. Generalization (a second non-GitHub fixture)
is Milestone 2. Field-carrying scope = **fix clear bugs + carry key content**; defer pure
metadata to a later "richness" milestone.

## Goal

Make the v0.1 compiler **trustworthy as a compiler**: refuse bad input with clear
messages instead of tracebacks, surface author mistakes instead of silently
emitting a degraded bundle, and stop dropping authored content the author clearly
intended to reach the agent. The compiler stays pure: folder in → dict out, no side
effects beyond the CLI writing files.

The north-star stays green throughout: the compiled bundle must round-trip through
the real installed `armature-agents==0.3.5`.

## Baseline (verified before designing)

- Repo was zipped, not laid out at root; scaffold extracted into working dir.
- `pytest` 5/5 pass; `build` on `tests/fixtures/security-triage` is byte-identical
  to committed `examples/`; e2e `load_spec("examples/workflow.yml")` resolves the
  `agent_library` ref, clears `stage.agent`, merges `skill_library`.
- Env: anaconda base, Python 3.11.5, `armature-agents` pinned 0.3.5.

### Gaps in v0.1 that this milestone closes

1. Bad input → raw Python traceback (no clean message, no exit code).
2. `--skill <bogus>` silently compiles a 0-skill, 0-tool bundle.
3. No duplicate-skill-id detection; minimal agent emits `description: ''` and
   `x_schema_version: null`.
4. Authored content silently dropped (see mapping table below).

## Design

### 1. Validation — fail fast, clean UX

Add `validate_package(pkg, include=None) -> ValidationResult` returning
`errors: list[str]` (fatal) and `warnings: list[str]`. One structured message per
problem, naming the file/field.

| Rule | Severity |
|---|---|
| folder missing or not a dir | error |
| `cabinet.yaml` missing | error |
| `id` missing/empty/non-str | error |
| `name` missing | warning (default to `id`) |
| `kind` present but not in `{partner, clone}` | error |
| `kind` absent | warning (default `partner`) |
| `schema_version` absent | warning |
| duplicate skill `id` | error |
| skill `id` empty | error |
| malformed YAML frontmatter (any block) | error (caught, not raised as traceback) |
| `--skill`/`include` id not present in package | error |
| skill `context` ref does not resolve to a `context/*.md` file | error |

`build` runs validation, prints errors/warnings to stderr, and exits 1 on any
error (no traceback). Warnings print but do not fail.

### 2. `armature-cabinet validate <folder>` command

Dry-run: load → validate → compile in memory, no file writes. Prints
errors/warnings. Exit 0 if clean, 1 if any error. Reuses the same
`validate_package`. No new flags for M1 (no `--strict`).

### 3. Tighten `compose_description`

- Graceful on missing blocks (already mostly true); never emit `x_schema_version:
  null` — omit the key when `schema_version` is absent.
- Fold additional identity/mandate content into the description (the "key content"
  carries — see table). Section order, fixed:
  role → body → expertise → standards → refusals(+forbidden) → halt-and-ask →
  mandate(goal, out_of_scope, success_looks_like) → trust requirements.

### 4. Field-carrying mapping (the "bugs + key content" scope)

| Source field | Compiles to | Notes |
|---|---|---|
| `soul.md` `expertise` | prose in `role.description` ("Expertise:\n- …") | **interpretation** — not enumerated in the option; see note below |
| `soul.md` `temperament` | prose in `role.description` ("Temperament: …") | **interpretation** — same note |
| `mandate.md` `success_looks_like` | prose in `role.description` ("Success looks like:\n- …") | |
| skill `context` refs | `x_context: {<ref>: <body>}` on the skill entry | loader re-keys `pkg.context` by path relative to agent root so refs resolve directly; dangling ref → error |
| skill `extra` (e.g. `outputs`) | `x_<key>` on the skill entry | passes through any unknown frontmatter via `extra="allow"` |
| `cabinet.yaml` `schema_version` | `x_schema_version` | omitted when null |

**Deferred to a later "richness" milestone** (NOT in M1): `cabinet.yaml`
`summary`, `maturity`, `owner`, `tags`, `tool_resolution`, `runtime_hints` as `x_`
metadata.

> **Note on expertise/temperament:** the chosen option text listed context,
> outputs/extra, success_looks_like, and the null fix — it did not enumerate
> `expertise`/`temperament`. I'm including them because they are identity *content*
> (not pure metadata) and are currently dropped, which is the same class of loss.
> Flagging explicitly so it can be vetoed at review; removing them shrinks M1.

### 5. CLI error UX — two error paths, one UX

- **Load-time structural errors** (folder missing/not-a-dir, `cabinet.yaml`
  missing, malformed YAML frontmatter) → `load_package` raises `CabinetError`
  instead of `FileNotFoundError`/`NotADirectoryError`/`yaml.YAMLError`.
- **Logical errors** (dup skill id, bogus `--skill`, invalid `kind`, dangling
  context ref, …) → `validate_package` returns them in `errors`.

`cli.py` wraps both: catches `CabinetError` and prints any returned `errors` as
`error: <msg>` to stderr, exit 1, no traceback. Warnings print but don't fail.
Unexpected errors still surface normally (don't swallow real bugs).

### 6. Housekeeping

- `git init`, `.gitignore` (`dist/`, `__pycache__/`, `*.egg-info/`, `.pytest_cache/`),
  initial baseline commit of the scaffold.
- The repo root still holds the **original archives** (`armature-cabinet.zip`,
  `files (5).zip`) and orphan loose copies (`compiler.py`, `agent.yaml`) that
  duplicate `src/` and `examples/`. I did not create these — they're the user's
  originals. **Action is the user's call:** move to `archive/`, delete, or keep.
  Surfaced, not auto-deleted.

## Tests (TDD)

New tests, one per behavior:
- duplicate skill id → error; bogus `--skill` → error (non-zero exit, no traceback);
  missing `cabinet.yaml` → clean error; not-a-dir → clean error; malformed
  frontmatter → clean error; missing `id` → error; invalid `kind` → error.
- `validate` command: exit 0 clean, exit 1 on errors; prints warnings.
- context ref resolves → `x_context` present with body; dangling ref → error.
- skill `extra` (`outputs`) → `x_outputs` present.
- `success_looks_like` / `expertise` / `temperament` present in `description`.
- `x_schema_version` omitted when `schema_version` absent.
- **North-star e2e** promoted to a real test (marked `slow`/optional, skipped if
  `armature-agents` not importable) asserting the section-6 round-trip.

## Contract invariants preserved (must not break)

- Bundle always validates as `CompiledAgent`; every `role.skills` id is a key in
  `skill_library`; every `SkillDef` has `content`.
- `role.type` ∈ {worker, orchestrator, judge, researcher}; cabinet `kind` maps to
  it (default `worker`) and rides as `x_kind`.
- No fields invented outside `extra="allow"` objects; extra metadata only on `Role`
  and `SkillDef`, prefixed `x_`.
- Soft/hard guardrail split preserved; `*.safety.yaml` stays advisory.
- `cabinet.yaml` (source) vs `agent.yaml` (output) naming unchanged.
- One-directional: this package compiles; core consumes. No core edits, no
  folder parsing in core, no network/registry fetching.

## Non-goals (M1)

- Second fixture / generalization (Milestone 2).
- `when`-based skill selection (Milestone 3+).
- CI / wheel / lint (Milestone 4).
- "Writing a cabinet agent" guide (Milestone 5).
- Carrying pure cabinet metadata (`summary`/`tags`/`maturity`/…) as `x_` (later
  "richness" milestone).
- `--strict`, marketplace/shelf fetching, anything networked.