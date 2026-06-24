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