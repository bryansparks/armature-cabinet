---
id: gmail.draft-reply
version: "1.0.0"
name: draft-reply
when: A message needs a response and a proposed reply should be drafted for the user to review.
tools:
  - gmail:messages.get
  - gmail:drafts.create
cost_tier: T2
outputs: ProposedReply
---

1. Re-read the message and the summary; identify what a reply must accomplish.
2. Draft a short, plain reply that does exactly that — no filler, no overcommitment.
3. If the reply would commit the user (a meeting, a payment, a yes/no), stop and
   flag it instead of drafting the commitment; offer a non-committal alternative.
4. Save it as a Gmail DRAFT (never send) and return a `ProposedReply` (message id,
   draft id, the draft text, what it commits to if anything, confidence).
5. The user reviews and sends — the agent never sends.