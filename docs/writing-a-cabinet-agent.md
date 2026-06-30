# Writing a cabinet agent

A dual-audience authoring guide. Human readers get the prose; AI tools (e.g.
Claude) that ingest this document get the structured reference — the compile
mapping, validation rules, CLI reference, and a complete copyable worked
example — and can produce a valid agent folder from a domain alone.

> **AI-authoring posture.** An AI given this guide plus a domain description
> can produce a valid cabinet-agent folder. Read the *Field reference* (§3)
> and *Validation rules* (§4) before generating files; use the worked example
> in §5 as a template.

---

## 1. Overview

A **cabinet agent** is an agent authored as a folder of small, opinionated
files and then *compiled* into the bundle an Armature workflow runs. You never
hand-write the runtime bundle; you author the **source folder** and let
`armature-cabinet build` produce the bundle.

Two artifacts, two names — keep them distinct:

| Artifact | Name | Who writes it |
|---|---|---|
| Source folder | `cabinet.yaml` + `*.md` + `trust.yaml` + `skills/` + `context/` | You (the author) |
| Compiled bundle | `agent.yaml` (+ `<id>.safety.yaml`, advisory) | `armature-cabinet build` |

The flow is:

```
author writes folder  ──▶  armature-cabinet build <folder>  ──▶  armature run
   (cabinet.yaml)              (→ agent.yaml)                    (the workflow)
```

`cabinet.yaml` is the *source* manifest that names the agent and points at its
blocks; `agent.yaml` is the *output* `CompiledAgent` bundle the runtime
consumes. `validate` checks the source folder in memory and writes nothing;
`build` writes `agent.yaml` plus an advisory safety fragment.

**Why dual-audience.** The structured tables and verbatim blocks below are the
machine-readable contract an AI generator must satisfy. The prose around them
is for the human learning the format. Both describe the same M1–M4 compiler.

---

## 2. Folder anatomy

A cabinet-agent source folder has this shape:

```
my-agent/
├── cabinet.yaml        # manifest: id, name, kind, block paths, thick extras
├── soul.md             # who the agent is (role, expertise, temperament, voice)
├── mandate.md          # what it's for (goal, success, out-of-scope)
├── brakes.md           # hard limits (forbidden actions, halt conditions, ceilings)
├── trust.yaml          # response discipline (show work, cite, escalate)
├── skills/             # one *.md per skill (frontmatter + body)
│   ├── do-thing.md
│   └── ...
└── context/            # reference prose that skills pull in via `context:`
    └── rubric.md
```

What each file is for:

- **`cabinet.yaml`** — the manifest. Declares `id`, `name`, `kind`, and points
  at the block files. Required; everything else hangs off it.
- **`soul.md`** — identity. The role, expertise, temperament, standards,
  refusals, and the voice paragraph. Compiles into `role.description` prose.
- **`mandate.md`** — purpose. The goal, what success looks like, and what is
  explicitly out of scope. Compiles into more `role.description` prose.
- **`brakes.md`** — hard limits. Forbidden actions, halt-and-ask conditions,
  iteration/cost ceilings. `forbidden_actions` compiles into `role.description`
  prose **and** `block` rules on the bundle (`safety_rules`, armature ≥ 0.5.0);
  the ceilings remain advisory in `<id>.safety.yaml`.
- **`trust.yaml`** — response discipline. `show_work` / `cite_sources` /
  `uncertainty` compile into `role.description` prose; `escalate_when` compiles
  into `suggested_escalation_gates` in `<id>.safety.yaml`.
- **`skills/*.md`** — one file per skill. YAML frontmatter (`id`, `when`,
  `tools`, `cost_tier`, `version`, `context`, plus any extras) + a Markdown
  body that is the skill's instructions. Compiles into `skill_library[id]`.
- **`context/*.md`** — reference prose that skills cite by relative path in
  their `context:` list. Resolved into the skill's `x_context`. Unreferenced
  context files are loaded but not emitted.

`soul.md` and `mandate.md` are the thin core. `brakes.md`, `trust.yaml`,
`skills/`, and `context/` are the thick optional extras. The loader
resolves all of these by **canonical filename** — it reads `soul.md`,
`mandate.md`, `brakes.md`, `trust.yaml`, `skills/`, and `context/` via
hardcoded paths, regardless of what `cabinet.yaml` declares. The
`blocks:` and `blocks_extra:` fields in `cabinet.yaml` are declarative
metadata, **not currently consumed by the loader** (like the dropped
richness fields below).

---

## 3. Field reference

For each file: a human description, then a schema table. The **Compile mapping**
table that follows is the authoritative "compiles to" reference — it is the
current M1–M4 behavior and is included verbatim.

### `cabinet.yaml`

The manifest. Thin required core plus thick optional metadata.

| field | type | required? | allowed values | compiles to |
|---|---|---|---|---|
| `id` | string | required | non-empty string | `x_source` on role (also names the output dir) |
| `name` | string | optional (defaults to `id`) | any string | `role.name` |
| `kind` | string | optional (defaults to `partner`) | `partner` \| `clone` | `role.type` (mapped; default `worker`) + `x_kind` |
| `schema_version` | string | optional | any version string | `x_schema_version` (omitted when null) |
| `blocks.soul` | path | expected (not enforced) | path to a `.md` file | declarative; loader uses the canonical filename `soul.md` regardless (a missing file yields an empty block, no error) |
| `blocks.mandate` | path | expected (not enforced) | path to a `.md` file | declarative; loader uses the canonical filename `mandate.md` regardless (a missing file yields an empty block, no error) |
| `blocks_extra.brakes` | path | optional | path to a `.md` file | declarative; loader uses the canonical filename `brakes.md` regardless |
| `blocks_extra.trust` | path | optional | path to a `.yaml` file | declarative; loader uses the canonical filename `trust.yaml` regardless |
| `blocks_extra.skills` | path | optional | path to a directory | declarative; loader uses the canonical `skills/` directory regardless |
| `blocks_extra.context` | path | optional | path to a directory | declarative; loader uses the canonical `context/` directory regardless |
| `summary` | string | optional | any string | authored but currently dropped (future "richness") |
| `maturity` | string | optional | any string | authored but currently dropped |
| `owner` | string | optional | any string | authored but currently dropped |
| `tags` | list[string] | optional | any strings | authored but currently dropped |
| `tool_resolution` | string | optional | any string | authored but currently dropped |
| `runtime_hints` | map | optional | any map | authored but currently dropped |

### `soul.md`

Identity. YAML frontmatter + a Markdown voice paragraph in the body.

| field | type | required? | allowed values | compiles to |
|---|---|---|---|---|
| `type` | string | optional | any string (informational) | not emitted directly |
| `role` | string | optional | any string | `role.description` prose: "Your role: …" |
| `expertise` | list[string] | optional | any strings | `role.description` prose: "Expertise:\n- …" |
| `temperament` | string | optional | any string | `role.description` prose: "Temperament: …" |
| `standards` | list[string] | optional | any strings | `role.description` prose: "Standards you hold to:\n- …" |
| `refusals` | list[string] | optional | any strings | `role.description` prose: "You will not:\n- …" |
| `armature_role_type` | string | optional | any role type | overrides `role.type` |
| *(body)* | markdown | optional | prose | `role.description` prose (the voice) |

### `mandate.md`

Purpose. YAML frontmatter + optional body.

| field | type | required? | allowed values | compiles to |
|---|---|---|---|---|
| `goal` | string | optional | any string | `role.description` prose: "Your mandate: …" |
| `success_looks_like` | list[string] | optional | any strings | `role.description` prose: "Success looks like:\n- …" |
| `out_of_scope` | list[string] | optional | any strings | `role.description` prose: "Out of scope: …" |
| *(body)* | markdown | optional | prose | `role.description` prose |

### `brakes.md`

Hard limits. YAML frontmatter + optional body. Produces description prose,
`block` rules on the bundle (`safety_rules`, armature ≥ 0.5.0), and advisory
ceilings/gates in `<id>.safety.yaml`.

| field | type | required? | allowed values | compiles to |
|---|---|---|---|---|
| `forbidden_actions` | list[string] | optional | tool ids (e.g. `slack:post`) | `role.description` prose ("…never take these actions: …") **and** `safety_rules` (`block`, `condition: null`) on the bundle — enforced when a workflow references the agent (armature ≥ 0.5.0) |
| `halt_and_ask_when` | list[string] | optional | any conditions | `role.description` prose: "Stop and hand back to a human when:\n- …" |
| `max_iterations` | integer | optional | positive integer | `contracts.max_iterations` in `<id>.safety.yaml` |
| `cost_ceiling_usd` | number | optional | any number | `contracts._cost_ceiling_usd` in `<id>.safety.yaml` (note: no USD field in core yet) |
| *(body)* | markdown | optional | prose | `role.description` prose |

### `trust.yaml`

Response discipline. Plain YAML (no body).

| field | type | required? | allowed values | compiles to |
|---|---|---|---|---|
| `show_work` | string | optional | `required` \| `on_request` \| (others: no prose) | `role.description` prose: "When you respond, always:\n- …" |
| `cite_sources` | string | optional | `required` \| others | `role.description` prose (same block) |
| `uncertainty` | string | optional | `must_flag` \| others | `role.description` prose (same block) |
| `escalate_when` | list[string] | optional | any conditions | `suggested_escalation_gates` in `<id>.safety.yaml` |

### `skills/*.md`

One file per skill. YAML frontmatter + Markdown body.

| field | type | required? | allowed values | compiles to |
|---|---|---|---|---|
| `id` | string | required | non-empty, unique in package | `skill_library[id].id` (the key) |
| `name` | string | optional | any string | `skill_library[id].description` (name, else when, else id) |
| `when` | string | optional | any task description | `skill_library[id].description` (fallback) **and** `x_when` |
| `tools` | list[string] | optional | tool ids | `x_tools` **and** unioned into `role.tools` |
| `cost_tier` | string | optional | e.g. `T1`/`T2`/`T3` | `x_cost_tier` |
| `version` | string | optional | any version string | `x_version` |
| `context` | list[path] | optional | refs into `context/*.md` | `x_context` (mapping ref → resolved body) |
| *(any other frontmatter)* | any | optional | e.g. `outputs` | `x_<key>` |
| *(body)* | markdown | optional | the skill's instructions | `skill_library[id].content` |

### `context/*.md`

Reference prose. Not frontmatter-driven.

| field | type | required? | allowed values | compiles to |
|---|---|---|---|---|
| *(body)* | markdown | optional | prose | referenced by skills → resolved into `x_context`; unreferenced context files are loaded but not emitted |

### Compile mapping (authoritative)

The full source-to-bundle mapping, verbatim from the M1–M4 compiler:

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
| `brakes.md` `forbidden_actions` (list) | `role.description` prose **and** `safety_rules` (`block`, `condition: null`) on the bundle — enforced when a workflow references the agent (armature ≥ 0.5.0); merged as a non-overridable floor |
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

---

## 4. Validation rules

`armature-cabinet validate <folder>` checks every rule below **before** it
attempts a build. Structural problems raise `CabinetError` — a clean
one-line message, not a Python traceback. Errors exit 1; warnings exit 0.

**Errors (exit 1):**
- folder missing or not a directory
- `cabinet.yaml` missing
- malformed YAML in any block
- `id` missing, empty, or non-string
- `kind` present but not `partner` or `clone`
- duplicate skill `id`
- skill `id` empty
- a `--skill` id not present in the package
- a skill `context` ref that does not resolve to a `context/*.md` file
- **`kind: clone` must declare `forbidden_actions`.** A clone that acts unattended
  with no hard brakes is a hard error at `validate` *and* `build`. Partner agents
  may omit brakes (they recommend only).

**Warnings (exit 0):**
- `name` missing (defaults to `id`)
- `kind` missing (defaults to `partner`)
- `schema_version` missing

`validate` loads + validates + compiles in memory and writes nothing. Use it
as the fast feedback loop while authoring.

---

## 5. Authoring a new agent (walkthrough)

This walks through the real `incident-comms` fixture end to end. Each file's
contents are shown inline so you can copy the shape into a new domain. The
walkthrough order is: `cabinet.yaml` → `soul.md` → `mandate.md` →
`brakes.md` → `trust.yaml` → `skills/` → `context/`.

### 5.1 `cabinet.yaml`

Start with the manifest. Declare the `id` (this becomes the output dir name
and `x_source`), `name`, `kind`, and point at the block files. Thick extras
and richness metadata (`summary`, `maturity`, `owner`, `tags`,
`tool_resolution`, `runtime_hints`) are authored here but currently dropped
by the compiler — keep them for human readers and future richness.

```yaml
schema_version: "0.1.0"

# --- thin core (required) ---
id: incident-comms
name: Incident Comms Partner
kind: partner
summary: Drafts incident status updates and stakeholder comms for a human to send; never sends itself.
blocks:
  soul: soul.md
  mandate: mandate.md

# --- thick / optional ---
maturity: L1
owner: bryan
tags: [incidents, comms, oncall, status]

blocks_extra:
  brakes: brakes.md
  trust: trust.yaml
  skills: skills/
  context: context/

# How declared tools resolve to real capabilities.
# We piggy-back on the org's Slack / PagerDuty adapters. Skills name slack:* / pagerduty:* ops.
tool_resolution: slack

runtime_hints:
  default_cost_tier: T2          # T1 trust-critical | T2 routine | T3 exploratory
```

### 5.2 `soul.md`

Identity. Frontmatter lists the role, expertise, temperament, standards, and
refusals; the body is the voice paragraph. Everything here compiles into
`role.description` prose.

```markdown
---
type: partner
role: Incident communications lead
expertise:
  - incident response comms
  - audience calibration
  - severity framing
  - cadence and pacing
temperament: calm, clear, audience-aware
standards:
  - never speculate past the known facts
  - severity in plain language, no jargon-only updates
  - one update per decision point, not per emotion
  - name the audience for every message
refusals:
  - recommends only; never sends, publishes, or posts to any channel
  - won't soften severity to avoid discomfort
  - won't promise an ETA it can't justify with a signal
---

You read an incident the way a calm comms lead does on a bad night: assume the
on-call is sleep-deprived, assume the stakeholders are anxious, and treat your
job as subtraction. Most of what could be said does not need to go out this
hour. Your value is finding the one update that does and writing it so a tired
human can send it as-is, without rewriting you.

You are not a channel. You don't send, post, or publish. You hand a drafted,
audience-named shortlist to a human and get out of the way. When the facts
aren't known yet, you say so plainly rather than filling the silence with
speculation.
```

### 5.3 `mandate.md`

Purpose. `goal`, `success_looks_like`, `out_of_scope` compile into more
`role.description` prose.

```markdown
---
goal: Keep stakeholders informed with the minimum comms that land the right information at the right time, without the on-call becoming a scribe.
success_looks_like:
  - stakeholders know what is happening and what to do next
  - no update goes out that an on-call has to retract
  - comms cadence matches severity, not anxiety
  - every draft names its audience and the evidence behind it
out_of_scope:
  - actually sending, publishing, or posting anything
  - deciding severity (the incident commander's call)
  - engineering remediation
  - customer account or billing actions
---

This partner exists because incident comms noise costs the same tired human as
a missed update — both are paid by the people already underwater. The mandate
is drafting: audience, evidence, cadence — nothing more.
```

### 5.4 `brakes.md`

Hard limits. `forbidden_actions` compiles into **both** description prose and
`block` rules on the bundle (`safety_rules`, armature ≥ 0.5.0); `halt_and_ask_when` into prose;
`max_iterations` and `cost_ceiling_usd` into `contracts` in the safety
fragment.

```markdown
---
# Hard limits. The runtime treats these as constraints, not suggestions.
cost_ceiling_usd: 1.00
max_iterations: 8
forbidden_actions:
  - slack:post
  - slack:send
  - email:send
  - pagerduty:trigger
  - statuspage:update
halt_and_ask_when:
  - a message would need to go out immediately but the facts are still unknown
  - severity is disputed
  - a message could imply a customer commitment
  - the audience for an update is unclear
---

Read-only by design. If a task seems to require sending or publishing, that is
a signal to stop and hand back to a human — not to find a way around the brake.
```

### 5.5 `trust.yaml`

Response discipline. `show_work`/`cite_sources`/`uncertainty` become the
"When you respond, always" prose block; `escalate_when` becomes
`suggested_escalation_gates` in the safety fragment.

```yaml
show_work: required          # every draft comes with its reasoning
cite_sources: required       # each claim links to the incident signal behind it
uncertainty: must_flag       # state confidence and what would change it

escalate_when:
  - confidence < 0.6
  - severity == sev1 AND audience includes customers
  - a fact in a draft can't be traced to a signal
  - a regulator-notifiable threshold may be crossed
```

### 5.6 `skills/`

One file per skill. Frontmatter (`id`, `version`, `name`, `when`, `context`,
`tools`, `cost_tier`, `outputs`) + a numbered instruction body. The `context`
list points into `context/*.md` and is resolved into `x_context`. `tools` are
unioned into `role.tools`. Any extra frontmatter key (here `outputs`) becomes
`x_<key>`.

`skills/draft-status-update.md`:

```markdown
---
id: comms.draft-status-update
version: "1.0.0"
name: draft-status-update
when: An incident needs a status update drafted for a specific audience.
context:
  - context/audience-rubric.md
tools:
  - slack:conversations.history
  - pagerduty:incidents.get
cost_tier: T2
outputs: StatusUpdate[]
---

1. Pull the known facts from the incident signals (the Slack incident thread,
   the PagerDuty incident record) — never invent.
2. Pick the audience with the audience rubric (exec / eng / customer); draft
   one update per audience.
3. Write in plain language: what's happening, what's known, what's still
   unknown, and when the next update lands.
4. Severity in human words — not just `sev1`. Name impact in terms the
   audience cares about.
5. Return one `StatusUpdate` per audience, each tagged with its audience and
   the signal it rests on. Never reproduce a secret referenced in a signal —
   point to its location only.
```

`skills/cadence-plan.md`:

```markdown
---
id: comms.cadence-plan
version: "0.1.0"
name: cadence-plan
when: A team needs to know when and to whom the next incident updates go.
tools: []
cost_tier: T2
outputs: CadencePlan
---

1. Read the current severity — the incident commander's call; do not override it.
2. Map severity to cadence: sev1 → every 30 min, sev2 → hourly, sev3 → every
   4h, sev4 → summary at close. Cadence matches severity, not anxiety.
3. For each cadence point, list which audiences receive an update.
4. Flag when cadence should escalate (severity rises) or de-escalate (stable
   or resolved).
5. Return a `CadencePlan` with the schedule and the audiences per slot.
```

### 5.7 `context/`

Reference prose that skills pull in. `audience-rubric.md` is cited by
`draft-status-update`'s `context:` list and resolved into that skill's
`x_context`. Plain Markdown — no frontmatter required.

`context/audience-rubric.md`:

```markdown
# Audience rubric

Calibrate every message to its audience. The same incident reads differently
to each.

**Exec / leadership.** Wants impact, exposure, and what they need to decide or
approve. One paragraph. Lead with business impact, not mechanism. No acronyms
without a gloss.

**Engineering / on-call.** Wants mechanism, current hypothesis, and what's
being tried. Technical detail welcome. Lead with what's known and the active
mitigation.

**Customer / external.** Wants what's affected, what to do, and when to expect
resolution. Plain language, no internal tool names, no blame. Lead with the
user-visible impact and the workaround if any.

**Severity → cadence.** sev1: every 30 min, all audiences. sev2: hourly, exec
+ eng. sev3: every 4h, eng + customer-only-if-affected. sev4: summary at close.

**Tone.** Calm, factual, no reassurance that isn't backed by a signal.
`Unknown` is a valid and respected status — say it rather than fill the
silence.
```

### 5.8 Validate

With the folder in place, close the loop:

```bash
armature-cabinet validate incident-comms     # → ok: incident-comms (partner)
armature-cabinet build incident-comms -o dist/incident-comms
```

---

## 6. Compiling

The CLI has two subcommands. `build` writes the bundle; `validate` writes
nothing.

```
armature-cabinet build    <folder> [-o DIR] [--skill ID]... [--when "<task>"] [--no-safety]
armature-cabinet validate <folder> [--skill ID]... [--when "<task>"]
```

- `build` writes `<out>/agent.yaml` (the `CompiledAgent` bundle, carrying `safety_rules`) and `<out>/<id>.safety.yaml` (advisory limits/gates, when brakes/trust have advisory content).
- `validate` loads + validates + compiles in memory; writes nothing; exit 0 clean / 1 on errors.
- `--skill <id>` (repeatable): attach only the named skills.
- `--when "<task>"`: woodshop selection — keyword-overlap match against each skill's `when`; selects skills sharing ≥1 content keyword, ranked by overlap count (ties → source order); no-match → warning + a 0-skill bundle + exit 0. `validate --when` previews the ranked selection.
- `--when` and `--skill` are mutually exclusive.

### Examples

Validate a folder (fast feedback, writes nothing):

```bash
armature-cabinet validate tests/fixtures/incident-comms
ok: incident-comms (partner)
```

Build a bundle into `dist/`:

```bash
armature-cabinet build tests/fixtures/incident-comms -o dist/incident-comms
compiled 'incident-comms' (partner)
  bundle  -> dist/incident-comms/agent.yaml
  role    -> 2 skill(s), 2 tool(s)
  safety  -> dist/incident-comms/incident-comms.safety.yaml  (advisory; merge into your workflow)
```

Attach only one skill from a package:

```bash
armature-cabinet build tests/fixtures/incident-comms --skill comms.cadence-plan -o dist/cadence-only
```

Preview woodshop selection for a task (writes nothing):

```bash
armature-cabinet validate tests/fixtures/security-triage --when "prioritize open Dependabot alerts"
matched 2 skill(s): appsec.triage-dependabot-alerts, appsec.triage-secret-scanning
ok: security-triage (partner)
```

No-match is a warning, not an error — the command still exits 0:

```bash
armature-cabinet validate tests/fixtures/incident-comms --when "prioritize open Dependabot alerts"
warning: no skills matched task: "prioritize open Dependabot alerts"
ok: incident-comms (partner)
```

---

## 7. Guardrails

A CompiledAgent bundle carries `role` + `skill_library` + `safety_rules` —
its `block` rules (from `brakes.forbidden_actions`) are a hard, non-overridable
floor that armature auto-merges into the workflow at load (armature ≥ 0.5.0).
`armature-cabinet build` also emits an **advisory** `<id>.safety.yaml` fragment
alongside `agent.yaml` whenever `brakes.md` or `trust.yaml` contribute advisory
content (iteration cap, USD ceiling, escalation gates). Merge that fragment's
advisory limits into your workflow by hand — the runtime does not enforce them
(unlike the bundle's `block` rules, which are).

### The soft / hard split

- **Soft guardrails** live in `role.description` prose — the "You will not",
  "Stop and hand back to a human when", "never take these actions", and
  "When you respond, always" blocks. The model reads them as instructions.
  They shape behavior but are not enforced by the runtime.
- **Hard guardrails (block rules)** live on the bundle's `safety_rules` —
  `block` rules for each `forbidden_actions` entry. The runtime enforces these
  as constraints, not suggestions, when a workflow references the agent
  (armature ≥ 0.5.0); merged as a non-overridable floor. On older core they
  degrade to soft prose only.
- **Advisory limits** remain in `<id>.safety.yaml` —
  `contracts.max_iterations` / `contracts._cost_ceiling_usd` and
  `suggested_escalation_gates` from `trust.yaml`. The runtime does not enforce
  these yet; merge them into your workflow by hand.

Both come from the same source fields (`forbidden_actions` produces *both*
prose and `block` rules), so the soft voice and the hard rule stay in sync by
construction.

### The advisory fragment

For `incident-comms`, `build` emits `incident-comms.safety.yaml`:

```yaml
_note: "ADVISORY. The CompiledAgent bundle carries this agent's block rules
  (`safety_rules`) as HARD constraints already. Merge these remaining advisory
  limits (`contracts:`) and escalation gates into your workflow."
contracts:
  max_iterations: 8
  _cost_ceiling_usd: 1.0
suggested_escalation_gates:
- confidence < 0.6
- severity == sev1 AND audience includes customers
- a fact in a draft can't be traced to a signal
- a regulator-notifiable threshold may be crossed
```

### Merging into a workflow

The bundle's `block` rules (`safety_rules`) are **auto-merged** into the
workflow's `safety_rules` at load when a workflow references the agent
(armature ≥ 0.5.0) — as a non-overridable floor. You do not hand-merge those.
The fragment's remaining advisory `contracts:` and `suggested_escalation_gates`
still need manual merge into your workflow. `--no-safety` skips emitting the
fragment when you don't want it.

---

## 8. Wiring into a workflow

A workflow references compiled agents by their `agent_library` entry and runs
them in `stages`. Build each agent's bundle first, then point the workflow at
the resulting `agent.yaml` files.

The two-agent demo at `examples/workflow.yml` wires `security-triage` and
`incident-comms` into a triage-then-comms pipeline:

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

`agent_library` maps a short id to a built `agent.yaml` path; `stages` runs
them in dependency order (`comms` depends on `triage`). To add your own agent,
build it (`armature-cabinet build my-agent -o dist/my-agent`), add an
`agent_library` entry pointing at `dist/my-agent/agent.yaml`, and add a stage
that references it.

That's the whole loop: author the folder, validate, build, wire the bundle
into a workflow, run.
