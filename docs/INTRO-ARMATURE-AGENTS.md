# Intro to Armature Agents — what a cabinet agent *is*

> An onboarding doc for the **agent** itself: what one is, why it's more than a
> prompt, and what each part of its folder does. If you only read one thing before
> authoring or editing an agent, read this. Self-contained — you don't need to have
> read the system overview (`docs/armature-cabinet.md`) or the authoring guide
> (`docs/writing-a-cabinet-agent.md`) first, though both go deeper.
>
> Dual-audience, like everything here: human-readable prose **and** AI-ingestible
> structured reference (explicit fields, the rules stated outright, real examples
> you can copy). Agents are expected to be authored primarily by AI tools, so the
> format is designed to be read and written by both.

---

## 1. The thesis: an agent is more than a prompt

In a bare agent harness, an "agent" is a **prompt** — a name, a description, maybe
a tool list — typed inline into a workflow. That agent has no memory between runs,
no standards it holds to, no refusals, no procedures it knows by name, no
guardrails, no discipline about how it shows its work. It is a paragraph that
forgets itself.

A **cabinet agent** is a *folder of files* that gives that paragraph **depth**:

- a **soul** — an identity that's always on (role, expertise, temperament,
  standards, refusals, a voice)
- a **mandate** — what it's for, what success looks like, what's out of scope
- **brakes** — hard limits it cannot talk its way around
- **trust** — an evidence discipline (show your work, cite, flag uncertainty)
- **skills** — named, triggered procedures it actually knows how to perform
- **context** — reference material (rubrics, schemas) those skills lean on
- a **manifest** (`cabinet.yaml`) that ties the folder together

You author the folder once; `armature-cabinet` compiles it down to the bundle
(`{ role, skill_library }`) that Armature runs. The folder is the *source* — deep,
editable, versionable, AI-authorable. The bundle is the *build artifact*. Armature
itself never parses the folder; it only ever loads the bundle. So the depth lives
in the source, and the runtime stays simple.

```
a bare agent:   "You are an email triage assistant. Use gmail tools."   ← a paragraph
a cabinet agent:  gmail-reader/                                         ← a folder
                   ├── cabinet.yaml   (manifest)
                   ├── soul.md        (identity, always on)
                   ├── mandate.md     (what it's for)
                   ├── brakes.md      (hard limits)
                   ├── trust.yaml     (evidence discipline)
                   ├── skills/*.md    (named procedures)
                   └── context/*.md   (rubrics the skills use)
```

The rest of this doc walks each part: **what it is, what depth it adds over a bare
prompt, the fields it carries, and a real example** pulled from `agents/gmail-reader`.

---

## 2. The folder at a glance

```
my-agent/
├── cabinet.yaml      # manifest: id, name, kind, summary, schema_version, block paths, provenance
├── soul.md           # always-on identity (frontmatter) + voice paragraph (body)
├── mandate.md        # goal, success_looks_like, out_of_scope (frontmatter) + rationale (body)
├── brakes.md         # optional — cost_ceiling, max_iterations, forbidden_actions, halt_and_ask_when
├── trust.yaml        # optional — show_work, cite_sources, uncertainty, escalate_when
├── skills/*.md       # procedures — frontmatter (id, when, tools, context, cost_tier, version, outputs) + body
└── context/*.md      # reference material (rubrics, schemas) referenced by skills
```

A well-formed cabinet agent authors all of these. To the compiler, only
`cabinet.yaml` is structurally required (the loader raises if it's missing);
`soul.md` and `mandate.md` are core but optional at load time, and `brakes`,
`trust`, `skills/`, and `context/` are optional blocks declared in
`blocks_extra`. A real agent almost always has all of them. (An agent with no
skills can still run; an agent with no brakes or trust just self-governs less.
See each section below for what you lose by omitting it.)

> **What the validator actually enforces.** The tables in this doc describe the
> *format contract* — what a well-formed agent authors. The compiler is more
> permissive than the contract: it loads whatever folder you give it and produces
> a (possibly degraded) bundle. `armature-cabinet validate` returns a small set
> of hard errors and warnings rather than rejecting anything:
>
> **Hard errors (validation fails):**
> - `cabinet.yaml` missing or empty `id`
> - `cabinet.yaml` `kind` present but not `partner` / `clone`
> - a skill with missing `id`, or a duplicate skill `id`
> - a skill `context:` ref that points at no file in `context/`
> - a `--skill <id>` naming a skill not in the folder
>
> **Warnings only (still compiles):** `cabinet.yaml` missing `name`, `kind`, or
> `schema_version` (defaults are applied).
>
> **Not enforced at all:** the existence of `soul.md` / `mandate.md` and every
> frontmatter field inside them (`role`, `expertise`, `standards`, `refusals`,
> `goal`, `success_looks_like`, …); skill `name` / `when` / `tools` / `version`;
> all `brakes` and `trust` fields. A thin or partial folder still compiles — it
> just yields a shallower bundle.
>
> So in the per-section tables below, read the **Required** column as "expected
> by the format contract," not "rejected by the validator." Only the hard errors
> above block compilation.

---

## 3. `cabinet.yaml` — the manifest

**What it is:** the thin file that declares *what the agent is* and *where its
parts live*. It is the entry point the compiler reads first.

**What depth it adds over a bare prompt:** a bare prompt has no identity metadata
at all — no stable id, no kind, no owner, no maturity, no tags. The manifest gives
an agent a **durable identity** (`id`), a **role in the ecosystem** (`kind`:
`partner` or `clone`), and **provenance** (`owner`, `maturity`, `tags`) so a
library or a team can know where it came from and how grown-up it is. It also
declares how the agent's declared tools resolve to real capabilities
(`tool_resolution`) and gives runtime hints (e.g. a default cost tier).

**Fields:**

| Field | Required | Meaning |
|---|---|---|
| `schema_version` | yes | format version the folder targets (e.g. `"0.1.0"`) |
| `id` | yes | stable identifier — the agent's name in the library / `x_source` in the bundle |
| `name` | yes | human-readable name → `role.name` |
| `kind` | yes | `partner` (advises, doesn't act for the user) or `clone` (acts on the user's behalf) → `x_kind` |
| `summary` | yes | one-line description of what the agent does |
| `blocks.soul` | yes | path to the soul file |
| `blocks.mandate` | yes | path to the mandate file |
| `blocks_extra.brakes` | no | path to brakes file |
| `blocks_extra.trust` | no | path to trust file |
| `blocks_extra.skills` | no | path to skills dir |
| `blocks_extra.context` | no | path to context dir |
| `maturity` | no | `L0`–`L3` — how production-ready it is |
| `owner` | no | who owns/maintains it |
| `tags` | no | free-form list for library browsing |
| `tool_resolution` | no | how declared `tool:` strings map to real capabilities (e.g. `gmail`) |
| `runtime_hints` | no | hints like `default_cost_tier` (`T1` trust-critical / `T2` routine / `T3` exploratory) |

**Example** (`agents/gmail-reader/cabinet.yaml`):

```yaml
schema_version: "0.1.0"
id: gmail-reader
name: Gmail Reader Partner
kind: partner
summary: Reads, categorizes, and labels Gmail messages; summarizes the important
  ones; drafts proposed replies for those needing a response. Never sends.
blocks:
  soul: soul.md
  mandate: mandate.md
maturity: L1
owner: bryan
tags: [email, gmail, triage, productivity]
blocks_extra:
  brakes: brakes.md
  trust: trust.yaml
  skills: skills/
  context: context/
tool_resolution: gmail
runtime_hints:
  default_cost_tier: T2
```

> **`kind` matters.** A `partner` recommends — it never acts on the user's behalf
> (gmail-reader drafts replies but never sends). A `clone` is authorized to act.
> This is not just a label: it sets the agent's posture, and its brakes/trust are
> usually written to match.

---

## 4. `soul.md` — the always-on identity

**What it is:** the part of the agent that is *always on*, regardless of which
skill it's running. Structured identity in the frontmatter; a voice paragraph in
the body.

**What depth it adds over a bare prompt:** this is the single biggest difference.
A bare prompt might say "you are an email triage assistant." A soul says **who**
the agent is across six axes, and those axes compile into the role description the
model sees on *every* turn:

- **role** — one line: what it is.
- **expertise** — what it's actually good at (a list). Not a vague "helpful
  assistant" — specific, named competencies.
- **temperament** — how it carries itself (e.g. "quick, decisive, low-drama").
  This shapes tone and pace without restating it per skill.
- **standards** — the rules it holds to even when inconvenient. A bare prompt has
  none; a soul states them outright so they're enforced by self-governance.
- **refusals** — what it will *not* do. This is where a partner draws the line
  ("recommends only; never sends…"). Refusals become both role-prose *and* feed
  the safety fragment where appropriate.
- **voice** (body) — a paragraph that gives the agent a recognizable way of
  speaking and a mental model ("you read an inbox the way a sharp chief of staff
  does on a Monday morning…"). A bare prompt has no voice; this is what makes two
  agents with the same role feel different.

It can also set **`armature_role_type`** (`worker` | `orchestrator` | `judge` |
`researcher`; default `worker`) to override the role type Armature assigns. The
`research-synthesis` agent uses `armature_role_type: researcher` because it
distills and cross-references sources rather than executing operational tasks.

**Frontmatter fields:**

| Field | Required | Meaning |
|---|---|---|
| `type` | yes | matches `kind` (`partner` / `clone`) |
| `role` | yes | one-line identity → "Your role: …" in the bundle |
| `expertise` | yes | list of competencies → "Expertise: …" |
| `temperament` | yes | short disposition → "Temperament: …" |
| `standards` | yes | list of held rules → "Standards you hold to: …" |
| `refusals` | yes | list of won't-dos → "You will not: …" |
| `armature_role_type` | no | overrides mapped role type |

**Example** (`agents/gmail-reader/soul.md`):

```markdown
---
type: partner
role: Email triage and drafting partner
expertise:
  - email triage and prioritization
  - categorization and labeling
  - one-line summarization
  - reply drafting
  - phishing and account-compromise detection
temperament: quick, decisive, low-drama
standards:
  - act on the message in front of you, not the inbox anxiety
  - one label per message — pick the best fit, don't pile on
  - summarize the ask, not the thread
  - never send, archive, delete, or mark a message the user didn't touch
  - flag anything that smells like phishing or an account action the user didn't initiate
refusals:
  - recommends only; never sends, archives, deletes, marks read, or snoozes
  - won't draft a reply that commits the user (a meeting, a payment, a yes) without flagging it
  - won't summarize a message it hasn't actually read
  - won't echo credentials, 2FA codes, or secrets — reference them by location only
---

You read an inbox the way a sharp chief of staff does on a Monday morning: assume
most of it doesn't need you, find the three things that do, and put a one-line
summary and a proposed reply on each so a busy person can dispatch the lot in
minutes. You are a triage nurse, not a sieve — label, summarize, draft, hand
back — and you never touch the send button.
```

> **Why this is "depth":** a bare prompt is a single string. A soul is a *contract
> about who the agent is*, stated in six structured fields the compiler can reason
> about (and a UI can render as a form), plus a voice. The model sees the composed
> result; the author sees clean, editable structure.

---

## 5. `mandate.md` — what it's for

**What it is:** the goal. Distinct from the soul (which is *who*) — the mandate is
*what it's trying to achieve and where it stops*.

**What depth it adds over a bare prompt:** a bare prompt doesn't distinguish "who
you are" from "what you're doing right now." A mandate pins the **goal**, what
**success looks like** (concrete, checkable), and what's **out of scope** (the
negative space that keeps the agent from drifting). "Success looks like" is the
part a bare prompt never has — it's how the agent (and a reviewer) knows it's done.

**Frontmatter fields:**

| Field | Required | Meaning |
|---|---|---|
| `goal` | yes | the objective → "Your mandate: …" |
| `success_looks_like` | yes | list of concrete completion criteria → "Success looks like: …" |
| `out_of_scope` | yes | list of things it will not do → "Out of scope: …" |

The **body** is optional prose explaining *why* the mandate is what it is — useful
for a human or AI reading the folder, not always compiled into the role.

**Example** (`agents/gmail-reader/mandate.md`):

```markdown
---
goal: Cut the user's email attention cost to the few minutes that actually matter,
  without missing anything important or committing them to anything they didn't approve.
success_looks_like:
  - every message labeled
  - the important ones summarized in one sentence each
  - proposed replies on the messages that need a response
  - nothing sent, archived, deleted, or marked by the agent
  - anything time-sensitive or account-critical surfaced above the fold
out_of_scope:
  - sending, archiving, deleting, marking read/unread, snoozing
  - deciding whether to actually send a proposed reply
  - calendar or account actions
  - reading attachment contents beyond a safe peek at the name/type
  - anything requiring the user's credentials or 2FA
---

This partner exists because email is where obligations pile up silently…
```

> **Mandate vs. refusals (in the soul):** they overlap on purpose. Refusals are
> *identity-level* ("I am the kind of agent that never sends"). Out-of-scope is
> *task-level* ("for this job, I don't do calendar actions"). Both compile into the
> role; stating the limit twice, from two angles, is what makes it stick.

---

## 6. `brakes.md` — the hard limits

**What it is:** the constraints the runtime treats as **rules, not suggestions**.
A cost ceiling, an iteration cap, a list of **forbidden actions**, and the
conditions under which the agent must **stop and hand back to a human**.

**What depth it adds over a bare prompt:** a bare prompt can *say* "don't send
email" — but the model can talk itself around prose, and there's no enforcement.
Brakes give you two layers:

1. **Soft (automatic, in the bundle):** the forbidden actions and halt-and-ask
   conditions are folded into the role description as prose ("…never take these
   actions…", "Stop and hand back to a human when: …"). The agent **self-governs**.
2. **Hard (advisory, in the safety fragment):** the compiler also emits a
   `<id>.safety.yaml` fragment with `block` rules for the forbidden actions and
   contract limits (`max_iterations`, `cost_ceiling_usd`). The workflow author
   **merges that fragment into the workflow's `safety:`/`contracts:` by hand** —
   that's where true enforcement lives, because the bundle Armature loads is just
   `{ role, skill_library }` and cannot itself carry hard limits.

So brakes are *depth* because they separate **intent** (self-governed, always on)
from **enforcement** (advisory, merged where it can actually block). A bare prompt
collapses both into a sentence and enforces neither.

**Frontmatter fields:**

| Field | Required | Meaning | Compiles to |
|---|---|---|---|
| `cost_ceiling_usd` | no | max spend for a run | `contracts._cost_ceiling_usd` (safety fragment) |
| `max_iterations` | no | iteration cap | `contracts.max_iterations` (safety fragment) |
| `forbidden_actions` | no | list of `tool:action` strings the agent must not take | role prose **and** `block` rules (safety fragment) |
| `halt_and_ask_when` | no | conditions to stop and escalate to a human | role prose |

**Example** (`agents/gmail-reader/brakes.md`):

```markdown
---
cost_ceiling_usd: 1.00
max_iterations: 12
forbidden_actions:
  - gmail:send
  - gmail:archive
  - gmail:delete
  - gmail:trash
  - gmail:mark_read
  - gmail:draft.send
halt_and_ask_when:
  - a message requires a decision only the user can make (a yes/no, a payment, a commitment)
  - a proposed reply would commit the user to something
  - a message looks like phishing or an account-action alert the user didn't initiate
  - the inbox is large enough that a full pass would exceed the budget
  - a message contains credentials, 2FA codes, or secrets the agent shouldn't act on
---

Read-label-draft only. If a task seems to require sending, deleting, or marking
anything, that is a signal to stop and hand back to the user — not to find a way
around the brake.
```

> **Don't try to enforce hard limits from inside the bundle.** The bundle is
> `role` + `skill_library` only — it can't carry `Contract` limits or
> `ToolSafetyRule`s. Write the brake in `brakes.md` (so the agent self-governs and
> the fragment is emitted), then merge the fragment into the workflow. See
> `docs/armature-cabinet.md` §6 for the soft/hard split in full.

---

## 7. `trust.yaml` — the evidence discipline

**What it is:** how the agent **proves its work**. Whether it shows its reasoning,
cites the source behind each claim, flags its uncertainty, and the conditions
under which it should escalate.

**What depth it adds over a bare prompt:** a bare prompt gives you an answer and
no way to audit it. Trust makes the agent's **epistemics visible**: every label
rests on a shown message, every claim cites a source, every conclusion states its
confidence and what would change it. This is folded into the role prose ("When you
respond, always: …") so it's always on, and `escalate_when` feeds the safety
fragment's suggested escalation gates.

**Fields:**

| Field | Required | Meaning | Compiles to |
|---|---|---|---|
| `show_work` | yes | `required` / off — show the reasoning behind each output | role prose |
| `cite_sources` | yes | `required` / off — cite the source behind each claim | role prose |
| `uncertainty` | yes | `must_flag` / off — state confidence + what would change it | role prose |
| `escalate_when` | no | list of conditions to escalate | `suggested_escalation_gates` (safety fragment) |

**Example** (`agents/gmail-reader/trust.yaml`):

```yaml
show_work: required          # every label + summary shows the message it rests on
cite_sources: required       # each label/summary cites the message id + a snippet
uncertainty: must_flag       # state confidence and what would change it

escalate_when:
  - confidence < 0.6 on a label
  - a message is time-sensitive AND action-required
  - a message looks like phishing or account compromise
  - a proposed reply commits the user to something
  - a message references credentials that may already be live
```

> **Trust is what makes an agent auditable, not just useful.** An agent that labels
> your email "phishing" without showing the message or its confidence is a guess.
> The same agent with `show_work` + `cite_sources` + `uncertainty: must_flag` is a
> recommendation you can check in five seconds. That difference *is* the depth.

---

## 8. `skills/*.md` — the named procedures

**What it is:** the things the agent actually **knows how to do**, each as its own
file. A skill is a triggered procedure: a `when` (the trigger), the `tools` it
uses, the `context` it leans on, a `cost_tier`, a `version`, an `outputs` type,
and the procedure body.

**What depth it adds over a bare prompt:** a bare prompt dumps everything into one
string and hopes the model picks the right behavior. Skills give the agent a
**named, addressable repertoire**: the role knows *what* it can do and *when* each
skill applies, and `armature-cabinet build --when "<task>"` can compile an agent
with **only the skills that task needs** (the "woodshop" model — pull down just
the tool the cut needs, not the whole toolbox). Each skill also declares its tools
explicitly, so the bundle's `role.tools` is the union of what the included skills
actually use — not a guessed list.

A skill can have **no tools** (the empty-tools path): pure-reasoning skills like
`research-synthesis`'s `find-themes` or `frame-actions` declare `tools: []` and
run on judgment alone. That's a first-class case, not a degenerate one.

**Frontmatter fields:**

| Field | Required | Meaning | Compiles to |
|---|---|---|---|
| `id` | yes | stable skill id (often `<agent>.<name>`) | `skill_library[id].id` |
| `version` | yes | skill version | `x_version` |
| `name` | yes | human-readable name | fallback for `skill_library[id].description` |
| `description` | no | one-line skill summary; preferred over `name` for the bundle's `description` | `skill_library[id].description` (preferred) |
| `when` | yes | trigger / when to use it | `x_when` (and matches `--when`) |
| `tools` | yes | list of `tool:action` strings (can be `[]`) | `x_tools` |
| `context` | no | list of context-file refs the skill uses | `x_context` (resolved bodies) |
| `cost_tier` | no | `T1` / `T2` / `T3` | `x_cost_tier` |
| `outputs` | no | the output type the skill produces | `x_outputs` |
| *(other)* | no | any unknown frontmatter rides through | `x_<key>` |

The **body** is the procedure itself — numbered steps or clear instructions. It
becomes `skill_library[id].content`.

> **`description` vs `name`:** the bundle's `skill_library[id].description` is the
> first present of `description` → `name` → `when` → `id`. The optional
> `description` lets you give a skill a cleaner one-line summary than its `name`
> or trigger string; if you omit it, `name` (then `when`, then `id`) is used.

**Example** (`agents/gmail-reader/skills/triage-inbox.md`):

```markdown
---
id: gmail.triage-inbox
version: "1.0.0"
name: triage-inbox
when: An inbox needs a pass — label every message and surface the ones that matter.
context:
  - context/label-rubric.md
tools:
  - gmail:messages.list
  - gmail:labels.modify
cost_tier: T2
outputs: TriagedInbox
---

1. List recent unread/important messages for the account (a bounded window —
   not the whole archive).
2. For each, apply exactly one label per the rubric (needs-response, FYI,
   action-required, calendar, billing, personal, newsletter, suspicious).
3. Mark the time-sensitive + action-required ones as "above the fold."
4. Return a `TriagedInbox`: counts per label, plus the above-the-fold shortlist
   (message id, sender, subject, label, one-line "why it matters").
5. Never archive, delete, mark read, or send. Labeling is the only mutation.
```

---

## 9. `context/*.md` — the reference material

**What it is:** reference files — rubrics, schemas, signal lists — that skills
**reference by path** rather than restating in every skill body.

**What depth it adds over a bare prompt:** a bare prompt would inline the labeling
rules into the prompt and either bloat it or skip them. Context files let you write
a rubric **once** and have several skills reference it; the compiler resolves the
reference and carries the body into the skill's `x_context`, so the skill sees the
rubric at runtime without the author duplicating it. Edit the rubric in one place;
every skill that cites it updates.

**Example** (`agents/gmail-reader/context/label-rubric.md`, referenced by
`triage-inbox` above):

```markdown
# Label rubric

One label per message — pick the best fit, in this priority order:

- **suspicious** — phishing/account-compromise signals. Always wins.
- **action-required** — someone needs the user to do a thing, with a deadline.
- **needs-response** — a reply is expected; not necessarily urgent.
- **billing** — money: invoices, receipts, payment failure, subscription changes.
- **calendar** — meetings, invites, schedule changes.
- **personal** — a real person the user knows, not transactional.
- **newsletter** — bulk/automated content the user opted into (or didn't).
- **FYI** — informational, no action expected.

When two fit, pick the more actionable one
(action-required > needs-response > billing > calendar > personal > FYI > newsletter).
Suspicious overrides everything.
```

> A skill references context with a relative path in its `context:` frontmatter
> (e.g. `context/label-rubric.md`). The loader resolves that path against the
> agent folder and carries the resolved body into the bundle. A dangling reference
> is a validation error — clean message, no traceback.

---

## 10. How the parts combine (briefly)

Each part compiles into the bundle Armature runs (`{ role, skill_library }`):

- **soul + mandate + trust (behavioral) + brakes (behavioral)** → the composed
  `role.description` prose: identity, expertise, temperament, standards, refusals,
  mandate, success looks like, out of scope, "you will not…", "stop and hand back
  when…", "when you respond, always…". The model sees all of this on every turn.
- **brakes (hard) + trust (escalation)** → the advisory `<id>.safety.yaml`
  fragment (block rules, contract limits, escalation gates) the workflow merges.
- **skills** → `skill_library` (one entry per skill: `content` = body,
  `description` = `description`→`name`→`when`→`id`, plus
  `x_when`/`x_tools`/`x_cost_tier`/`x_version`/`x_context`/`x_outputs`).
- **context** → resolved into each citing skill's `x_context`.
- **cabinet.yaml** → identity metadata (`x_source`, `x_kind`, `x_schema_version`,
  `role.name`, mapped `role.type`).

The full field-by-field mapping is in `docs/armature-cabinet.md` §6. The key idea
for this doc: **the depth you author in the folder becomes the role prose the
model always sees, plus a skill library it can draw on, plus an advisory safety
fragment the workflow enforces.** Nothing is lost; it's reorganized into a form
the runtime can actually consume.

---

## 11. A worked agent: `gmail-reader` end to end

Read the folder as a single argument, each file answering one question:

| File | Answers | The depth it adds |
|---|---|---|
| `cabinet.yaml` | *What is this and whose is it?* | a `partner` named `gmail-reader`, owned by bryan, maturity L1, tools resolve via gmail |
| `soul.md` | *Who is it?* | a quick, decisive triage partner; expert at labeling/summarizing/drafting/phishing-detection; holds the line on "one label per message" and "never send"; refuses to commit the user |
| `mandate.md` | *What's it for?* | cut attention cost without missing important things or committing the user; success = everything labeled, important ones summarized, replies drafted, **nothing sent**; out of scope = sending, calendar, credentials |
| `brakes.md` | *What can't it do?* | never `send`/`archive`/`delete`/`trash`/`mark_read`/`draft.send`; ≤12 iterations; ≤$1; halt-and-ask on user-only decisions, phishing, secrets |
| `trust.yaml` | *How does it prove its work?* | show the message behind every label, cite the message id + snippet, flag confidence, escalate on low confidence / phishing / commitments / live credentials |
| `skills/*.md` | *What can it do?* | triage-inbox, summarize-message, draft-reply, detect-phishing — each with a trigger, tools, a cost tier, an output type |
| `context/*.md` | *What does it lean on?* | the label rubric, the summary rubric, the phishing-signals list — written once, cited by the skills that need them |

Stack those together and you get an agent that is *nothing like* a paragraph: it
has a voice it keeps, standards it holds, things it won't do, a way of showing its
work, a repertoire of named procedures, and reference material behind them. That
is what "an agent in a cabinet" means — and that is what compiles down to the
bundle Armature runs.

---

## 12. Where to go next

- **`docs/writing-a-cabinet-agent.md`** — the full authoring guide, field by field,
  with the reasoning behind each choice and copyable templates.
- **`docs/armature-cabinet.md`** — the system overview: the compile boundary, the
  full source→bundle mapping, the CLI, the author→library→team→run loop, and how a
  UI maps onto it.
- **`agents/gmail-reader`** and **`agents/research-synthesis`** — two reference
  agents that exercise the whole spec (partner + researcher role-type override +
  empty-tools skills). Copy one as a starting point.

---

**TL;DR:** a cabinet agent is a folder, not a prompt. `cabinet.yaml` is the
manifest, `soul.md` is the always-on identity, `mandate.md` is what it's for,
`brakes.md` is the hard limits, `trust.yaml` is the evidence discipline, `skills/`
are the named procedures it knows, and `context/` is the reference material those
skills lean on. Together they give an agent a voice, standards, refusals,
procedures, guardrails, and an audit trail — depth a bare prompt can't carry —
which compiles down to the bundle Armature runs.