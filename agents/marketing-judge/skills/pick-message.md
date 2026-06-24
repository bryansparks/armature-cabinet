---
id: marketing.pick-message
version: "1.0.0"
name: pick-message
when: Candidates + critiques + a comparison need a single pick (or a 'none good enough' call).
context: [context/judging-rubric.md]
tools: []
cost_tier: T1
outputs: Verdict
---

1. Take the candidates, their critiques, and the comparison as input.
2. Weigh per the rubric: which candidate best serves the week's goal, accepting
   which trade-off.
3. If one candidate clearly wins, pick it + name the critiques that drove the
   pick, the trade-off accepted, and what to watch for.
4. If none is good enough (all over-claim, all miss the audience, all risky),
   declare "none good enough, re-ideate" — don't pick the least-bad.
5. If the top two are tied on a brand judgment (not a quality call), hand it to
   the human rather than guessing.
6. Return `Verdict` (the pick or the 're-ideate' call, the reasoning, the
   critiques cited, the trade-off, confidence).
7. The pick is a recommendation; nothing is posted.