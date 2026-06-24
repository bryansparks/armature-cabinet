# armature-cabinet — giving Armature agents depth

> A conceptual overview for anyone (human or AI) who needs to understand what
> `armature-cabinet` is, how it folds onto the **Armature** agent harness, and
> what new capability it creates — especially as context for building a UI on
> top of it. Self-contained: you don't need to have read the repo.

## 1. The one-paragraph version

**Armature** runs *workflows* — pipelines of stages, each stage driven by an
*agent*. An agent, to Armature, is a compiled **bundle** (`{ role, skill_library }`
in an `agent.yaml`). **`armature-cabinet`** is the compiler that produces those
bundles from a rich, human-authorable **folder of files** — a "cabinet agent."
The folder is the *source* (a voice, standards, several skills, guardrails, an
evidence discipline); the bundle is the *build artifact* Armature runs. Cabinet
also manages a *library* of agents and assembles them into a *team* workflow
that Armature launches. Net effect: Armature agents go from ephemeral, inline
one-liners to reusable, deep, self-governing teammates you author once and run
in teams.

```
                author                     compile                    run
  cabinet agent folder  ──armature-cabinet build──▶  agent.yaml  ──armature run──▶  workflow / team
  (soul, skills, brakes…)                          (role + skills)
```

## 2. Armature in one paragraph (the host)

Armature (≥0.3.5) is an "ELF ecosystem agent harness runner." It ships a CLI
(`armature`) with `run`, `validate`, `new`, `serve`, `optimize`, `report`,
`replay`, `dashboard`, etc. A **workflow spec** (`workflow.yml`) declares
`model_tiers` (which LLM/provider for which role size), `role_type_defaults`
(which tier each role type uses), an **`agent_library`** (named references to
compiled agent bundles), and **`stages`** (each stage references an agent from
the library, has an id, an output mode, and `depends_on` other stages — a DAG).
`armature run <workflow.yml>` executes the stages in dependency order, each
stage driven by its agent's `role` + `skill_library`. At load time, Armature
resolves each `agent_library` entry to its bundle, merges the bundle's
`skill_library` into the spec, and clears the stage's agent reference (the stage
then runs the resolved role). The bundle Armature loads is a **`CompiledAgent`**:
exactly `{ role, skill_library }` — nothing more.

## 3. The problem cabinet solves

Without cabinet, an Armature agent is an inline `role:` block typed into a
workflow — ephemeral, redefined every time, shallow (a name + a description +
maybe a tool list). Real agents have **depth**: a voice, standards they hold to,
refusals, several named skills with triggers and procedures, hard guardrails,
and an evidence discipline (show your work, cite, flag uncertainty). Writing all
that inline, per workflow, is unworkable, and the result isn't reusable.

`armature-cabinet` lets you author that depth once, as a **folder of files**,
and compiles it down to the bundle Armature consumes. The rich folder is the
*source*; the bundle is the *build artifact*. Armature core never parses the
folder format — it only ever loads a standard `CompiledAgent`. So Armature stays
simple; cabinet is a pure frontend that adds depth without Armature having to
know about it.

## 4. The core boundary (the thing to internalize)

- **Cabinet compiles; Armature runs.** One-directional. Cabinet depends on
  `armature-agents` (so its output validates as a `CompiledAgent`); Armature
  never depends on cabinet.
- **The bundle is the seam.** `{ role, skill_library }` is the entire interface
  between them. Cabinet's job is to produce a valid one; Armature's job is to
  run it.
- **The compiler is pure.** Folder in → dict out, no side effects beyond the CLI
  writing files. No network, no LLM inside the compiler. (The authoring *wizard*
  and the *team* run-handoff are separate surfaces; the compile core stays pure.)

## 5. The cabinet folder format (the source you author)

A cabinet agent is a folder:

```
my-agent/
├── cabinet.yaml      # manifest: id, name, kind (partner|clone), summary, schema_version, ...
├── soul.md           # always-on identity — role, expertise, temperament, standards, refusals + voice body
├── mandate.md        # what it's for — goal, success_looks_like, out_of_scope (+ optional body)
├── brakes.md         # optional — hard limits: cost_ceiling, max_iterations, forbidden_actions, halt_and_ask_when
├── trust.yaml        # optional — how it proves its work: show_work, cite_sources, uncertainty, escalate_when
├── skills/*.md       # procedures — frontmatter (id, when, tools, context, cost_tier, version, outputs) + body
└── context/*.md      # reference material (rubrics, schemas) referenced by skills
```

- **`cabinet.yaml`** is the thin manifest: `id`, `name`, `kind` (`partner` or
  `clone`), `schema_version`, `summary`, plus optional provenance (`maturity`,
  `owner`, `tags`, `tool_resolution`, `runtime_hints`).
- **`soul.md`** is the always-on identity — the role, what it's expert at, its
  temperament, the standards it holds to, what it refuses to do, and a voice
  paragraph. It can also set `armature_role_type` to override the mapped role
  type (`worker` | `orchestrator` | `judge` | `researcher`; default `worker`).
- **`mandate.md`** is the goal — what it's for, what success looks like, what's
  out of scope.
- **`brakes.md`** is the hard limits — a cost ceiling, a max-iterations cap, a
  list of forbidden actions (e.g. `gmail:send`, `web:form.submit`), and the
  conditions under which it should stop and hand back to a human.
- **`trust.yaml`** is the evidence discipline — `show_work`, `cite_sources`,
  `uncertainty`, and `escalate_when` conditions.
- **`skills/*.md`** are the procedures the agent can perform — each with a
  trigger (`when`), the tools it uses, context references, a cost tier, a
  version, an `outputs` type, and the procedure body.
- **`context/*.md`** is reference material (rubrics, schemas) that skills
  reference by path; the referenced content is carried into the bundle.

> **Agents are expected to be authored primarily by AI tools** (like Claude),
> not just humans. The format and the docs are deliberately *dual-audience* —
> human-readable prose **and** AI-ingestible structured reference (explicit field
> schemas, the validation rules stated outright, complete copyable examples).

## 6. What compiles where (the mapping)

| Cabinet source | Compiles to (in the `agent.yaml` bundle) |
|---|---|
| `cabinet.yaml` `id` / `name` / `kind` / `schema_version` | `x_source` / `role.name` / `x_kind` (+ mapped `role.type`) / `x_schema_version` |
| `soul.md` `role` / `expertise` / `temperament` / `standards` / `refusals` / body | composed into `role.description` prose ("Your role: …", "Expertise: …", "Temperament: …", "Standards you hold to: …", "You will not: …", + the voice) |
| `soul.md` `armature_role_type` (optional) | overrides `role.type` |
| `mandate.md` `goal` / `success_looks_like` / `out_of_scope` | folded into `role.description` ("Your mandate: …", "Success looks like: …", "Out of scope: …") |
| `brakes.md` `forbidden_actions` | `role.description` prose ("…never take these actions…") **and** `block` rules in the safety fragment |
| `brakes.md` `halt_and_ask_when` | `role.description` prose ("Stop and hand back to a human when: …") |
| `brakes.md` `max_iterations` / `cost_ceiling_usd` | `contracts.max_iterations` / `contracts._cost_ceiling_usd` in the safety fragment |
| `trust.yaml` `show_work` / `cite_sources` / `uncertainty` | `role.description` prose ("When you respond, always: …") |
| `trust.yaml` `escalate_when` | `suggested_escalation_gates` in the safety fragment |
| each `skills/*.md` body | `skill_library[id].content` |
| skill `name` / `when` | `skill_library[id].description` |
| skill `when` / `tools` / `cost_tier` / `version` | `x_when` / `x_tools` / `x_cost_tier` / `x_version` |
| skill `context` refs | `x_context` (a mapping of ref → resolved body) |
| skill `extra` (e.g. `outputs`) | `x_<key>` (any unknown frontmatter rides through) |
| `context/*.md` | referenced by skills → resolved into `x_context` |

### The one subtlety that matters: the soft/hard guardrail split

A `CompiledAgent` carries **`role` + `skill_library` only** — it cannot carry
`Contract` limits, `ToolSafetyRule`s, or gates. So an agent's brakes/trust
**can't be enforced from inside the bundle**. Cabinet handles this two ways:

1. **Soft (automatic):** the behavioral intent (recommends-only, refusals,
   halt-and-ask, show-work, cite, flag-uncertainty) is folded into the role's
   prose, so the agent **self-governs**.
2. **Hard (advisory):** a `<id>.safety.yaml` fragment is emitted with the `block`
   rules for forbidden actions, contract limits, and suggested escalation gates.
   The workflow author **merges it into the workflow's `safety:`/`contracts:`
   by hand** — that's where hard enforcement lives (in the workflow, not the
   bundle).

So the bundle is the *identity + capability*; the safety fragment is the
*hard-enforcement handoff*. Don't try to smuggle hard enforcement into the bundle
— it won't validate or will be silently dropped.

## 7. The bundle Armature loads

```yaml
# agent.yaml — the CompiledAgent
role:                       # an Armature Role (extra fields allowed)
  name: <str>
  type: worker              # worker | orchestrator | judge | researcher
  description: <the composed prose — identity, mandate, behavioral guardrails>
  tools: [<union of all skill tools>]
  skills: [<ids that must exist as keys in skill_library>]
  x_kind: partner           # original cabinet kind, rides along
  x_source: <id>            # original cabinet id
  x_schema_version: "0.1.0"
skill_library:              # dict[id -> SkillDef]
  <skill_id>:
    id: <skill_id>
    description: <name or when or id>
    content: <the procedure body>      # OR path: <relative>; exactly one required
    x_when: <trigger>
    x_tools: [...]
    x_cost_tier: T2
    x_version: "1.0.0"
    x_context: {<ref>: <body>}         # resolved context refs
    x_outputs: <type>                  # any extra skill frontmatter, x_-prefixed
```

Armature resolves this at load: each `role.skills` id must be a key in
`skill_library`; the skill_library merges into the spec; the stage's `agent`
reference clears after resolution. The bundle is the whole contract between
cabinet and Armature.

## 8. The CLI (the operations a UI would wrap)

```
armature-cabinet new      <id> [--out DIR]                     # interactive authoring wizard (rich + questionary)
armature-cabinet build    <folder> [--skill ID]... [--when "<task>"] [-o DIR] [--no-safety]
armature-cabinet build    <library> --all [--bundles DIR]      # bulk-compile every agent in a library dir
armature-cabinet validate <folder> [--skill ID]... [--when "<task>"]
armature-cabinet list     <library>                            # enumerate a library (rich table)
armature-cabinet team     <library> [--agent id]... [--bundles DIR] [--out WF] [--dry-run | --run]
```

- **`new`** — an interactive wizard that walks you through every field (identity
  → soul → mandate → brakes → trust → skills) with per-field teaching hints, and
  writes a complete, valid cabinet folder.
- **`build`** — compile one agent folder to an `agent.yaml` (+ advisory
  `*.safety.yaml`). `--skill` attaches only named skills; `--when "<task>"`
  selects skills whose `when` matches the task (the **woodshop** model — pull
  down only the tool the cut needs).
- **`build --all`** — compile every agent in a library directory in one command
  (continue-on-failure).
- **`validate`** — load + validate + compile in memory; writes nothing; clean
  errors (no tracebacks) for missing/malformed input, duplicate skill ids,
  dangling context refs, bogus `--skill` ids, etc.
- **`list`** — enumerate a library directory's agents (id/name/kind/skills/valid)
  in a table.
- **`team`** — assemble selected library agents into a sequential-pipeline team
  workflow (`workflow.yml`) and hand off to `armature run`: `--dry-run` validates
  the team through real Armature (no API key); `--run` executes it.

## 9. The author → library → team → run loop

This is the end-to-end capability cabinet adds on top of Armature:

```bash
# 1. author an agent (interactively, or by hand, or by an AI given the guide)
armature-cabinet new gmail-reader --out agents/

# 2. keep agents in a folder of adjacent agents (a library)
armature-cabinet list agents                      # see them
armature-cabinet build agents --all               # compile the whole library -> dist/

# 3. assemble a team and run it via armature
armature-cabinet team agents --dry-run            # armature validates the team
armature-cabinet team agents --run                # armature runs the team (needs a provider/key)
```

A "library" is just a directory of cabinet agent folders (each with a
`cabinet.yaml`). `team` generates an Armature workflow that references the
compiled bundles (`agent_library`) and wires the agents into a sequential
pipeline (`stages` with `depends_on`), then hands off to `armature run`. The
generated workflow is editable (the DAG, the model tiers, the order) — cabinet
gives you a sensible default team; you refine it.

## 10. How this adds depth to an armature team

The thesis: **an Armature team is only as deep as its agents.** With inline
roles, a "team" is a pipeline of one-paragraph personas. With cabinet agents, a
team is a pipeline of:

- **Voices** — each agent has a soul (role, expertise, temperament, standards,
  refusals, a voice paragraph), not just a name.
- **Skills** — each agent carries named, triggered procedures (`when`/`tools`/
  `outputs`), so a stage knows what its agent can actually do and when to invoke
  each skill. The woodshop `--when` selection lets you compile an agent with only
  the skills a given task needs.
- **Guardrails** — each agent has brakes (forbidden actions, halt-and-ask
  conditions) and trust (show-work, cite, flag-uncertainty). The behavioral parts
  self-govern via the role prose; the hard parts become an advisory safety
  fragment the workflow enforces.
- **Evidence discipline** — show your reasoning, cite the source behind every
  claim, state your confidence. Folded into the role, so it's always on.
- **Reusability + provenance** — author once, run in many workflows; the
  `x_kind`/`x_source`/`x_schema_version` metadata (and the optional
  `maturity`/`owner`/`tags`) let a team/library know where each agent came from.
- **Domain generality** — the format isn't secretly shaped to one domain. The
  reference agents span security triage, incident comms, Gmail triage, and
  research synthesis, all compiled by the unchanged compiler.

So a cabinet-powered Armature team is a *roster of deep, self-governing
specialists* you assemble and launch — not a stack of inline prompts.

## 11. Principles (don't regress these)

- **Compiler purity** — `loader`/`compiler`/`validate`/`select` are pure (folder
  in → `AgentPackage`/dict/`ValidationResult`/ids out), no I/O/network/LLM. Only
  the CLI writes files; the wizard and team run-handoff are separate surfaces.
- **One-directional boundary** — cabinet compiles; Armature runs. Never edit
  Armature core from cabinet; never parse the folder format in core.
- **Soft/hard guardrail split** — behavioral intent → role prose (self-govern);
  hard enforcement → advisory safety fragment (workflow merges it). Never smuggle
  hard enforcement into the bundle.
- **`x_` metadata only** on `Role`/`SkillDef` (both `extra="allow"`); no invented
  fields elsewhere.
- **`cabinet.yaml` = source; `agent.yaml` = output.** Don't confuse them.
- **Dual-audience docs/tooling** — agents are AI-authored; docs stay
  human-readable + AI-ingestible.

## 12. Reference agents (concrete examples of the depth)

Two example agents live in `agents/`, each exercising the full spec from a
different angle — useful as templates to compare new agents against:

- **`gmail-reader`** — a read-only Gmail triage partner (`worker` role type;
  `gmail:*` tools). 4 skills (triage-inbox, summarize-message, draft-reply,
  detect-phishing), 3 context rubrics (label, summary, phishing signals). Brakes
  forbid `send`/`archive`/`delete`/`trash`/`mark_read`/`draft.send`; trust
  requires show-work + cite + flag-uncertainty. Demonstrates: a read-only
  operational partner, all-tooled skills, the safety fragment as the
  hard-enforcement handoff for destructive actions.
- **`research-synthesis`** — a research synthesis partner (`researcher` role type
  via `armature_role_type`; `web:`/`pdf:`/`x:` tools). 4 skills (distill-source,
  find-themes, frame-actions, write-brief), 3 context rubrics. Demonstrates: the
  `researcher` role-type override, web/pdf tools, and **skills with no tools**
  (the empty-tools path — pure-reasoning skills like find-themes/frame-actions).

Both validate, compile, and load through real Armature (`armature run --dry-run`
on a workflow referencing their bundles succeeds).

## 13. How a UI maps onto this

A UI on top of armature-cabinet is, at its core, a friendly face over the
**operations** in §8, with the **cabinet folder as the source of truth** and the
**bundle as the runnable artifact**. Concretely, a UI would expose:

- **Author** — a form/wizard over the cabinet schema (the `new` command's
  fields), writing a cabinet folder. The schema is fully specified (§5, §6) and
  dual-audience, so a UI can render each field with its type/required/allowed
  values + a hint of what it compiles to. The output is a folder on disk (or in a
  store) that's the editable source.
- **Library** — a collection view over a directory of agent folders (`list` +
  `build --all`). Each agent card shows id/name/kind/skills/valid; the UI can
  validate + compile the library. The folder is the canonical state; the UI is a
  view + editor over it.
- **Compile** — turning a folder into a bundle (`build`). The UI shows the
  compiled `role.description` (the folded prose) + the `skill_library` + the
  safety fragment — i.e., "here's what Armature will actually get."
- **Team assembly** — a DAG editor over the library's agents (`team`): pick
  agents, order them, wire `depends_on`, choose model tiers, generate the
  `workflow.yml`. The default is a sequential pipeline; the UI lets you draw the
  real DAG.
- **Run / validate** — hand off to `armature run` (validate via `--dry-run` with
  no API key; execute with one). The UI surfaces Armature's run/trace/report
  output. The boundary stays clean: the UI calls cabinet to author/compile/
  assemble, and Armature to run.

The **source-of-truth model** matters for the UI: the cabinet folder is the
editable, versionable, diff-able source. The bundle and the workflow are
generated artifacts. A UI that edits the folder (not the bundle) keeps agents
re-compilable + re-runnable, and lets an AI author/modify agents by editing the
folder per the (AI-ingestible) schema. The safety fragment is the place where
the UI shows the user "here's the hard enforcement you must merge into your
workflow" — a deliberate handoff, not a silent auto-wire (until a future Armature
core change lets a bundle carry its own safety/contract).

## 14. Current state + what's next

**Built (M1–M8):** the compiler (validation, clean errors, field-carrying,
`--when` woodshop selection), the authoring wizard (`new`), library management
(`list`/`build --all`), team generation + `armature run` handoff (`team`), CI
(ruff lint + test + wheel build, green on push/PR), and the dual-audience docs
(authoring guide + this overview). 75 tests, ruff-clean, e2e round-trips through
real `armature 0.3.5`, compiler untouched since M3.

**Deferred (in `NEXT-STEPS.md`):** carrying the dropped "richness" metadata
(`summary`/`tags`/`maturity`) as `x_`; `when`-matcher improvements (stemming,
weighting, top-N); `blocks`/`blocks_extra` path resolution (the loader currently
uses canonical filenames); the marketplace/shelf (`shelf://` fetching); carrying
safety/contract inside the bundle (an Armature core change); PyPI publish. Plus
M8 follow-ups surfaced by the reference agents: the `team` command's default
model tiers only cover `worker` (a library with `researcher`/`judge`/etc. agents
needs all four role-type tiers in the generated workflow), a team-DAG editor, a
`team --build` auto-build, and a `--model` flag.

---

**TL;DR for a UI builder:** armature-cabinet turns a folder of files into the
agent bundle Armature runs, manages a library of those agents, and assembles them
into a team workflow Armature launches. The folder is the source of truth (deep,
editable, AI-authorable); the bundle is the runnable artifact; the safety
fragment is the hard-enforcement handoff. Your UI wraps author → library →
compile → team → run, editing folders and calling the CLI, while Armature does
the actual execution.