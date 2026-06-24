---
id: marketing.refine-candidate
version: "1.0.0"
name: refine-candidate
when: An angle needs polishing into a full candidate weekly marketing message.
context: [context/message-rubric.md]
tools: []
cost_tier: T2
outputs: CandidateMessage
---

1. Take an angle (from ideate-angles) + the seed as input.
2. Polish it into a full candidate message per the rubric: a clear line, the
   hook, the substance, a CTA if the seed has one.
3. Keep it honest — every claim traces to the seed; no fabrication.
4. Return `CandidateMessage` (the message, the angle it came from, the seed ref,
   confidence it's faithful, brand-safety flag if any).
5. If the angle can't be polished without inventing, flag it — don't fabricate.