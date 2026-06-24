---
id: marketing.critique-candidate
version: "1.0.0"
name: critique-candidate
when: A candidate message needs critique on clarity, resonance, risk, brand-fit, and over-claiming.
context: [context/critique-rubric.md]
tools: []
cost_tier: T2
outputs: Critique
---

1. Take a candidate message as input.
2. Assess per the rubric: clarity (is the idea understandable in one read?),
   resonance (does it name what the audience feels?), risk (could it backfire?),
   brand-fit (is it on-brand?), over-claiming (does it promise more than the
   seed supports?).
3. For each criterion, give a specific critique — not vague ("doesn't land")
   but tied to a line/claim in the candidate.
4. Return `Critique` (candidate ref, per-criterion assessment + specific notes,
   overall strengths/risks, confidence).
5. Flag any over-claim or severe brand risk plainly.