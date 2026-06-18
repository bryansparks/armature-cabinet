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
  (soul, skills, brakes...)                          (role + skills)
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
both under `tests/fixtures/` and `examples/`.

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
| `brakes.md` `forbidden_actions` (list) | `role.description` prose **and** `block` rules in `<id>.safety.yaml` |
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

A `CompiledAgent` carries **role + skills only** — not `Contract` limits,
`ToolSafetyRule`s, or gates. So an agent's **brakes and trust can't be enforced
from inside the bundle**. `armature-cabinet` handles this two ways:

1. **Soft (automatic):** the behavioral intent (recommends-only, refusals,
   halt-and-ask, show-work, cite, flag-uncertainty) is folded into the role's
   prose, so the agent self-governs.
2. **Hard (advisory):** a `*.safety.yaml` fragment is emitted with the
   `block` rules, contract limits, and suggested escalation gates. You merge it
   into your workflow's `safety:` / `contracts:` sections by hand.

Making bundles able to *carry* their own safety/contract is the next candidate
change to Armature core. Until then, hard enforcement is opt-in at the workflow.

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
