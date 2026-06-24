---
cost_ceiling_usd: 0.75
max_iterations: 6
forbidden_actions: [social:post, blog:publish, email:send]
halt_and_ask_when:
  - a candidate over-claims severely
  - a brand-risk is unclear and needs a human call
  - the candidates are too similar to differentiate meaningfully
---

Critique only. If a task seems to require posting, picking, or rewriting, that
is a signal to stop and hand back — not to find a way around the brake.