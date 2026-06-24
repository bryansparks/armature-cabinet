# Self-Improving Deep Agents in a Live Harness

**How Armature's self-improvement extends beyond prompt edits to richly-defined Cabinet
agents — and why that combination is uncommon.**

**Date:** 2026-06-24
**Companion spec:** `docs/superpowers/specs/2026-06-24-cabinet-evolve-design.md` (the
technical `evolve` surface)

---

## 1. The premise, corrected

A common framing of "self-improving agents" reduces the remedy to: *watch the agent fail,
then rewrite its prompt.* That framing undersells what Armature already does and misreads
what Cabinet agents are.

**Armature's remedy is already broader than prompts.** The `improve` flow
(`SelfImproveRunner` + `SpecRefiner`) operates over a configurable `EditableSurface` set —
prompts (`descriptions`) by default, but also `retry_counts`, `timeouts`, `model_tiers`,
and (under review) `schemas`, stage structure, and `safety_rules`. In parallel, the LoRA
adapter lifecycle edits **model weights** — a low-rank delta trained from exported run
traces, bound to `SkillDef`s, with continual learning to resist catastrophic forgetting and
promotion policies governing when a new version becomes `latest`. So the remedy substrate
already spans four layers:

```
text (prompt)  →  structure (schema/stages)  →  config (retries/timeouts/tiers)  →  weights (LoRA)
```

The genuine gap is not "prompt vs. richer prompt." It is that **none of these surfaces are
aware of a Cabinet agent's internal decomposition.**

## 2. What a Cabinet agent *is*

An Armature agent without Cabinet is an inline `role:` block — a name, a description, maybe
a tool list. Ephemeral, shallow. A Cabinet agent is a **folder of authored files**, each
answering one question:

| File | Answers | Depth it adds |
|---|---|---|
| `cabinet.yaml` | *What is this and whose is it?* | id, kind, owner, maturity, runtime hints |
| `soul.md` | *Who is it?* | role, expertise, temperament, standards, refusals, voice |
| `mandate.md` | *What's it for?* | goal, success_looks_like, out_of_scope |
| `brakes.md` | *What can't it do?* | forbidden_actions, halt_and_ask_when, ceilings |
| `trust.yaml` | *How does it prove its work?* | show_work, cite_sources, uncertainty, escalate_when |
| `skills/*.md` | *What can it do?* | named procedures — `when` trigger, `tools`, `cost_tier`, output type |
| `context/*.md` | *What does it lean on?* | rubrics, schemas, signal lists cited by skills |

The compiler collapses this folder into Armature's standard `{role, skill_library}`
bundle. Cabinet compiles; Armature runs. One-directional.

## 3. The gap, precisely

When `improve` runs against a Cabinet agent, it edits the **flattened bundle prose**, not
the folder. Three consequences:

1. **Edits don't round-trip.** The next `cabinet build` overwrites the bundle's prose —
   the improvement is erased.
2. **Structure is lost.** "Tighten `trust.yaml.cite_sources`" cannot be expressed as a
   prose-rewrite of one flattened blob; the structured intent is destroyed.
3. **Attribution is wrong-grained.** Traces are keyed by `stage_id` + `role_type`, but a
   Cabinet agent's behavior is an emergent blend of six files. A parse failure could be a
   `mandate.md` problem, a `context/` rubric problem, or a `skills/` output-discipline
   problem — the current taxonomy can't tell.

## 4. The reframing: the folder *is* the remedy taxonomy

Cabinet's file decomposition is not an obstacle to self-improvement — it is a
better-factored target than a monolithic prompt ever was. Each file owns a distinct
failure class, and that mapping is deterministic:

| Trace symptom | Responsible Cabinet file | Lever |
|---|---|---|
| `OUTPUT_INVALID`, schema/parse failures | `mandate.md`, `skills/*.md`, `context/*.md` | tighten output contract |
| `LOW_SKILL_ACTIVATION`, wrong/no tool calls | `skills/*.md` (`when`, `tools`), `soul.md` expertise | sharpen trigger / declare tools |
| refusals, over-caution, false halts | `brakes.md` (`halt_and_ask_when`, `forbidden_actions`) | relax/retarget limits |
| hallucination, uncited claims | `trust.yaml` (`cite_sources`, `show_work`) + `context/*.md` | evidence discipline |
| tone/voice drift | `soul.md` (`temperament`, `voice`) | voice |
| scope creep | `mandate.md` (`out_of_scope`) | boundaries |
| latency/cost | `cabinet.yaml` (`runtime_hints`, `cost_tier`) | config |
| forgetting / skill regression | continual-learning prior + context refresh | weights |

The promise of self-improving *deep* agents is fulfilled not by editing a richer prompt
but by editing the **right file** in the richer definition.

## 5. The design: `cabinet evolve`

(Full technical detail in the companion spec. Summary here.)

A new Cabinet surface — `cabinet evolve <agent-id>` — closes a loop across both repos,
preserving the one-directional boundary:

```
Armature runs → records enriched traces → Cabinet reads them
  → ROUTER (pure) picks (file, surface, gate) from the routing table
  → PROPOSER (LLM, sandboxed to that one file) writes a frontmatter-aware patch
      + predicted_fixes / predicted_regressions
  → SURFACE GATE: auto-apply prose/skills, review-queue guardrails
  → VERSIONING: write agents/<id>/v<N>/; HQS-gated latest pointer (rollback on regression)
  → (optional) decide weights-vs-text → shell out to `armature adapter create`
  → recompile bundle → Armature runs again → verify prior predictions next cycle
```

**The safety-critical decision is kept out of the LLM's hands.** A pure-Python router —
unit-tested, data-driven (`routing_rules.yaml`) — is the *only* thing that chooses which
file is edited. The LLM only writes content inside the file it's handed. Guardrail files
(`brakes`, `trust`, `cabinet.yaml` limits) are hard-coded to `review` and cannot be
overridden by `--apply`. Unmodeled symptoms produce a **no-op report** — there is no
fallback to "let the LLM pick a file."

## 6. Why this is uncommon

Three properties rarely co-occur in "self-improving agent" systems:

1. **Structured, not free-text, improvement.** Most self-improvement systems rewrite a
   prompt blob. Here the unit is a *typed file* in a factored definition, with a
   frontmatter-aware patch format, re-validated against the agent's own schema before
   landing. The improvement is auditable, diffable, and reversible at file granularity.

2. **Falsifiable, not hopeful.** Every proposal carries `predicted_fixes` and
   `predicted_regressions`; the next cycle verifies them against fresh traces and computes
   a `drift_score` that detects oscillation. Versions promote only on measured HQS gain.
   No edit ships without a later check; no check is silent.

3. **Multi-substrate, by design.** Text edits (cheap, interpretable, reversible) and LoRA
   weight edits (tacit patterns text can't express) are two complementary remediation
   paths *for the same agent*, gated by the same router and governed by the same
   falsifiable contract. A skill that resists textual fixes can be routed to adapter
   training instead — and the decision is data-driven, not manual.

Together: a deep agent whose **definition** (not just its memory) improves measurably
inside a running harness, with the structure that lets you trust the changes.

## 7. What is deliberately *not* conflated

Cabinet's `AGENT-VS-WORKFLOW.md` draws a sharp line between what an agent **is** (its
definition) and what it **has seen** (its memory). Self-improvement edits the former; a
state store accumulates the latter. `evolve` reads traces (performance signal) and writes
to the folder (definition). It does not become the agent's memory. The loop is closed by
traces + scheduler cadence, not by the agent introspecting on its own history. Keeping
that line clean is what lets a stateless, reproducible agent also be a self-improving one.

## 8. Decisions and rejected alternatives

| Decision | Chosen | Rejected (why) |
|---|---|---|
| Ownership model | Layered auto/apply | Human-in-the-loop only (too slow to fulfill the promise); fully autonomous (guardrail-erosion risk); proposal-only dry (doesn't deliver the promise) |
| Versioning | Versioned + HQS-gated promotion | In-place + history log (no clean rollback / no HQS gate); hybrid (two mental models) |
| Attribution | Cross-repo trace enrichment | Cabinet-side inference only (can't distinguish wrong-skill from poorly-written-skill); defer enrichment (ships with known-weak attribution) |
| LoRA scope | Decide-in-evolve, train-via-CLI | Recommend-only (loop not closed); train inside evolve (breaks one-directional boundary) |
| Routing architecture | Deterministic router + sandboxed LLM proposer | LLM-routed meta-harness (LLM picks the target file → no safety boundary); pure heuristic (too blunt to deliver the promise) |
| v1 coverage | 2 prose routes + 2 locked guardrails | Full 8-route table (ships routes we can't yet validate); 3-route set (defers guardrails, which is where safety gating matters most) |

## 9. Predicted improvements

What the loop should produce, concretely, once v1 runs against real workflows:

- **Falling `OUTPUT_INVALID` rates** on agents whose mandate/skill output contracts were
  tightened by R1/R2 — the most directly traceable win.
- **Rising hands-free rate (`hfr`)** as R3 sharpens `when` triggers and tool declarations,
  reducing escalations from missed tool calls.
- **Guardrail changes that surface in the review queue, not in incidents** — G1/G2 routes
  exist precisely so that the *first* time a refusal or hallucination pattern appears, a
  human sees a proposed `brakes`/`trust` edit rather than discovering it post-mortem.
- **A measurable, non-zero LoRA-eligibility rate** — a small fraction of skills routed to
  adapter training rather than prose, confirming the multi-substrate path is real and not
  vestigial.
- **A `drift_score` that stays low** — the oscillation detector catching any
  fix→regress→fix cycle early, which is itself the evidence that the falsifiable contract
  is working.

The falsifiability cuts both ways: if `predicted_fixes` don't land or `drift_score` climbs,
that is the system telling us the routing table is wrong — and the table is data, so the
fix is a policy edit, not a code change.

## 10. Prerequisites and sequencing

1. **Richness-metadata carry-through** (NEXT-STEPS #1) — emit `cabinet.yaml`'s
   `summary`/`maturity`/`owner`/`tags`/`runtime_hints` as `x_*` in the bundle. Hard
   prerequisite for trace joinability and for the proposer's model-tier resolution.
2. **Cross-repo trace enrichment** — `agent_id`, `agent_version`, `active_skill_id(s)`
   on `TraceRecord`. The keystone; everything routes through it.
3. **Per-agent versioning field** — `schema_version` is repo-wide today; evolve needs a
   per-agent semantic `version:` on the manifest to version folders.
4. **`evolve` surface** itself, v1 routes only.

(1) and (2) can land in parallel; (3) is small; (4) is the bulk of the implementation work
and is what the companion spec details.

---

*This document is the "why." The companion spec is the "how."*