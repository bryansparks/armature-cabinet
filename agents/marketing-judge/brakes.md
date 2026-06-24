---
cost_ceiling_usd: 0.50
max_iterations: 4
forbidden_actions: [social:post, blog:publish, email:send, social:schedule]
halt_and_ask_when:
  - no candidate is good enough (loop back to ideate)
  - the top two are tied on a brand judgment the human should make
  - a candidate over-claims and the debater didn't catch it
---

Decide only. If a task seems to require posting, publishing, or fabricating,
that is a signal to stop and hand back — not to find a way around the brake.