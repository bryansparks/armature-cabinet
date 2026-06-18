# armature-cabinet — Milestone 3 Design: `when`-based skill selection (woodshop)

**Date:** 2026-06-18
**Status:** Draft — pending user review
**Scope decisions (confirmed):**
- **Selection granularity:** any-overlap, ranked — select every skill whose `when` shares ≥1 content keyword with the task, ranked by overlap count (ties → source order).
- **No-match behavior:** warn + build with 0 skills, exit 0.
- **Matching mechanism:** pure keyword overlap — no LLM, no network (the compiler-purity constraint decides this).

## Goal

Add a compile-time selection mode that picks the skills an agent should actually carry for a given task, by matching the task string against each skill's `when`. This is the "woodshop" model: pull down only the tool the cut needs. It reuses the existing `compile_agent(include=...)` path — the new work is a pure selector + CLI wiring. The compiler stays pure (folder in → dict out, no I/O, no network, no LLM).

## Baseline (M1+M2 complete)

- `compile_agent(pkg, include: list[str] | None)` already supports attaching a subset of skills by id; `--skill` (repeatable) feeds it. `validate_package(pkg, include)` errors on bogus `--skill` ids.
- Skills carry `when` (free-text prose), preserved on the compiled `SkillDef` as `x_when`.
- 35 tests passing; two fixtures (`security-triage`, `incident-comms`); e2e round-trips through real `armature 0.3.5`.

## The selector — new `src/armature_cabinet/select.py`

```python
def select_skills(pkg: AgentPackage, task: str) -> list[str]: ...
```

Pure, deterministic. Returns a list of **skill ids** (not Skill objects), in ranked order.

Algorithm:
1. **Tokenize** the task and each skill's `when`: lowercase, split on non-alphanumeric (`[a-z0-9]+`), drop tokens in a small **stopword set** (function words: articles, conjunctions, prepositions, pronouns, auxiliary verbs — e.g. `a/an/the/for/to/of/and/or/that/this/is/are/be/with/needs/need/in/on/at/by/it/…`) and drop single-character tokens. No stemming.
2. **Score** each skill: `score = |tokens(task) ∩ tokens(skill.when)|`. A skill with no `when` scores 0 and is never selected.
3. **Select** skills with `score >= 1`, **ranked by score desc; ties broken by source order** (the order skills appear in `pkg.skills`, which the loader sorts by filename).

Worked example (security-triage fixture), task `"prioritize open Dependabot alerts"`:
- `appsec.triage-dependabot-alerts` — `when` "A repository has open Dependabot alerts that need prioritizing." → shared `{open, dependabot, alerts}` → score 3.
- `appsec.triage-secret-scanning` — `when` "A repository has secret-scanning alerts to assess." → shared `{alerts}` → score 1.
- `appsec.rank-findings` — `when` "A set of raw security signals needs to be gated, then ordered for a human." → shared `{}` → score 0, excluded.
- Result: `["appsec.triage-dependabot-alerts", "appsec.triage-secret-scanning"]`.

Known crudeness (accepted for the seed): a broad term like `alerts` over-selects; no stemming means `prioritize` ≠ `prioritizing`. Matching is on `when` only (not `name`/`description`).

## CLI surface (`src/armature_cabinet/cli.py`)

- `armature-cabinet build <folder> [--when "<task>"] [--skill ID...] [-o DIR] [--no-safety]`
- `armature-cabinet validate <folder> [--when "<task>"] [--skill ID...]`
- `--when` and `--skill` are **mutually exclusive**. If both are given → clean `error:` message to stderr, exit 1 (they are two selection modes; only one may drive selection).
- `--when` flow: `select_skills(pkg, task)` → the `include` list → `validate_package(pkg, include)` (passes trivially — ids are self-derived) → `compile_agent(pkg, include=...)`.
- **No-match** (`select_skills` returns `[]`) → print `warning: no skills matched task: "<task>"; building with 0 skills` to stderr; build proceeds with `include=[]` (the role's soul/mandate/brakes still compile; `role.skills=[]`, `skill_library={}` — a valid `CompiledAgent`); **exit 0**.
- `validate --when` → dry-run preview: print the ranked matched-skill list (e.g. `matched 2 skill(s): appsec.triage-dependabot-alerts, appsec.triage-secret-scanning`), then validate + compile in memory; exit 0/1 on validation errors. No-match in `validate` → the warning + exit 0 (a no-match is not a validation error).

`__init__.py` exports `select_skills`.

## What stays unchanged

`compiler.py` (`compile_agent` already takes `include`), `validate.py`, `loader.py`, `errors.py`, `model.py`. `validate_package` is unchanged — for `--when` the include list is self-derived from `pkg.skills`, so its bogus-`--skill` check passes. The new code is one module (`select.py`) + CLI wiring (`cli.py`) + an export.

## Global Constraints (unchanged, must still hold)

- Runtime deps `armature-agents>=0.3.5` + `pyyaml>=6.0`; no new deps. `requires-python = ">=3.11"`.
- Bundle validates as `CompiledAgent`; every `role.skills` id is a key in `skill_library`; every `SkillDef` has `content`. (A 0-skill `--when`-no-match bundle is still valid — both invariants hold vacuously.)
- `role.type ∈ {worker, orchestrator, judge, researcher}`; `kind` → `x_kind`.
- No fields outside `extra="allow"`; extra metadata only on `Role`/`SkillDef`, `x_`-prefixed.
- Soft/hard guardrail split preserved; `*.safety.yaml` advisory.
- `cabinet.yaml` (source) vs `agent.yaml` (output) naming unchanged.
- One-directional; no core edits, no folder parsing in core.
- **Purity:** `select_skills` is pure (no I/O, no network, no LLM, deterministic). The compiler stays pure; only the CLI writes files.

## Tests

- **`tests/test_select.py`** (new):
  - tokenization: lowercase, punctuation split, stopword + single-char dropping.
  - scoring + ranking on `security-triage`: task `"prioritize open Dependabot alerts"` → `["appsec.triage-dependabot-alerts", "appsec.triage-secret-scanning"]` (dependabot first by score 3, secret-scanning second by score 1, rank-findings excluded).
  - no-match: an unrelated task (e.g. `"quantum entanglement simulation"`) → `[]`.
  - `incident-comms` fixture: task `"draft a status update for executives"` → `["comms.draft-status-update"]` (shared `status`/`update`; `cadence-plan` excluded).
  - source-order tie-break: construct a case where two skills tie on score and assert the loader's filename order wins.
- **`tests/test_validate.py`** (extend):
  - `build --when "<task>" -o /tmp/x` produces a bundle whose `role.skills` is exactly the matched subset; `build --when` + `--skill` together → exit 1 with a clean error; `build --when <no-match>` → stderr warning + a 0-skill bundle + exit 0; `validate --when "<task>"` prints the ranked matched list.
- Existing 35 tests stay green; the north-star e2e (full bundle, no `--when`) is untouched.

## Success criteria

- All tests pass (35 → ~45): existing 35 + `test_select.py` (~6) + `test_validate.py` CLI `--when` cases (~4).
- `armature-cabinet build tests/fixtures/security-triage --when "prioritize open Dependabot alerts" -o /tmp/x` succeeds and the bundle carries only the matched skills.
- `armature-cabinet validate tests/fixtures/security-triage --when "..."` previews the ranked selection.
- `select_skills` is pure and deterministic (same inputs → same output, no I/O).

## Non-goals (M3)

- LLM/semantic matching, embeddings, stemming, fuzzy matching.
- Matching on `name`/`description`/`context` (seed matches `when` only).
- `when`-selection at the workflow/runtime layer (this is a compile-time CLI feature).
- Carrying `tool_resolution`/`tags`/`maturity` as `x_` metadata (still deferred richness).
- A tunable threshold / top-N flag (any-overlap is the seed; tunability can come later).