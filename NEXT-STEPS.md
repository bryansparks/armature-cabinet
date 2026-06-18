# NEXT-STEPS.md — armature-cabinet

**Written:** 2026-06-18
**Status:** The 5-milestone roadmap (M1–M5) is **complete and shipped**. This file is a parking
lot for deferred / forward-looking work, so a future session can pick up without re-deriving it.

## Where things stand

`armature-cabinet` is a small, **pure** compiler: it turns a folder of agent-authoring files
(`cabinet.yaml`, `soul.md`, `mandate.md`, `brakes.md`, `trust.yaml`, `skills/*.md`, `context/*.md`)
into an Armature `CompiledAgent` bundle (`agent.yaml` + an advisory `*.safety.yaml`).

- **M1 solidify** — `CabinetError`, `validate_package` (logical rules), `validate` cmd, clean CLI
  errors, field-carries (`soul.expertise`/`temperament`, `mandate.success_looks_like` →
  `role.description`; skill `context` refs → `x_context`; skill `extra` → `x_<key>`; null
  `x_schema_version` omitted), north-star e2e round-trip through real `armature`.
- **M2 generalize** — `incident-comms` (non-GitHub, Slack/pagerduty) compiles + round-trips with
  **zero `src/` changes** → the format is proven domain-general.
- **M3 woodshop** — `--when "<task>"` selection: a pure keyword-overlap matcher (`select.py`),
  ranked, mutually exclusive with `--skill`, no-match → warn + 0-skill bundle + exit 0.
- **M4 packaging & CI** — ruff lint (`E4/E7/E9/F/W`, dev-only) + GitHub Actions
  (`.github/workflows/ci.yml`: lint / test / build-wheel), green on push + PR.
- **M5 docs** — `docs/writing-a-cabinet-agent.md` (dual-audience: human prose + AI-ingestible
  schema tables + validation rules + a copyable worked example) + README refresh.

State: 47 tests passing, `ruff check` clean, e2e green through `armature 0.3.5`, CI green,
`origin/main` in sync (private: github.com/bryansparks/armature-cabinet). Design docs + plans
for each milestone live under `docs/superpowers/{specs,plans}/`.

## Deferred / next-step candidates

Roughly in priority order. None are started; each would be its own spec → plan → implement cycle.

1. **Richness metadata carry-through.** `cabinet.yaml`'s `summary`, `maturity`, `owner`, `tags`,
   `tool_resolution`, `runtime_hints` are authored but currently **dropped** by the compiler
   (deferred in M1). Carry them as `x_<key>` metadata on `Role` (both `Role` and `SkillDef` allow
   `extra="allow"`). Low risk; small. Would let workflows/observability see agent provenance.

2. **`blocks` / `blocks_extra` path resolution.** Today the loader resolves blocks by **canonical
   filename** (`soul.md`, `mandate.md`, `brakes.md`, `trust.yaml`, `skills/`, `context/`) and
   **ignores** `cabinet.yaml`'s `blocks:`/`blocks_extra:` paths (the guide now documents this
   accurately). Either (a) make the loader honor those paths, or (b) drop the fields and document
   canonical names as the contract. Decision needed before doing it. Touches `loader.py` +
   `validate.py` + the guide/README.

3. **`when`-matcher improvements (M3 was the seed).** The current matcher is pure keyword overlap,
   no stemming (`prioritize` ≠ `prioritizing`), broad terms over-select (`alerts`), no top-N /
   threshold knob. Options: stemming/normalization, TF-IDF-ish weighting, a `--when-top N` or
   `--when-min-score` flag, and/or matching on `name`/`description` too (seed matches `when` only).
   Keep it **pure** (no LLM in the compiler).

4. **AI-authoring tool.** The M5 guide is built for AI ingestion; an AI (e.g. Claude) given the
   guide + a domain can already produce a valid folder. A natural next step is a thin authoring
   helper — e.g. an `armature-cabinet init <id>` scaffold command, or a template generator that
   emits a starter folder a human/AI then fills in. Keep the compiler pure; this is a separate
   surface. (See the project memory: agents are expected to be **AI-authored**; docs/tooling
   should stay dual-audience.)

5. **Marketplace / shelf.** The kickoff explicitly deferred this: `from: shelf://appsec/rank-findings@^1.0`
   style fetching, `pull`, registry. Non-goal until then — `AgentRef.path` is local-only. Big
   change; needs its own milestone(s) and a registry story.

6. **Carry safety/contract in the bundle.** Today hard enforcement is an advisory `*.safety.yaml`
   the workflow author merges by hand, because a `CompiledAgent` carries only `role` + `skill_library`.
   A future Armature **core** change could let bundles carry their own safety/contract — out of
   scope for this repo (one-directional: this package compiles, core consumes), but worth tracking.

7. **CI polish.** (a) Bump `actions/checkout`/`actions/setup-python` to versions targeting
   Node.js 24 to clear the current `Node.js 20 is deprecated` warning annotation. (b) Optionally
   add a multi-Python matrix (only 3.11 floor is tested now). (c) Optionally pin `ruff`/`build`
   versions. (d) A README CI badge is already in place. Small, cosmetic.

8. **PyPI publish.** Not done. Would need publish workflow + versioning policy + a public name
   check. Only relevant if/when the package is shared beyond the private repo.

## Principles to preserve (do not regress these)

- **Compiler purity:** `loader`/`compiler`/`validate`/`select` are pure — folder in →
  `AgentPackage`/dict/`ValidationResult`/ids out, no I/O, no network, **no LLM**. Only the CLI
  writes files. Any "smart" matching/authoring happens outside the compiler or in a separate surface.
- **One-directional boundary:** this package compiles; Armature core consumes. Never edit core
  from here; never parse the folder format in core. Core only ever loads a standard `CompiledAgent`.
- **Soft/hard guardrail split:** behavioral intent → `role.description` prose (agent self-governs);
  hard enforcement → advisory `*.safety.yaml` fragment the workflow merges. Do not smuggle hard
  enforcement into the bundle (it won't validate or will be dropped).
- **`x_` metadata only** on `Role`/`SkillDef` (both `extra="allow"`); no invented fields elsewhere.
- **`cabinet.yaml` = source; `agent.yaml` = output.** Don't confuse/rename.
- **Dual-audience docs:** agents will be authored primarily by AI tools; docs/tooling must stay
  human-readable **and** AI-ingestible (explicit schemas, validation rules stated outright, copyable
  examples). (Captured in the project memory `armature-cabinet-ai-authored`.)

## Known minor items (not blockers)

- **Node.js 20 deprecation** warning on the CI actions (see deferred #7a) — harmless; runs forced
  to Node 24.
- **Original archives at repo root** (`armature-cabinet.zip`, `files (5).zip`, orphan loose
  `compiler.py`/`agent.yaml`) are gitignored and kept on disk — Bryan's originals; archive or
  delete at your discretion.
- **SDD working artifacts** (`.git/sdd/` — task briefs, review packages, the progress ledger) are
  local-only, not tracked. The ledger's commit SHAs are pre-rewrite (a first-push authorship fix
  rewrote all SHAs from `bryan@local` → `bryan@drycanyon.com`); trust `git log` for current SHAs.

## How to resume tomorrow

- The workflow used this session: **brainstorm → spec (`docs/superpowers/specs/`) → plan
  (`docs/superpowers/plans/`) → subagent-driven execute (implementer + reviewer per task) →
  final whole-branch review → push + watch CI**. Reuse it for any item above.
- `pip install -e ".[dev]"` → `pytest` (47) + `ruff check src tests` to confirm a clean baseline
  before starting.
- `armature-cabinet validate`/`build`/`--when` to exercise the compiler; `tests/fixtures/`
  (`security-triage`, `incident-comms`) + `examples/workflow.yml` for the e2e.
- The north-star: a compiled bundle must round-trip through real `armature 0.3.5`
  (`tests/test_e2e.py`, marked `slow`).