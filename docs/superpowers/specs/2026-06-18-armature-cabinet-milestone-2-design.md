# armature-cabinet — Milestone 2 Design: Prove it generalizes

**Date:** 2026-06-18
**Status:** Draft — pending user review
**Scope decision (confirmed):** Author a second cabinet agent in a non-GitHub, non-security domain — an **Incident Comms Partner** — and prove it compiles and round-trips through real `armature` with **zero `src/` changes**. If authoring it forces a compiler change, that is the headline finding (the format *was* secretly security-shaped) — surfaced, not papered over.

## Goal

The v0.1+M1 compiler was built and hardened against a single security-triage fixture. M2 tests whether the cabinet format is genuinely domain-general by adding a structurally-parallel agent in a different domain (incident communications) with non-GitHub tools, and confirming the compiler, validation, and e2e machinery handle it unchanged. The north-star extends: two different-domain agents cooperate in one workflow and both resolve through the installed `armature-agents==0.3.5`.

## Baseline (M1 complete)

- 28 tests passing; `src/armature_cabinet/` carries `errors`, `loader`, `model`, `validate`, `compiler`, `cli`.
- Compiler folds soul/mandate content + `x_context`/`x_<extra>`; `validate_package` enforces logical rules; CLI `build`/`validate` print clean errors; e2e round-trips `examples/workflow.yml` → `security-triage` stage.
- Contract invariants from the M1 spec still hold (see Global Constraints below).

## The second agent: `incident-comms`

`partner` → `worker`; non-GitHub tools (slack/pagerduty/email/statuspage); recommends-only, read-only. Structurally parallel to `security-triage` so any divergence in compilation is attributable to domain, not shape.

### `cabinet.yaml`
```yaml
schema_version: "0.1.0"
id: incident-comms
name: Incident Comms Partner
kind: partner
summary: Drafts incident status updates and stakeholder comms for a human to send; never sends itself.
blocks:
  soul: soul.md
  mandate: mandate.md
maturity: L1
owner: bryan
tags: [incidents, comms, oncall, status]
blocks_extra:
  brakes: brakes.md
  trust: trust.yaml
  skills: skills/
  context: context/
tool_resolution: slack
runtime_hints:
  default_cost_tier: T2
```
(`tool_resolution`/`maturity`/`owner`/`tags`/`runtime_hints` are authored for fidelity but currently dropped by the compiler — deferred "richness" metadata, same as the security fixture.)

### `soul.md` (frontmatter + voice body)
- `type: partner`
- `role: Incident communications lead`
- `expertise`: [incident response comms, audience calibration, severity framing, cadence and pacing]
- `temperament: calm, clear, audience-aware`
- `standards`: never speculate past the known facts; severity in plain language (no jargon-only updates); one update per decision point, not per emotion; name the audience for every message
- `refusals`: recommends only; never sends/publishes/posts to any channel; won't soften severity to avoid discomfort; won't promise an ETA it can't justify with a signal
- **body (voice):** calm, clear, audience-aware. Assumes the on-call is sleep-deprived and stakeholders are anxious. Treats comms as subtraction — most updates don't need to go out; value is the one that does, written so a tired human can send it as-is. (Authored in the plan; ~4-6 sentences mirroring the security soul's tone.)

### `mandate.md`
- `goal`: Keep stakeholders informed with the minimum comms that land the right information at the right time, without the on-call becoming a scribe.
- `success_looks_like`: stakeholders know what is happening and what to do next; no update goes out that an on-call has to retract; comms cadence matches severity, not anxiety; every draft names its audience and the evidence behind it
- `out_of_scope`: actually sending/publishing/posting anything; deciding severity (the incident commander's call); engineering remediation; customer account or billing actions
- **body:** one short paragraph on why this partner exists (comms noise costs the same tired human as missed updates).

### `brakes.md`
- `cost_ceiling_usd: 1.00`
- `max_iterations: 8`
- `forbidden_actions`: [slack:post, slack:send, email:send, pagerduty:trigger, statuspage:update]
- `halt_and_ask_when`: a message would need to go out immediately but the facts are still unknown; severity is disputed; a message could imply a customer commitment; the audience for an update is unclear
- **body:** one short paragraph — read-only by design; a write is a signal to stop and hand back, not to route around the brake.

### `trust.yaml`
```yaml
show_work: required
cite_sources: required
uncertainty: must_flag
escalate_when:
  - confidence < 0.6
  - severity == sev1 AND audience includes customers
  - a fact in a draft can't be traced to a signal
  - a regulator-notifiable threshold may be crossed
```

### Skills (2)

**`skills/draft-status-update.md`** — `id: comms.draft-status-update`, `version: "1.0.0"`, `name: draft-status-update`, `when: An incident needs a status update drafted for a specific audience.`, `context: [context/audience-rubric.md]`, `tools: [slack:conversations.history, pagerduty:incidents.get]`, `cost_tier: T2`, `outputs: StatusUpdate[]`. Body: gather known facts from incident signals (no invention), pick the audience via the rubric, draft with severity in plain language + what's known + what's unknown + next-update time; never reproduce secrets referenced in signals.

**`skills/cadence-plan.md`** — `id: comms.cadence-plan`, `version: "0.1.0"`, `name: cadence-plan`, `when: A team needs to know when and to whom the next incident updates go.`, `tools: []` (empty — exercises the empty-tools path), `cost_tier: T2`, `outputs: CadencePlan`. Body: map severity → cadence, list audiences per cadence, flag when cadence should escalate, return a plan.

### `context/audience-rubric.md`
A short rubric referenced by `draft-status-update` (resolves to `x_context`). Covers audience types (exec / eng / customer), severity → cadence, tone calibration, and what each audience needs to hear. (~150-250 words.)

### `README.md`
One-paragraph fixture description, mirroring `tests/fixtures/security-triage/README.md`.

## Compiled artifacts (generated, not hand-written)

- `examples/incident-comms/agent.yaml` — produced by `armature-cabinet build tests/fixtures/incident-comms -o examples/incident-comms`. Carries `Expertise:`/`Temperament:`/`Success looks like:` prose, `x_context` (resolved audience-rubric), `x_outputs`, non-GitHub `tools`, `x_kind: partner`, `x_source: incident-comms`, `x_schema_version: 0.1.0`.
- `examples/incident-comms/incident-comms.safety.yaml` — advisory fragment with `block` rules for the five forbidden actions + `contracts.max_iterations: 8` + `_cost_ceiling_usd` + `suggested_escalation_gates`.

## Workflow + e2e (extend, not replace)

Extend `examples/workflow.yml` to carry **both** agents in one workflow:
```yaml
name: triage-and-comms-demo
version: "1.0"
model_tiers:
  small: { provider: anthropic, model: claude-haiku-4-5-20251001 }
role_type_defaults:
  worker: small
agent_library:
  security-triage:
    path: security-triage/agent.yaml
  incident-comms:
    path: incident-comms/agent.yaml
stages:
  - id: triage
    agent: security-triage
    output_mode: text
    depends_on: []
  - id: comms
    agent: incident-comms
    output_mode: text
    depends_on: [triage]
```
The existing `triage` stage id is unchanged, so the existing e2e assertion stays green.

Extend `tests/test_e2e.py` with `test_incident_comms_stage_roundtrips`: load `examples/workflow.yml`, find the `comms` stage, assert `stage.agent is None`, `role.name == "Incident Comms Partner"`, `role.type.value == "worker"`, `len(role.skills) == 2`, and `{"comms.draft-status-update"} <= set(spec.skill_library)`. (Both agents' skills merge into `spec.skill_library`; ids don't collide — `appsec.*` vs `comms.*`.)

## Unit tests — new `tests/test_compile_comms.py`

- `test_loads_comms_package`: `pkg.id == "incident-comms"`, `kind == "partner"`, `len(skills) == 2`.
- `test_compiles_comms_bundle`: `role.name == "Incident Comms Partner"`, `type == "worker"`, 2 skills, `skill_library` keys == `role.skills`; description contains `"Out of scope"`, `"cite the evidence"`, `"Stop and hand back to a human"`, `"Expertise:"`, `"Temperament:"`, `"Success looks like:"`.
- `test_comms_tools_are_non_github`: **no** tool in `role.tools` starts with `github:` (the explicit generality assertion); asserts `slack:conversations.history` and `pagerduty:incidents.get` are present.
- `test_comms_skill_context_resolved`: `skill_library["comms.draft-status-update"]["x_context"]` has key `context/audience-rubric.md` with non-empty body.
- `test_comms_skill_outputs_passed_through`: `skill_library["comms.cadence-plan"]["x_outputs"] == "CadencePlan"`.
- `test_comms_safety_fragment_is_advisory`: blocked tools include `slack:post` and `email:send`; `contracts["max_iterations"] == 8`; `_note` present.

## Global Constraints (unchanged from M1, must still hold)

- Runtime deps `armature-agents>=0.3.5` + `pyyaml>=6.0`; no new deps. `requires-python = ">=3.11"`.
- Bundle validates as `CompiledAgent`; every `role.skills` id is a key in `skill_library`; every `SkillDef` has `content`.
- `role.type ∈ {worker, orchestrator, judge, researcher}`; `kind` → `x_kind` (default worker).
- No fields outside `extra="allow"`; extra metadata only on `Role`/`SkillDef`, `x_`-prefixed.
- Soft/hard guardrail split preserved; `*.safety.yaml` advisory.
- `cabinet.yaml` (source) vs `agent.yaml` (output) naming unchanged.
- One-directional; no core edits, no folder parsing in core, no network fetching.
- **M2-specific invariant: NO changes to `src/armature_cabinet/`.** Compiler/loader/validate/cli/errors/model are untouched. Only fixtures, examples, and tests are added/edited.

## Success criteria

- All tests pass (28 → ~35): existing 28 unchanged + ~6 new `test_compile_comms.py` + 1 new e2e.
- `armature-cabinet build tests/fixtures/incident-comms -o examples/incident-comms` succeeds; `armature-cabinet validate tests/fixtures/incident-comms` exits 0.
- Both stages round-trip through real `armature 0.3.5`.
- `git diff` over `src/armature_cabinet/` is empty across all M2 commits.

## Non-goals (M2)

- `when`-based skill selection (M3).
- CI / wheel / lint (M4).
- "Writing a cabinet agent" docs guide (M5).
- Carrying `tool_resolution`/`tags`/`maturity`/`owner`/`runtime_hints` as `x_` metadata (deferred richness).
- A third agent, marketplace/shelf fetching, role types other than worker.