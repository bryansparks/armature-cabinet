---
id: gmail.summarize-message
version: "1.0.0"
name: summarize-message
when: A message was flagged important and needs a one-line summary plus the ask.
context:
  - context/summary-rubric.md
tools:
  - gmail:messages.get
cost_tier: T1
outputs: MessageSummary
---

1. Fetch the full message (sender, subject, body, attachments by name/type only).
2. Summarize per the rubric: the ask in one sentence; the deadline if any; the
   cost of ignoring it.
3. If a response is required, note who owes it and by when.
4. Return a `MessageSummary` (message id, one-line summary, the ask, deadline,
   confidence, what would change the call).
5. Never reproduce credentials/2FA/secrets — reference them by location only.