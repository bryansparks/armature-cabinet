---
# Hard limits. The runtime treats these as constraints, not suggestions.
cost_ceiling_usd: 1.00
max_iterations: 12
forbidden_actions:
  - gmail:send
  - gmail:archive
  - gmail:delete
  - gmail:trash
  - gmail:mark_read
  - gmail:draft.send
halt_and_ask_when:
  - a message requires a decision only the user can make (a yes/no, a payment, a commitment)
  - a proposed reply would commit the user to something
  - a message looks like phishing or an account-action alert the user didn't initiate
  - the inbox is large enough that a full pass would exceed the budget
  - a message contains credentials, 2FA codes, or secrets the agent shouldn't act on
---

Read-label-draft only. If a task seems to require sending, deleting, or marking
anything, that is a signal to stop and hand back to the user — not to find a way
around the brake.