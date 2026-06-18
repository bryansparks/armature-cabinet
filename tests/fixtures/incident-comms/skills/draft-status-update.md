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
