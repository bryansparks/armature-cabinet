# armature-cabinet

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

## Build

```bash
pip install armature-cabinet
armature-cabinet build ./security-triage -o dist/security-triage
```

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

| Cabinet block | Becomes |
|---|---|
| `soul.md` (role, standards, refusals, body) | composed into `role.description` |
| `mandate.md` (goal, out_of_scope) | folded into `role.description` |
| `skills/*.md` body | `skill_library[id].content` |
| skill `tools:` frontmatter | unioned into `role.tools` |
| skill `when`/`cost_tier`/`version` | preserved as `x_*` metadata (`extra="allow"`) |
| `brakes` / `trust` (behavioral) | instruction prose in `role.description` |
| `brakes` / `trust` (hard enforcement) | **advisory** `*.safety.yaml` fragment |

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

`--skill <id>` (repeatable) attaches only chosen skills. This is the seed of the
"woodshop" model: each skill declares a `when`, and a future build mode will
select skills by matching the workflow's task instead of attaching all of them.

## Develop

```bash
pip install -e ".[dev]"
pytest
```
