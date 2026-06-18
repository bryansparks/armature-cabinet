# armature-cabinet Milestone 5 — Authoring guide + README refresh — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a dual-audience authoring guide (`docs/writing-a-cabinet-agent.md`, for humans **and** AI ingestion) and refresh the README to reflect the M1–M4 compiler. Docs-only — no code changes.

**Architecture:** Two docs files. The guide gives plain-language explanations alongside structured, machine-readable reference (field schemas, the validation rules, the compile mapping, a complete copyable worked example). The README is updated in place (mapping table, selection/validate, badge, Develop). Technical content (mapping/rules/CLI) is specified verbatim below; the implementer authors the explanatory prose and builds the worked example from the real `incident-comms` fixture.

**Tech Stack:** Markdown only. No deps, no code.

## Global Constraints

Copied verbatim from the approved M5 spec; every task inherits these.
- Runtime deps `armature-agents>=0.3.5` + `pyyaml>=6.0`; ruff dev-only; `requires-python = ">=3.11"`.
- **M5 does not modify `src/armature_cabinet/`, `tests/`, `pyproject.toml`, or `.github/`.** Docs-only. `git diff <M5-base>..HEAD -- src/ tests pyproject.toml .github/` must be empty.
- **Accuracy:** the guide's "compiles to" mapping, validation rules, and CLI behavior must match the actual M1–M4 compiler. An AI following the guide must produce an agent that passes `armature-cabinet validate` and compiles to the stated bundle.
- Dual-audience: every reference section gives human prose **and** AI-ingestible structure (schema tables with type/required/allowed-values/compiles-to; the validation rules stated outright; a complete copyable example).
- Soft/hard guardrail split and `cabinet.yaml`(source)/`agent.yaml`(output) naming described correctly.

---

## File Structure

| File | Responsibility | Status |
|---|---|---|
| `docs/writing-a-cabinet-agent.md` | dual-audience authoring guide (8 sections) | NEW |
| `README.md` | refresh: mapping table, selection/validate, badge, Develop, link to guide | MODIFY |
| `src/`, `tests/`, `pyproject.toml`, `.github/` | **unchanged** | untouched |

---

## Task 1: Commit M5 spec + plan docs

**Files:**
- Create: `docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-5-design.md` (already written)
- Create: `docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-5.md` (this file)
- Test: none (setup)

**Interfaces:**
- Produces: a git commit of the M5 spec + plan; the post-commit HEAD is the **M5 base** for the no-`src/` proof.

- [ ] **Step 1: Verify the docs exist**

Run:
```bash
ls docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-5-design.md docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-5.md
```
Expected: both files listed.

- [ ] **Step 2: Confirm baseline still green + lint clean**

Run:
```bash
python3 -m pytest -q 2>&1 | tail -2
ruff check src tests 2>&1 | tail -1
```
Expected: `47 passed`; ruff clean.

- [ ] **Step 3: Commit the docs**

Run:
```bash
git add docs/superpowers/specs/2026-06-18-armature-cabinet-milestone-5-design.md docs/superpowers/plans/2026-06-18-armature-cabinet-milestone-5.md
git commit -m "docs: milestone-5 design + implementation plan" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
git rev-parse HEAD
```
Expected: commit created; **record the printed HEAD sha** — this is the M5 base.

---

## Task 2: Write `docs/writing-a-cabinet-agent.md` (dual-audience guide)

**Files:**
- Create: `docs/writing-a-cabinet-agent.md`
- Test: accuracy spot-checks against the real compiler (no code change)

**Interfaces:**
- Consumes: the real `tests/fixtures/incident-comms/` fixture (for the worked example), the actual `validate_package`/`compile_*` behavior, the `armature-cabinet` CLI.
- Produces: a complete, accurate, dual-audience authoring guide.

The guide is **dual-audience**: humans read the prose; AI tools (e.g. Claude) ingest the structured reference to generate a valid agent. The technical content below (compile mapping, validation rules, CLI reference) MUST appear verbatim; the implementer authors the surrounding plain-language explanations and builds the worked example by reading the real `tests/fixtures/incident-comms/` files.

- [ ] **Step 1: Author the guide with these 8 sections**

Create `docs/writing-a-cabinet-agent.md`. Structure (each reference section = human prose **+** structured table/spec):

1. **Overview** — what a cabinet agent is; source folder vs compiled bundle (`agent.yaml`); the `author → armature-cabinet build → armature run` flow. State the AI-authoring posture up front: "an AI given this guide + a domain can produce a valid folder."
2. **Folder anatomy** — the file tree and what each file is for (cabinet.yaml, soul.md, mandate.md, brakes.md, trust.yaml, skills/*.md, context/*.md).
3. **Field reference** — for each file, a human description **and** a schema table with columns `field | type | required? | allowed values | compiles to`. Use the **Compile mapping** table (below) for the "compiles to" values. Cover every field listed in the mapping.
4. **Validation rules** — state the rules verbatim from the **Validation rules** list (below). Note that `armature-cabinet validate <folder>` checks them before build, and that structural problems raise `CabinetError` (clean message, not a traceback).
5. **Authoring a new agent (walkthrough)** — step-by-step, using the `incident-comms` fixture as the worked example. **Read the real files** at `tests/fixtures/incident-comms/` (cabinet.yaml, soul.md, mandate.md, brakes.md, trust.yaml, skills/*.md, context/audience-rubric.md) and include their contents inline as the copyable example. Walk through: cabinet.yaml → soul → mandate → brakes → trust → skills → context.
6. **Compiling** — document the CLI (below): `build`, `validate`, `--skill`, `--when` (woodshop matching, ranked, no-match → warn + 0-skill bundle + exit 0), `--when`/`--skill` mutual exclusion. Example commands.
7. **Guardrails** — the soft/hard split; the advisory `<id>.safety.yaml` fragment; how to merge it into a workflow's `safety:`/`contracts:`.
8. **Wiring into a workflow** — `agent_library` + `stages`; reference the two-agent `examples/workflow.yml` (security-triage + incident-comms) as the demo.

**Compile mapping** (include verbatim in the Field reference; this is the current M1–M4 behavior):

| Cabinet source | Compiles to |
|---|---|
| `cabinet.yaml` `id` | `x_source` on role (also names the output dir) |
| `cabinet.yaml` `name` | `role.name` |
| `cabinet.yaml` `kind` (`partner`\|`clone`) | `role.type` (mapped; default `worker`) + `x_kind` |
| `cabinet.yaml` `schema_version` | `x_schema_version` (omitted when null) |
| `cabinet.yaml` `summary`/`maturity`/`owner`/`tags`/`tool_resolution`/`runtime_hints` | authored but currently dropped (future "richness") |
| `soul.md` `role` | `role.description` prose: "Your role: …" |
| `soul.md` `expertise` (list) | `role.description` prose: "Expertise:\n- …" |
| `soul.md` `temperament` (str) | `role.description` prose: "Temperament: …" |
| `soul.md` `standards` (list) | `role.description` prose: "Standards you hold to:\n- …" |
| `soul.md` `refusals` (list) | `role.description` prose: "You will not:\n- …" |
| `soul.md` body | `role.description` prose (the voice) |
| `soul.md` `armature_role_type` (optional) | overrides `role.type` |
| `mandate.md` `goal` | `role.description` prose: "Your mandate: …" |
| `mandate.md` `success_looks_like` (list) | `role.description` prose: "Success looks like:\n- …" |
| `mandate.md` `out_of_scope` (list) | `role.description` prose: "Out of scope: …" |
| `brakes.md` `forbidden_actions` (list) | `role.description` prose ("…never take these actions: …") **and** `block` rules in `<id>.safety.yaml` |
| `brakes.md` `halt_and_ask_when` (list) | `role.description` prose: "Stop and hand back to a human when:\n- …" |
| `brakes.md` `max_iterations` | `contracts.max_iterations` in `<id>.safety.yaml` |
| `brakes.md` `cost_ceiling_usd` | `contracts._cost_ceiling_usd` in `<id>.safety.yaml` (note: no USD field in core yet) |
| `trust.yaml` `show_work`/`cite_sources`/`uncertainty` | `role.description` prose: "When you respond, always:\n- …" |
| `trust.yaml` `escalate_when` (list) | `suggested_escalation_gates` in `<id>.safety.yaml` |
| skill body | `skill_library[id].content` |
| skill `name` / `when` | `skill_library[id].description` (name, else when, else id) |
| skill `when` | `x_when` |
| skill `tools` (list) | `x_tools` **and** unioned into `role.tools` |
| skill `cost_tier` | `x_cost_tier` |
| skill `version` | `x_version` |
| skill `context` (list of refs into `context/`) | `x_context` (mapping ref → resolved body) |
| skill `extra` (any other frontmatter, e.g. `outputs`) | `x_<key>` |
| `context/*.md` | referenced by skills → resolved into `x_context`; unreferenced context files are loaded but not emitted |

**Validation rules** (include verbatim):

Errors (exit 1):
- folder missing or not a directory
- `cabinet.yaml` missing
- malformed YAML in any block
- `id` missing, empty, or non-string
- `kind` present but not `partner` or `clone`
- duplicate skill `id`
- skill `id` empty
- a `--skill` id not present in the package
- a skill `context` ref that does not resolve to a `context/*.md` file

Warnings (exit 0):
- `name` missing (defaults to `id`)
- `kind` missing (defaults to `partner`)
- `schema_version` missing

**CLI reference** (include verbatim):

```
armature-cabinet build    <folder> [-o DIR] [--skill ID]... [--when "<task>"] [--no-safety]
armature-cabinet validate <folder> [--skill ID]... [--when "<task>"]
```
- `build` writes `<out>/agent.yaml` (the `CompiledAgent` bundle) and `<out>/<id>.safety.yaml` (advisory, when brakes/trust have hard content).
- `validate` loads + validates + compiles in memory; writes nothing; exit 0 clean / 1 on errors.
- `--skill <id>` (repeatable): attach only the named skills.
- `--when "<task>"`: woodshop selection — keyword-overlap match against each skill's `when`; selects skills sharing ≥1 content keyword, ranked by overlap count (ties → source order); no-match → warning + a 0-skill bundle + exit 0. `validate --when` previews the ranked selection.
- `--when` and `--skill` are mutually exclusive.

- [ ] **Step 2: Verify accuracy against the real compiler**

Run:
```bash
armature-cabinet validate tests/fixtures/incident-comms
armature-cabinet build tests/fixtures/incident-comms -o /tmp/guide-check
armature-cabinet validate tests/fixtures/incident-comms --when "prioritize open Dependabot alerts" 2>&1 | head -1
armature-cabinet validate tests/fixtures/security-triage --when "prioritize open Dependabot alerts"
```
Expected: incident-comms `validate` → `ok: incident-comms (partner)`; `build` succeeds; the `--when` previews show ranked matches. Confirm the guide's stated rules/CLI match what these commands actually do (fix the guide if any discrepancy — do not change the compiler).

- [ ] **Step 3: Confirm `src/`/tests/`pyproject`/`.github` untouched + lint/tests still green**

Run:
```bash
git diff --stat <M5-base>..HEAD -- src/ tests pyproject.toml .github/
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: the `git diff --stat` is empty (only `docs/writing-a-cabinet-agent.md` is new); `47 passed`; ruff clean.

- [ ] **Step 4: Commit**

```bash
git add docs/writing-a-cabinet-agent.md
git commit -m "docs: writing-a-cabinet-agent guide (dual-audience: human + AI)" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: README refresh

**Files:**
- Modify: `README.md`
- Test: accuracy (commands in the README work)

**Interfaces:**
- Consumes: the guide from Task 2 (link to it); the current compiler behavior.

- [ ] **Step 1: Update the "What compiles where" table**

In `README.md`, replace the existing `## What compiles where` table with the **Compile mapping** table from Task 2 (the full current mapping, incl. `expertise`/`temperament`/`success_looks_like` → description, `x_context`, `x_<extra>`, `x_schema_version` omitted when null). Keep it readable; you may trim the dropped-metadata row to a footnote if it clutters, but the carried-fields rows must be present.

- [ ] **Step 2: Rewrite the "Compile-time skill selection" section**

Replace the `## Compile-time skill selection` section (which currently calls `--when` "a future build mode") with a present-tense section documenting **both** `--skill` and `--when`, plus `validate`. Use the **CLI reference** from Task 2. Add example commands:
```bash
armature-cabinet validate ./my-agent
armature-cabinet build ./my-agent -o dist/my-agent
armature-cabinet build ./my-agent -o dist/my-agent --when "prioritize open Dependabot alerts"
```

- [ ] **Step 3: Add `validate`/`--when` to the Build section**

In the `## Build` section, after the existing `build` example, add a one-line note that `validate` checks a folder without writing, and `--when`/`--skill` select skills (link to the guide for the full reference).

- [ ] **Step 4: Add a CI badge + refresh the Develop section**

At the top of `README.md` (under the title), add a CI badge:
```markdown
[![CI](https://github.com/bryansparks/armature-cabinet/actions/workflows/ci.yml/badge.svg)](https://github.com/bryansparks/armature-cabinet/actions/workflows/ci.yml)
```
Replace the `## Develop` section with:
````markdown
## Develop

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

CI (lint / test / build) runs on every push and PR — see the [actions](https://github.com/bryansparks/armature-cabinet/actions).
For authoring an agent, see [writing a cabinet agent](docs/writing-a-cabinet-agent.md).
````

- [ ] **Step 5: Add a one-line generalization note**

Near the cabinet-folder or Build section, add a line noting two fixtures demonstrate the format generalizes: `security-triage` (GitHub/appsec) and `incident-comms` (Slack/incident-comms) — both under `tests/fixtures/` and `examples/`.

- [ ] **Step 6: Verify the README's commands work + accuracy**

Run:
```bash
armature-cabinet validate tests/fixtures/security-triage
armature-cabinet build tests/fixtures/security-triage -o /tmp/readme-check
```
Expected: both succeed. Confirm every command shown in the README runs as documented (fix the README if any discrepancy — do not change the compiler).

- [ ] **Step 7: Confirm no code/test/config changes**

Run:
```bash
git diff --stat <M5-base>..HEAD -- src/ tests pyproject.toml .github/
git status -s
python3 -m pytest -q 2>&1 | tail -1
ruff check src tests 2>&1 | tail -1
```
Expected: the `git diff --stat` is empty; `git status -s` shows only `README.md` modified; `47 passed`; ruff clean.

- [ ] **Step 8: Commit**

```bash
git add README.md
git commit -m "docs(readme): refresh mapping/selection/validate, CI badge, link guide" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 9: Final repo check**

Run:
```bash
git log --oneline | head -5
git status -s
```
Expected: the 3 M5 commits on top of the M5 docs commit, clean tree.