# armature-cabinet

[![CI](https://github.com/bryansparks/armature-cabinet/actions/workflows/ci.yml/badge.svg)](https://github.com/bryansparks/armature-cabinet/actions/workflows/ci.yml)

Give Armature agents depth.

Armature runs workflows whose stages reference reusable agents from an
`agent_library` (core ≥ 0.3.5). A referenced agent is a **compiled bundle** —
`{ role, skill_library }` in an `agent.yaml`. Writing those bundles by hand is
fine for a one-liner like `echo`, but a real agent has a voice, standards,
several skills, guardrails, and an evidence discipline.

`armature-cabinet` lets you author an agent as a **folder of files** and compiles
it down to the bundle Armature consumes. The rich folder is the *source*; the
bundle is the *build artifact*. Core never has to understand the folder format —
it only ever loads a standard `CompiledAgent`.

```
                author                     compile                    run
  cabinet agent folder  ──armature-cabinet build──▶  agent.yaml  ──armature run──▶  workflow
  (soul, skills, brakes...)                    (role + skills + safety_rules)
```

## The cabinet folder

```
security-triage/
├── cabinet.yaml      # manifest: id, name, kind (partner|clone), summary, ...
├── soul.md           # always-on identity — role, standards, refusals, voice
├── mandate.md        # what it's for (goal, out_of_scope)
├── brakes.md         # hard limits & stop conditions
├── trust.yaml        # how it proves its work (show-work, cite, escalate)
├── skills/*.md       # procedures — frontmatter (id, when, tools, cost_tier) + body
└── context/*.md      # reference material (rubrics, schemas)
```

The format generalizes beyond security: two fixtures demonstrate it —
`security-triage` (GitHub/appsec) and `incident-comms` (Slack/incident-comms) —
both under `tests/fixtures/` and `examples/`. Eight fuller reference agents live
under [`agents/`](#reference-agents) — a Gmail triage partner, a research
synthesis partner, and a three-agent marketing deliberation team with channel
adapters.

## Reference agents

`agents/` ships eight agents that exercise the full format — useful as templates
and as proof the format isn't shaped to one domain:

| Agent | Kind / role type | Shows |
|---|---|---|
| `gmail-reader` | partner / worker | read-only Gmail triage; all-tooled skills; destructive actions blocked via the bundle's `safety_rules` (armature ≥ 0.5.0) |
| `research-synthesis` | partner / researcher | the `researcher` role-type override; web/pdf tools; **empty-tools** (pure-reasoning) skills |
| `marketing-ideator` | partner / worker | generates 3+ candidate messages from a seed |
| `marketing-debater` | partner / worker | critiques candidates on clarity, resonance, risk, brand-fit, over-claiming |
| `marketing-judge` | partner / judge | settles on one message, or declares none good enough and loops back |
| `social-adapter` | partner / worker | adapts a message to Instagram, Snapchat, X without altering substance |
| `blog-writer` | partner / worker | turns a message into a short blog post |
| `short-video-ideator` | partner / worker | Shorts/TikTok scripts + shot ideas |

The three marketing agents form a reusable **deliberation team**
(ideator → debater → judge). Every agent is `partner` kind — they recommend; they
never post or send. `armature-cabinet build agents --all` compiles the lot.

## Build

```bash
pip install armature-cabinet
armature-cabinet build ./security-triage -o dist/security-triage
```

`validate <folder>` checks the source in memory and writes nothing — the fast
feedback loop while authoring. `--skill <id>` (repeatable) attaches only chosen
skills; `--when "<task>"` selects skills by keyword overlap against each
skill's `when`. See [writing a cabinet agent](docs/writing-a-cabinet-agent.md)
for the full CLI reference.

Produces:

- `dist/security-triage/agent.yaml` — the `CompiledAgent` bundle. Point an
  `agent_library` entry at it and reference it from a stage:

  ```yaml
  agent_library:
    security-triage: { path: dist/security-triage/agent.yaml }
  stages:
    - id: triage
      agent: security-triage
  ```

- `dist/security-triage/<id>.safety.yaml` — see below.

## What compiles where

| Cabinet source | Compiles to |
|---|---|
| `cabinet.yaml` `id` | `x_source` on role (also names the output dir) |
| `cabinet.yaml` `name` | `role.name` |
| `cabinet.yaml` `kind` (`partner`\|`clone`) | `role.type` (mapped; default `worker`) + `x_kind` |
| `soul.md` `armature_role_type` (optional) | overrides `role.type` (else mapped from `kind`, default `worker`) |
| `cabinet.yaml` `schema_version` | `x_schema_version` (omitted when null) |
| `soul.md` `role` / body | `role.description` prose |
| `soul.md` `expertise` (list) | `role.description` prose: "Expertise:\n- …" |
| `soul.md` `temperament` (str) | `role.description` prose: "Temperament: …" |
| `soul.md` `standards` / `refusals` | `role.description` prose |
| `mandate.md` `goal` | `role.description` prose: "Your mandate: …" |
| `mandate.md` `success_looks_like` (list) | `role.description` prose: "Success looks like:\n- …" |
| `mandate.md` `out_of_scope` (list) | `role.description` prose: "Out of scope: …" |
| `brakes.md` `forbidden_actions` (list) | `role.description` prose **and** `safety_rules` (`block`) on the bundle — enforced when merged at load (armature ≥ 0.5.0) |
| `brakes.md` `halt_and_ask_when` | `role.description` prose (e.g. "Stop and hand back to a human when: …") |
| `brakes.md` `max_iterations` / `cost_ceiling_usd` | `contracts.*` in `<id>.safety.yaml`[^cc] |
| `trust.yaml` `show_work`/`cite_sources`/`uncertainty` | `role.description` prose: "When you respond, always:\n- …" |
| `trust.yaml` `escalate_when` (list) | `suggested_escalation_gates` in `<id>.safety.yaml` |
| skill body | `skill_library[id].content` |
| skill `name` / `when` | `skill_library[id].description` (name, else when, else id) |
| skill `when` | `x_when` |
| skill `tools` (list) | `x_tools` **and** unioned into `role.tools` |
| skill `cost_tier` / `version` | `x_cost_tier` / `x_version` |
| skill `context` (refs into `context/`) | `x_context` (mapping ref → resolved body) |
| skill `extra` (any other frontmatter, e.g. `outputs`) | `x_<key>` |
| `context/*.md` | referenced by skills → resolved into `x_context`; unreferenced files loaded but not emitted |

`cabinet.yaml` richness metadata (`summary`, `maturity`, `owner`, `tags`,
`tool_resolution`, `runtime_hints`) is authored but currently dropped — kept for
human readers and future richness.

[^cc]: `cost_ceiling_usd` → `contracts._cost_ceiling_usd` (advisory; no USD
contract field in Armature core yet, hence the leading underscore).

## The one thing to know about guardrails

A `CompiledAgent` carries **role + skills + `safety_rules`**. As of armature
0.5.0, a bundle's `block` rules (from `brakes.forbidden_actions`) are **enforced**:
when a workflow references the agent, armature merges the rules into the
workflow's `safety_rules` at load. An agent's `block` rules are a **non-overridable
floor** — a workflow can only add restrictions, never remove them; a workflow
`allow` on a tool the agent forbids is dropped, and the agent's block fires first.
Soft (automatic): the behavioral intent (recommends-only, refusals, halt-and-ask,
show-work, cite, flag-uncertainty) is folded into the role's prose, so the agent
self-governs even on older core.

**Prerequisite:** enforcement requires armature ≥ 0.5.0. On older core, the
bundle's `safety_rules` are silently ignored (degraded to soft-prose only —
not broken, not enforced).

**Still advisory** (the bundle cannot carry these yet — no enforced core target):
the USD cost ceiling, the iteration cap, and suggested escalation gates. These
remain in the `*.safety.yaml` fragment for you to merge by hand. A `clone` agent
without `forbidden_actions` is a hard compile/validate error — a clone that acts
unattended must declare hard brakes.

## Compile-time skill selection

`--skill <id>` (repeatable) attaches only the named skills. `--when "<task>"`
selects skills by keyword overlap against each skill's `when` — the "woodshop"
model: skills declare a `when`, and `--when` matches the workflow's task instead
of attaching all of them. `--skill` and `--when` are mutually exclusive.
`validate` checks a folder in memory and writes nothing.

```bash
armature-cabinet validate ./my-agent
armature-cabinet build ./my-agent -o dist/my-agent
armature-cabinet build ./my-agent -o dist/my-agent --when "prioritize open Dependabot alerts"
```

See [writing a cabinet agent](docs/writing-a-cabinet-agent.md) for the full
mapping, validation rules, and CLI reference.

## Develop

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

CI (lint / test / build) runs on every push and PR — see the [actions](https://github.com/bryansparks/armature-cabinet/actions).
For authoring an agent, see [writing a cabinet agent](docs/writing-a-cabinet-agent.md).

## Documentation

- [Into Armature Agents](docs/INTRO-ARMATURE-AGENTS.md) — what a cabinet agent
  *is*: the soul, mandate, brakes, trust, skills, and context, and why each is
  more than a prompt. Read this first.
- [Agent vs. Workflow](docs/AGENT-VS-WORKFLOW.md) — where an agent definition
  ends and an Armature workflow begins; orchestrators, subagents, and
  cadence-triggered vs. event-triggered teams.
- [Writing a cabinet agent](docs/writing-a-cabinet-agent.md) — the full
  field-by-field authoring guide, validation rules, and CLI reference.
- [System overview](docs/armature-cabinet.md) — the compile boundary, the CLI,
  the author → library → team → run loop, and how a UI maps onto it.

## Status

Early / experimental (`0.2.0`). The compiler core is stable, ruff-clean, and it
round-trips through real `armature 0.5.0` end-to-end. Bundle `safety_rules`
enforcement requires armature ≥ 0.5.0. The authoring surfaces (the `new` wizard, library
`list`/`build --all`, and `team` generation) are newer. Reference agents are
`maturity: L1`. See [`NEXT-STEPS.md`](NEXT-STEPS.md) for what's deferred.

## License

MIT — see [LICENSE](LICENSE).
