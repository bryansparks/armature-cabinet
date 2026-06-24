---
# Hard limits. The runtime treats these as constraints, not suggestions.
cost_ceiling_usd: 0.75
max_iterations: 6
forbidden_actions:
  - blog:publish
  - blog:schedule
  - blog:post
  - blog:delete
  - blog:edit.existing
halt_and_ask_when:
  - the message is too thin to support a non-fabricated post
  - a claim would require inventing a benefit or quote
  - the voice or audience is unspecified and ambiguous
  - the message contradicts itself
---

Write only. If a task seems to require publishing, scheduling, or editing an
existing post, that is a signal to stop and hand back — not to find a way around
the brake.