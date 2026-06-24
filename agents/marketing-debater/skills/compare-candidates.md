---
id: marketing.compare-candidates
version: "1.0.0"
name: compare-candidates
when: Several candidates + their critiques need a side-by-side comparison for the judge.
context: [context/critique-rubric.md]
tools: []
cost_tier: T2
outputs: Comparison
---

1. Take N candidates + their critiques as input.
2. Compare side-by-side per the rubric criteria: which candidate is clearest,
   most resonant, lowest-risk, best brand-fit, least over-claiming.
3. Surface the trade-offs (candidate A is sharpest but riskier; B is safer but
   blander). Don't rank or pick — that's the judge.
4. Return `Comparison` (per-candidate summary, the trade-offs, where they're
   similar, where they diverge, confidence).
5. If candidates are too similar to differentiate, flag it — the judge needs to
   know.