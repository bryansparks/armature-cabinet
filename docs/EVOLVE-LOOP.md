# The `cabinet evolve` Loop

**How the implemented self-improvement loop works, cycle by cycle — and how to run it.**

**Date:** 2026-06-25
**Implements:** the `evolve` surface shipped on `main` (v1 + the v2 "denser + automatic loop").
**Companion docs:** `docs/DEEP-AGENT-SELF-IMPROVEMENT.md` (the *why* / rationale),
`docs/superpowers/specs/2026-06-25-cabinet-evolve-denser-loop-design.md` (the v2 design spec).

---

## 1. What it does, in one paragraph

`cabinet evolve <folder>` runs **one improvement cycle** against a cabinet agent. It reads that
agent's `armature` run traces, identifies the dominant failure symptom, and routes it — through a
pure, data-driven table — to the **single file** in the agent's folder that owns that failure class.
A sandboxed LLM proposes a frontmatter-aware patch for that one file, plus a falsifiable prediction
(`predicted_fixes` / `predicted_regressions`). The patch is applied under a layered auto/review gate,
written to an atomic version snapshot, and promoted only on a measured HQS gain. Each cycle also
**auto-verifies the previous cycle's prediction**, **auto-rolls-back** regressions, and — when prose
edits are exhausted — **hands the skill off to LoRA adapter training**. State carries across cycles
through a per-agent sidecar. Nothing the LLM produces can pick which file is edited or override a
guardrail.

## 2. The cycle, step by step

One invocation = one cycle. The orchestrator (`evolve/orchestrator.py::run_evolve_cycle`) runs this
sequence:

```
load_package(folder)                              # once per cycle (was twice in v1)
 │
 ├─ 1. read_history(folder)                        ← .evolve/history.jsonl (sidecar)
 │      prose_cycles_without_gain(history)
 │      detect_oscillation(history) → is_oscillating
 │      prior_latest = read_latest(folder)
 │
 ├─ 2. read_summary(traces_db, …,                  ← AgentTraceSummary (None → stop, no record)
 │      latency_threshold_ms, cost_threshold_tokens)   now emits HIGH_LATENCY / HIGH_COST
 │
 ├─ 3. verify_prior(history, summary) → Verdict   # fixed | unfixed | regressed | None
 │      update_last_verified(folder, verdict, vs_cycle)   ← annotates the PRIOR record
 │      → structured missed_predictions [{predicted, observed, verdict}, …]
 │
 ├─ 4. ROUTER (pure) → (target_file, surface, gate, skill_id)
 │      data-driven by routing_rules.yaml; unmodeled symptom → no-op (target_file=None, gate=none)
 │
 ├─ 5. decide_lora(summary, prose_cycles, skill_id)        ← orchestrator-level, NOT a router route
 │      eligible & --apply & trained → handoff_to_adapter → RETURN (no prose edit this cycle)
 │      eligible & not trained       → prose fallback (lora_missed=True) → joins step 6
 │      not eligible                 → normal prose path (step 6)
 │
 ├─ 6. gate = "review" if is_oscillating else decide_gate(decision)
 │      guardrail surface → hard-locked "review" (never auto-applied)
 │      none surface      → "none" (no-op)
 │
 ├─ 7. PROPOSER (LLM, sandboxed to target_file) → patch + predicted_fixes/regressions
 │      SURFACE GATE: apply patch to the LIVE folder iff --apply and gate allows
 │
 ├─ 8. VERSIONING — atomic write_version → versions/<v>/  (+ .proposal.json with hqs)
 │      promote(folder, v, policy=ThresholdPromotionPolicy(min_gain=hqs_promote_min),
 │              current_hqs, new_hqs)   # gain ≥ hqs_promote_min, else latest unchanged
 │
 ├─ 9. _maybe_rollback — trial semantics (only if applied & not promoted & regression):
 │      guardrail-touched        → restore live folder to prior_latest  (unconditional)
 │      non-guardrail drop ≥ θ    → restore live folder to prior_latest
 │      non-guardrail drop < θ    → leave as a TRIAL on the live folder (latest unchanged)
 │
 └─ 10. append_record(folder, this_cycle_record)  → .evolve/history.jsonl
```

Two things to notice. First, **the router is never touched by v2** — it stays a pure symptom→file
mapper. All "automatic" behavior reads the sidecar, not the router. Second, **decide_lora runs
before the normal prose path**: a skill whose prose is exhausted is handed to adapter training
*instead of* another prose edit, and only falls back to prose if the handoff doesn't train.

## 3. The cycle-history sidecar

`<folder>/.evolve/history.jsonl` — one JSON object per line, one record per cycle, append-only. This
is the keystone: every automatic behavior (LoRA eligibility, oscillation, verify) reads it.

```jsonc
{
  "cycle": 3,
  "proposed_file": "skills/draft-reply.md",
  "gate": "auto",
  "surface": "skills",
  "hqs_before": 0.61,
  "hqs_after": 0.58,
  "predicted_fixes": ["OUTPUT_INVALID:draft-reply"],
  "predicted_regressions": ["LOW_SKILL_ACTIVATION:triage-inbox"],
  "verified": {"verdict": "unfixed", "vs_cycle": 2},
  "version": "0.3.0",
  "rolled_back": false
}
```

- `verified` is written by `update_last_verified` — the **only** non-append operation — which
  rewrites the *final* record's `verified` field. It is set by the *next* cycle's `verify_prior`,
  annotating the prior cycle's record with what actually happened to its predictions.
- `hqs_before` is the prior promoted version's HQS (read from `versions/<latest>/.proposal.json` by
  the CLI and threaded in as `current_hqs`). On the **first** cycle it is `null` — and every
  history-derived function guards `None` (no promotion → no rollback, no oscillation, prose-count
  breaks) so a first cycle is always safe.
- Malformed lines are skipped and logged; the cycle proceeds with the well-formed prefix.

**The sidecar is never compiled into a bundle.** `load_package` is allowlist-based — it reads only
the named agent files (`cabinet.yaml`, `soul.md`, `mandate.md`, `brakes.md`, `trust.yaml`,
`skills/*.md`, `context/*.md`); it never walks the tree. So `.evolve/` coexists with the agent
exactly as `versions/` already does. There is no ignore/exclude mechanism and none is needed.

## 4. The four invariants — as enforced

| # | Invariant | The mechanism that enforces it |
|---|---|---|
| 1 | **No file is edited without an explicit route.** | The router (`router.py::route`) is the *only* thing that picks `target_file`. It is pure (no I/O, no LLM, no history) and data-driven. An unmodeled symptom, or one below `min_observations`, returns `target_file=None, gate="none"` → a no-op report. There is no "let the LLM pick a file" fallback. |
| 2 | **Guardrails are never auto-applied.** | `surface_gate.decide_gate` hard-locks any `guardrail` surface to `"review"` **regardless of `--apply`**. So a guardrail proposal is never written to the live folder; it only produces a `.pending` patch for human review. Oscillation *also* forces `"review"`. Only an explicit `--promote` ack advances a guardrail version. |
| 3 | **Every proposal carries a falsifiable prediction, verified next cycle.** | Each proposal emits `predicted_fixes` / `predicted_regressions`, carried on the `CycleResult` and written into the cycle record. The *next* cycle's `verify_prior(history, summary)` compares them against the current dominant symptoms and returns a verdict (`fixed` / `unfixed` / `regressed`); `update_last_verified` annotates the prior record. No prediction is carried and dropped. |
| 4 | **A patch failing `validate.py` is rejected before any version.** | `patch_applier` writes the candidate, runs `validate_package`, and on failure restores the original and raises `PatchReject` — caught before any `write_version`. `write_version` snapshots into `.evolve/.tmp-<v>-<pid>` then `os.replace`-moves it into `versions/<v>/`; on any exception the temp dir is removed and re-raised. No partial `versions/<v>/` can ever exist. |

## 5. The routing table

`src/armature_cabinet/evolve/routing_rules.yaml` — the router is data-driven; this file is the whole
policy. Symptoms are matched against `armature` trace taxonomy.

| Rule | Symptom | Target file | Surface | Gate |
|---|---|---|---|---|
| R1 | `OUTPUT_INVALID` (skill-attributable) | `skills/{skill_id}.md` | skills | auto |
| R2 | `OUTPUT_INVALID` (not skill-attributable) | `mandate.md` | mandate | auto |
| R3 | `LOW_SKILL_ACTIVATION` | `skills/{skill_id}.md` | skills+soul | auto |
| R4 | `HIGH_LATENCY` | `cabinet.yaml` | config | auto |
| R5 | `HIGH_COST` | `cabinet.yaml` | config | auto |
| G1 | `REFUSAL_OR_FALSE_HALT` | `brakes.md` | guardrail | review (locked) |
| G2 | `HALLUCINATION_OR_UNCITED` | `trust.yaml` | guardrail | review (locked) |

- `target_file` is a **template**: `skills/{skill_id}.md` substitutes `{skill_id}` from the routed
  failing skill (`router._pick_skill`). In the proposer's prompt the resolved path is referenced via
  the `FILE(<path>)` marker. No other template variables are supported.
- A symptom must appear ≥ `min_observations` times to fire; the dominant *modeled* symptom wins.
- `_pick_skill` returns the failing, non-healthy skill — attributable if it has failures or declared
  tools that never fired (`SkillStats.fired` is `False` when `tools_declared` is non-empty and none
  were called). This is what makes R1 vs R2 (skill-attributable or not) deterministic.

## 6. The dials

Also in `routing_rules.yaml`. The CLI reads these via `load_rules()` and threads them in.

| Key | Default | What it does |
|---|---|---|
| `min_observations` | `3` | A symptom must appear this many times to route. |
| `hqs_promote_min` | `0.02` | A new version promotes only if HQS improved by ≥ this. |
| `rollback_threshold` | `0.05` | Non-guardrail regressions roll back past this HQS drop; smaller drops stay as a trial. |
| `auto_rollback_guardrail` | `true` | Roll back *unconditionally* if a guardrail-touched run regresses. *(Defense-in-depth: invariant #2 hard-locks guardrails to `review` → `applied=False`, so this branch is unreachable today — it is a forward safety net against a future code path that might apply guardrail patches.)* |
| `latency_threshold_ms` | `3000` | Mean per-row `latency_ms` above this emits `HIGH_LATENCY`. |
| `cost_threshold_tokens` | `8000` | Mean per-row `(input_tokens + output_tokens)` above this emits `HIGH_COST`. |

Because the table is data, a wrong route is a policy edit, not a code change.

## 7. Verify, rollback & oscillation semantics

**Verify (each cycle, observational only).** `verify_prior` compares the *previous* cycle's
`predicted_fixes`/`predicted_regressions` (as symptom tokens) against the *current* dominant
symptoms. Verdict precedence: `regressed` (a predicted regression is now dominant) > `unfixed` (a
predicted fix is still dominant) > `fixed` (none remain). The verdict is written into the prior
record's `verified`. Verify **never blocks** the current proposal — promotion remains HQS-gated
exactly as in v1.

**Rollback (trial semantics — the active safety net).** The trigger is *not* "a promoted version
regressed" (unreachable: the HQS gate only promotes on a gain). The real gap: on `--apply`, the
live folder is patched *before* the promote check; if the gate then blocks promotion (a regression),
the live folder is left patched (worse) while `latest` still points to the prior version — live and
`latest` diverge. Rollback closes that, firing only when `applied and not promoted and
hqs_after < hqs_before`:

- **guardrail-touched** → restore the live folder to `prior_latest` unconditionally.
- **non-guardrail, drop ≥ `rollback_threshold`** → restore to `prior_latest`.
- **non-guardrail, drop < `rollback_threshold`** → leave the patch as a **trial** on the live folder
  (`latest` unchanged) so a minor regression gets a next-cycle chance to prove out.

On restore, the live folder is rolled back to `prior_latest` and the cycle record is marked
`rolled_back: true`. `latest` itself is unchanged — the gate already refused to advance it.

**Oscillation (stops a thrasher).** `detect_oscillation` returns `True` when the last 3 records'
HQS-delta signs flip twice (`+,−,+` or `−,+,−`; a zero delta disqualifies). When true, the cycle's
gate is forced to `"review"` regardless of routing — a thrashing agent stops getting auto-applied.

The clean separation: **verify annotates, the HQS gate decides promotion, the threshold decides
whether a blocked-regression live-folder patch is restored or left as a trial.**

## 8. The LoRA handoff route

LoRA is an **orchestrator-level** decision, not a router route — the router stays pure (no history).
`decide_lora(summary, *, prose_cycles_without_gain, skill_id)` returns eligible iff:

1. **prose is exhausted:** `prose_cycles_without_gain >= 2` (two trailing prose cycles with no HQS
   gain), **and**
2. **the tools are firing correctly:** `stats.fired` is `True` (the skill declared tools and they
   were called) — i.e. *right tools, wrong output*, a tacit pattern a text edit cannot fix.

When eligible and `--apply`, the orchestrator shells out via `handoff_to_adapter` to
`armature adapter create <skill> --from-traces --role-type <kind> [--continual-learning]`. Cabinet
never imports `armature` (one-directional boundary; subprocess only) and never writes the workflow's
`adapter:` binding — it only trains. `HandoffResult.trained` is `True` only when a real invocation
returned exit 0.

- **trained** → the cycle returns with no prose edit (the adapter is the remedy).
- **not trained** (or no `--apply`) → fall back to the prose route and log `missed_predictions` with
  `lora_missed`. This fallback was v1's path, now reached with *real* history-derived
  `prose_cycles_without_gain` instead of only via monkeypatch.

## 9. Running it

```bash
# One cycle, dry (propose only, apply nothing):
armature-cabinet evolve path/to/agent \
  --traces-db ~/.armature/traces.db \
  --skill-tools draft-reply=gmail:draft.create \
  --skill-tools triage-inbox=gmail:messages.list

# One cycle, auto-apply safe surfaces (guardrails still require --promote):
armature-cabinet evolve path/to/agent --apply \
  --skill-tools draft-reply=gmail:draft.create

# Force everything to review (.pending patches only):
armature-cabinet evolve path/to/agent --review

# Verify the prior cycle's predictions against fresh traces:
armature-cabinet evolve path/to/agent --verify

# Manual ack to advance the latest pointer (the only way a guardrail version lands):
armature-cabinet evolve path/to/agent --promote 0.3.0

# Restore the live folder from a prior version snapshot:
armature-cabinet evolve path/to/agent --rollback 0.2.0
```

**Flags:**
- `--apply` — auto-apply prose/skill/config surfaces; guardrails stay review-locked.
- `--review` — emit `.pending` patches only; apply nothing (safe-by-default).
- `--verify` — check the prior cycle's `predicted_fixes` against fresh traces; prints a
  `VerificationResult` JSON and exits (no cycle run).
- `--rollback <VERSION>` — restore the live folder from `versions/<VERSION>/`.
- `--promote <VERSION>` — manually advance `latest` to `VERSION` (explicit human ack).
- `--skill-tools skill_id=tool1,tool2` (repeatable) — maps skills to their declared tools, used by
  the router's skill attribution and `SkillStats.fired`.

A default cycle prints one line of result plus its rationale:
```
rule=R1 target=skills/draft-reply.md gate=auto applied=True version=0.1.1 promoted=True
  OUTPUT_INVALID observed 4x; routing to skills/draft-reply.md
```

**Reading the run:** `cat path/to/agent/.evolve/history.jsonl | jq .` — one record per cycle, with
the `verified` verdict propagating back to the prior record on the next run. The version's
`.proposal.json` (`versions/<v>/.proposal.json`) carries `{version, hqs, predicted_fixes, …}` — this
is what the CLI threads forward as `current_hqs` so the HQS gate works on the CLI path.

**Looping it:** `evolve` runs one cycle per invocation; drive a cadence with a scheduler (cron,
launchd, or Armature's own loop when it lands). Each cycle picks up where the sidecar left off.

## 10. What is deliberately deferred

These are explicit non-goals of the shipped loop, deferred to later sub-projects:

- **Voice-drift → `soul.md`** and **scope-creep → `mandate.md` out_of_scope** — no clean trace signal
  for "the tone drifted" or "the agent went out of scope"; fuzzy detector work, distinct from the
  automation plumbing shipped here.
- **Autonomous `run_loop`** — a self-driving cadence; today you drive cycles externally.
- **State-store memory** — `evolve` edits the *definition* (the folder), not the agent's *memory*; a
  separate state store is a later sub-project (see `docs/AGENT-VS-WORKFLOW.md` for the line between
  what an agent *is* and what it *has seen*).
- **Bundle safety fragments** and **marketplace / `shelf://`** — separate v2 sub-projects.

---

*This document is the "how it works + how to run it." For the why, see
`DEEP-AGENT-SELF-IMPROVEMENT.md`. For the full design (decisions, rejected alternatives), see the v2
spec linked at the top.*