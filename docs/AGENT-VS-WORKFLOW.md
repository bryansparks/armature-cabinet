# Agent vs. Workflow — where each marketing activity lives

> A design doc answering two questions that kept coming up:
>
> 1. **Where does an agent definition end and an Armature workflow begin?** How
>    specific should I make agents?
> 2. **How do I organize Armature workflows, agents, and subagents** for real
>    ElfTech marketing — a product launch, a recurring weekly campaign that
>    adjusts mid-week, and lead-conversion responders?
>
> It assumes you've read `docs/INTO-ARMATURE-AGENTS.md` (what a cabinet agent
> *is*) and `docs/armature-cabinet.md` (the system). The marketing examples are
> grounded in the agents that already exist in `agents/` (the
> `marketing-ideator` / `marketing-debater` / `marketing-judge` deliberation team
> and the `social-adapter` / `blog-writer` / `short-video-ideator` channel
> adapters).

---

## 1. The one-sentence answer

**Armature reasons; the scheduler clocks; the state store remembers.** Agents
hold identity + capability + guardrails; workflows wire agents into a one-shot
DAG for a specific job; a scheduler (cron / n8n) fires DAGs on a cadence or in
reaction to an event; a state store carries what one run learned into the next.

Most confusion about "agent vs. workflow" comes from trying to make the workflow
do all four jobs. It can't — an Armature workflow is a DAG, and a DAG can't
self-loop or hold state between runs. Once you separate the four, everything
below falls into place, and the "n8n is too static" problem dissolves: n8n is
fine for the clock, it's bad for the brain, so use it for the clock.

---

## 2. The four layers

| Layer | Owns | Examples | Reusable? |
|---|---|---|---|
| **Agent** (cabinet folder) | identity, capability, self-guardrails | `marketing-ideator`, `social-adapter`, `campaign-judge` | yes — a role you'd reuse |
| **Workflow** (Armature YAML) | coordination: which agents, what order, the DAG, model tiers, team safety | `steward-launch.yml`, `weekly-generate.yml`, `lead-respond.yml` | no — specific to a job |
| **Scheduler** (cron / n8n) | the clock: cadence and event triggers | "Monday 8am → run weekly-generate", "inbound lead webhook → run lead-respond" | the triggers are reusable; the clock is infra |
| **State store** (sqlite / json / db) | memory between runs | `current_message`, `last_verdict`, `lead_state`, cumulative metrics | the store is infra; the schema is per-product |

The dividing lines:

- **Agent vs. workflow** — does it travel with the agent no matter which team
  runs it, or only make sense in one team's wiring? Identity/capability/guardrails
  → agent. Order/DAG/model-tiers/per-stage task → workflow.
- **Workflow vs. scheduler** — is it a single run-to-completion job, or is it a
  *recurrence* / a *reaction*? One DAG execution → workflow. "Every Monday" or
  "when a lead arrives" → scheduler firing workflows.
- **Everything vs. state** — does it need to survive past this run? Then it's not
  in the agent and not in the workflow; it's in the state store, read at the start
  of a run and written at the end.

> **The n8n contrast, resolved.** n8n workflows are static pipelines — they
> don't reason and they don't adjust. But the thing you actually want n8n for
> (firing on a schedule, reacting to a webhook) is exactly the *scheduler* layer,
> which Armature was never meant to be. So: **n8n/cron for the clock, Armature for
> the brain, a state store for the memory.** You're not replacing n8n; you're
> stopping it from pretending to be the brain.

---

## 3. Reusable agents vs. per-product agents (the "product is data" rule)

This answers "how specific should I make agents?" The rule:

> **The craft is the agent; the product is data.** A capability you'd use across
> every ElfTech product (ideate, critique, judge a message, adapt to a channel,
> read analytics, qualify a lead) is a reusable library agent. A product's
> specific voice, ICP, and value proposition are *context* — fed in, not compiled
> in.

Concretely for marketing:

- **Reusable library agents** (write once, used by Steward, Tessera, Anvil, every
  launch): `marketing-ideator`, `marketing-debater`, `marketing-judge`,
  `social-adapter`, `blog-writer`, `short-video-ideator` *(all already exist)*,
  plus the ones still to build — `message-architect`, `email-composer`,
  `text-composer`, `analytics-reader`, `lead-qualifier`.
- **Per-product thin agents or context** (one per product): Steward's brand voice
  and ICP. Brand voice is *identity* — the thing a `soul.md` is for — so the clean
  move is a thin per-product agent like `steward-brand` whose soul *is* the voice,
  or a `context/steward-voice.md` + `context/steward-icp.md` carried into runs.
  Either works; pick the thin-agent form if the voice needs to *refuse* things
  (e.g. "won't overclaim features"), the context form if it's pure reference.

Don't make a `steward-launch-orchestrator` unless Steward's launch flow is
*structurally* different from every other product's. It won't be — so use one
reusable `launch-orchestrator` and bind Steward's specifics through the
workflow's `agent_library` + the per-stage task + context. Same orchestrator,
different product, next month.

**Right-sizing test:** if an "agent" would only ever serve one run of one
workflow, it's not an agent — it's a stage's task prompt. If it's a god-agent
doing ideation *and* adaptation *and* judging, split it. The deliberation team
is the model here: three thin specialists (ideator/debater/judge) instead of one
"marketing agent."

---

## 4. Orchestrators and subagents — the fan-out pattern

Armature lets an agent spawn subagents. The rule from
`INTO-ARMATURE-AGENTS.md`: **a subagent is a first-class library cabinet agent;
orchestrators *reference* subagents, they don't own or inline-define them.**

The canonical good use of subagents is **fan-out of independent parallel work** —
exactly what channel adaptation is. One settled message → N platform assets. The
orchestrator spawns one adapter subagent per channel and combines their outputs:

```
launch-orchestrator  (orchestrator role type)
  ├── spawn social-adapter      → IG/Snapchat/X assets
  ├── spawn blog-writer         → blog post
  ├── spawn short-video-ideator → Shorts/TikTok scripts
  ├── spawn email-composer      → email sequence          (to build)
  └── spawn text-composer       → SMS copy                  (to build)
```

Each subagent is the *same* library agent you'd put in a top-level stage. The
only difference between a "subagent" and a "stage agent" is *who calls it*: the
workflow calls a stage agent; an orchestrator calls a subagent. The agent folder
is identical. So:

- **Delegation policy** (when to fan out, how many, how to combine, caps) lives
  in the orchestrator's `skills/` + `brakes.md`.
- **Which subagents are available** for a given run lives in the workflow's
  `agent_library` — that's the binding layer. The orchestrator says "spawn a
  channel adapter"; the workflow decides which adapter ids are on the bench.

> **Guardrails must not vanish when an agent is spawned.** A subagent's
  `brakes`/`trust` still self-govern via its role prose, and its safety fragment
  still must be emitted and merged into the workflow. A spawned `social-adapter`
  that "never posts" must keep that brake even though it was invoked by an
  orchestrator, not a top-level stage. Worth verifying in the Armature subagent
  path that the fragment currently bubbles up and isn't dropped.

---

## 5. Two trigger shapes: cadence vs. event

All marketing runs are fired by the scheduler in one of two shapes — and the
agent architecture is identical for both; only the trigger differs:

- **Cadence** — the clock fires: "Monday 8am, generate this week's campaign";
  "Wednesday, run the pulse check." Cron / n8n schedule → Armature DAG.
- **Event** — an inbound signal fires: "a lead filled the trial form", "an
  inbound email/text arrived." Webhook → Armature DAG.

This is why lead-responders (§8) and weekly campaigns (§7) use the *same* agent
library — they're just triggered differently. Don't build separate agent
families for "campaign" vs "respond"; build one library, trigger it two ways.

---

## 6. Guardrails scale with autonomy

Every marketing agent above is currently `kind: partner` — *recommends, never
posts/sends*. That's the right default for authoring and review. But two of the
scenarios below involve actually sending (posting to social, emailing/texting
leads). When an agent acts unattended, its guardrails must escalate:

- **Partner** (recommend) — for ideation, judging, analytics reading, retro.
  Low risk; the human publishes.
- **Clone** (act on behalf) — for actual posting/sending when you trust it
  unattended. Hard `brakes.forbidden_actions` on *what* it may send, tight
  `cost_ceiling`, and `trust` requiring it cite the lead/source and flag
  confidence. This is where the cabinet depth pays for itself — a bare prompt
  "send the email" has none of this.

Recommendation: start everything as `partner` with a human in the publish loop.
Promote a specific agent to `clone` only for a specific, bounded action (e.g.
"send the approved weekly email to the approved list") and only after you've
watched its outputs. The `kind` flip is a deliberate, per-action trust decision —
not a global setting.

---

## 7. Worked scenario A — Steward product launch (one-time, deep)

A launch is a *pipeline with a retro*, not a loop. One DAG, run once. Stages:

```
steward-launch.yml  (Armature workflow, run once)
  stage: icp            → icp-analyst          (refine Steward's ICP)            [build]
  stage: message        → launch-orchestrator
                          ├── marketing-ideator    (3+ candidate messages)
                          ├── marketing-debater    (critique each)
                          └── marketing-judge      (settle on THE message)        [exists]
  stage: assets         → launch-orchestrator  (fan-out subagents)
                          ├── social-adapter        → IG/Snapchat/X            [exists]
                          ├── blog-writer           → launch blog              [exists]
                          ├── short-video-ideator   → Shorts/TikTok scripts     [exists]
                          ├── email-composer        → launch email sequence     [build]
                          └── text-composer         → SMS copy                  [build]
  stage: publish        → (human, or a clone agent with hard brakes)            [decision]
  stage: metrics        → analytics-reader      (collect launch metrics)        [build]
  stage: retro          → campaign-judge        (what worked, surprises,        [exists-ish]
                          lessons for next effort)                                (judge)
```

**Where things sit:**
- *ICP, brand voice, value prop* — Steward context files / thin `steward-brand`
  agent. Data, not craft.
- *The deliberation (ideator→debater→judge)* — reusable library agents, already
  built. This is the existing marketing team; the launch just wires it.
- *Channel fan-out* — the orchestrator spawns the existing adapters + the two
  composers still to build.
- *Publish* — a deliberate trust gate (§6). Keep it human at first.
- *Metrics + retro* — `analytics-reader` (to build) pulls the numbers;
  `campaign-judge` (exists) reads them and writes the launch retrospective.
- *The DAG itself* — the only workflow-specific artifact. Reusable agents +
  Steward context in; launch assets + retro out.

`[exists]` = already in `agents/`; `[build]` = still to author; `[decision]` =
a trust/autonomy call.

---

## 8. Worked scenario B — recurring weekly campaign (the loop)

This is the case that breaks naive "put it all in one workflow" thinking, and
it's the heart of your question. The weekly loop:

> Monday 8am → generate a cohesive message → emails, posts, texts → Wednesday
> pulse check → if it's working, continue to next Monday; if not, tweak → next
> Monday 8am, evolve slightly, run again. Over and over.

**An Armature workflow is a DAG. A DAG cannot loop, and it cannot sleep for a
week.** So the loop is *not* one workflow. It is the scheduler + state + two
short DAGs:

```
                       state store
                  ┌──────────────────────┐
                  │ current_message       │
                  │ last_verdict          │
                  │ cumulative_metrics     │
                  │ this_week_assets       │
                  └──────────────────────┘
                       ▲              ▲
                       │ read/write   │ read/write
                       │              │
  ┌─────────┐    ┌─────┴────┐    ┌────┴─────────┐    ┌──────────┐
  │ cron    │──▶ │ weekly-  │──▶ │  midweek-     │──▶ │ cron     │──▶ (next Mon)
  │ Mon 8am │    │ generate │    │  pulse-check  │    │ Mon 8am │
  └─────────┘    └──────────┘    └───────────────┘    └──────────┘
```

**DAG 1 — `weekly-generate.yml`** (fired Mon 8am by cron):
```
  read state (last_verdict, current_message, ICP)
  stage: evolve    → message-architect   (last message + verdict → this week's variant)  [build]
  stage: settle    → marketing-judge    (confirm the variant is on-brand / not stale)    [exists]
  stage: produce   → weekly-orchestrator (fan-out)
                     ├── social-adapter      → week's posts                         [exists]
                     ├── email-composer      → week's emails                        [build]
                     └── text-composer       → week's SMS                           [build]
  write state (current_message, this_week_assets)
```

**DAG 2 — `midweek-pulse-check.yml`** (fired Wed by cron):
```
  read state (this_week_assets, cumulative_metrics)
  stage: read    → analytics-reader   (pull Wed metrics, compare to baseline)          [build]
  stage: judge   → campaign-judge     (verdict: on-track / tweak / kill)               [exists]
  stage: adjust  → (if tweak) a small reactive run: pause/swap underperforming assets  [decision]
  write state (last_verdict, cumulative_metrics)
```

**Where things sit:**
- *The message evolving "slightly each week"* — a **skill** of
  `message-architect` ("evolve-message: given last message + last verdict,
  produce a small variant"). The *cadence* of evolving is the scheduler; the
  *how* is the agent skill; the *what-it-was* is state.
- *The continue/modify decision* — `campaign-judge`'s verdict, written to state,
  read by next Monday's generate. The loop is closed by **scheduler + state**,
  not by the DAG. This is the key sentence of the whole doc.
- *Mid-week adjustments* — keep them bounded and mostly roll into next Monday's
  evolution; only do a small reactive run for things that genuinely can't wait
  (pause a flop). Don't try to re-launch mid-week.
- *The "over and over every week" forever* — that's the cron entry, not anything
  in Armature. To stop it, you stop the cron, not an agent.

This is the answer to "n8n workflows are static and don't adjust in real time":
the *adjustment* is `campaign-judge` reasoning inside `midweek-pulse-check.yml`
— a real agent reading real metrics and writing a verdict. n8n could never do
that part; it just fires the DAG that does.

---

## 9. Worked — lead-conversion responders (event-triggered)

Inbound leads (trial signup, inbound email, inbound text) are **events**, not a
cadence. A webhook fires an Armature DAG. One library, triggered differently:

```
lead-respond.yml  (Armature workflow, fired per inbound lead)
  read state (lead_state: history with this lead, if any)
  stage: qualify   → lead-qualifier      (judge: score the lead, fit vs ICP)            [build]
  stage: branch    → (qualified? hot? cold?)
  stage: respond   → lead-orchestrator  (fan-out by channel the lead used)
                   ├── email-responder     → reply / next-step email                  [build]
                   └── text-responder       → SMS reply                                 [build]
  stage: handoff   → sales-handoff       (route qualified leads to a human / CRM)      [build]
  write state (lead_state: this lead's thread, status, next-touch date)
```

**Where things sit:**
- *Qualifying the lead* — `lead-qualifier` (a `judge` role type). Reasoning, not
  routing.
- *Composing the reply* — `email-responder` / `text-responder`. These are the
  trust-critical ones: if they auto-send, they're `clone` kind with hard brakes
  on *what* they may say (no committing the user, no fabricating offers, no
  echoing anything sensitive) and `trust` requiring cite-the-lead + flag
  confidence on the qualification. Start them as `partner` (draft, human sends).
- *Routing to sales* — `sales-handoff`. A small orchestrator that writes to a
  CRM / notifies a human. Bounded action, hard brakes.
- *Lead memory* — `lead_state` in the store, so a responder knows "we already
  emailed this lead twice, they opened but didn't reply." Without state, every
  touch is amnesiac; with it, the responder can *escalate or back off*. This is
  where state pays off most.

> The same `campaign-judge` / `lead-qualifier` *capability* (read evidence,
> render a verdict) is reused across launch retro, mid-week pulse, and lead
> qualification. That's the library-first payoff: one judge agent, three jobs.

---

## 10. A concrete inventory for ElfTech marketing

**Reusable library agents — already in `agents/`:**
- `marketing-ideator` — generate 3+ candidate messages
- `marketing-debater` — critique candidates
- `marketing-judge` — settle on the message / render verdicts (launch retro,
  mid-week pulse, message settle)
- `social-adapter` — IG / Snapchat / X
- `blog-writer` — short blog post
- `short-video-ideator` — Shorts / TikTok scripts

**Reusable library agents — to build:**
- `message-architect` — turn ICP + brand + goal into a campaign angle; evolve it
  week-over-week (skill: `evolve-message`)
- `email-composer` — email sequences (launch + weekly + responder share this)
- `text-composer` — SMS copy
- `analytics-reader` — pull + read metrics, flag surprises (`researcher` role)
- `lead-qualifier` — score a lead against ICP (`judge` role)
- `email-responder` / `text-responder` — inbound reply composers (trust-critical)
- `sales-handoff` — route qualified leads to CRM / human

**Reusable orchestrators — to build:**
- `launch-orchestrator` — fan-out for a launch (deliberation + channels)
- `weekly-orchestrator` — fan-out for a week's campaign
- `lead-orchestrator` — fan-out for an inbound lead

**Per-product (Steward) — to build:**
- `steward-brand` (thin agent, soul = voice) *or* `context/steward-voice.md` +
  `context/steward-icp.md` + `context/steward-value-prop.md`

**Workflows (Armature YAML) — to build:**
- `steward-launch.yml` (§7)
- `weekly-generate.yml` + `midweek-pulse-check.yml` (§8)
- `lead-respond.yml` (§9)

**Infra (not Armature):**
- cron / n8n: Mon 8am → weekly-generate; Wed → midweek-pulse; webhook → lead-respond
- state store: `current_message`, `last_verdict`, `cumulative_metrics`,
  `this_week_assets`, `lead_state` (per-lead threads)

When you launch the *next* product (Tessera), you reuse every agent and every
orchestrator above, write a thin `tessera-brand` (or context), and clone the
three workflows with Tessera's `agent_library` binding. The craft is amortized;
the product is data.

---

## 11. Principles (the checklist)

1. **Agent = identity + capability + self-guardrails (reusable). Workflow =
   coordination + wiring (specific). Scheduler = the clock. State = the memory.**
   Don't make the workflow do all four.
2. **The craft is the agent; the product is data.** Capabilities are library
   agents; brand/ICP/value-prop are context or thin per-product agents.
3. **Right-size agents.** Reusable role → library agent. One-trick-used-once →
   a stage task. God-agent → split into specialists + an orchestrator.
4. **Subagents are library agents; orchestrators reference, don't own.** Fan-out
   is the good subagent pattern; delegation policy in the orchestrator, available
   subagents in the workflow's `agent_library`.
5. **Loops are scheduler + state, not DAG.** Armature can't self-loop or hold
   state between runs; the weekly recurrence and the mid-week branch live in
   cron + a state store, with short DAGs the scheduler fires.
6. **Two trigger shapes, one library.** Cadence (cron) and event (webhook) both
   fire Armature DAGs; don't build separate agent families for each.
7. **Guardrails scale with autonomy.** Start everything `partner` (recommend);
   promote an agent to `clone` per bounded action only after review, with hard
   brakes + trust on the send. The `kind` flip is a deliberate trust decision.
8. **Guardrails survive spawning.** A subagent keeps its brakes/trust; its safety
   fragment must bubble up to the workflow, not get dropped. (Verify in the
   Armature subagent path.)
9. **State makes agents non-amnesiac.** Anything that must survive a run — the
   current message, the last verdict, a lead's history — lives in the store, read
   at run start, written at run end.

---

## 12. The one thing to verify before building

This doc assumes the Armature subagent spawn path accepts a **library agent id**
(or a capability archetype the workflow binds to an id) and that a spawned
agent's **safety fragment bubbles up** to the workflow rather than being dropped.
Both are load-bearing for §4 and §8. If the current spawn API instead takes an
inline definition or silently drops the fragment, the recommendation still holds
in principle but the work to get there is: stop inlining (point at the library)
and make the fragment propagate. Worth a look at the Armature subagent code before
committing the orchestrator design above to real workflows.