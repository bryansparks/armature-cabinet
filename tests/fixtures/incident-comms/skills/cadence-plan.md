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
