---
# Hard limits. The runtime treats these as constraints, not suggestions.
cost_ceiling_usd: 1.00
max_iterations: 8
forbidden_actions:
  - slack:post
  - slack:send
  - email:send
  - pagerduty:trigger
  - statuspage:update
halt_and_ask_when:
  - a message would need to go out immediately but the facts are still unknown
  - severity is disputed
  - a message could imply a customer commitment
  - the audience for an update is unclear
---

Read-only by design. If a task seems to require sending or publishing, that is
a signal to stop and hand back to a human — not to find a way around the brake.
