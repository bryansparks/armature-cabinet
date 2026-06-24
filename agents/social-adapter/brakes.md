---
# Hard limits. The runtime treats these as constraints, not suggestions.
cost_ceiling_usd: 1.00
max_iterations: 8
forbidden_actions:
  - instagram:post
  - instagram:schedule
  - x:post
  - x:schedule
  - snapchat:post
  - snapchat:schedule
  - social:delete
  - social:publish
halt_and_ask_when:
  - a platform's constraint would distort the message's meaning
  - the supplied image can't fit a platform without a crop that loses the subject
  - the message is ambiguous about audience or tone
  - a platform requires a disclosure (sponsored) the message didn't specify
---

Reshape and adapt only. If a task seems to require posting, publishing,
scheduling, or deleting, that is a signal to stop and hand back to the user —
not to find a way around the brake.