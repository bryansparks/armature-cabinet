---
# Hard limits. The runtime treats these as constraints, not suggestions.
cost_ceiling_usd: 2.00
max_iterations: 10
forbidden_actions:
  - web:form.submit
  - web:post
  - email:send
  - web:purchase
  - web:auth.login
halt_and_ask_when:
  - a source is behind a paywall or login the user hasn't authorized
  - a claim can't be traced to a specific passage — don't fabricate one
  - sources contradict so sharply that a synthesis would mislead
  - an "actionable" option would require a commitment the user should decide
  - the material is large enough that a full synthesis would exceed the budget
---

Read and synthesize only. If a task seems to require submitting, publishing,
paying, or logging in, that is a signal to stop and hand back to the user — not
to find a way around the brake.