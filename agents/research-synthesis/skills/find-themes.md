---
id: research.find-themes
version: "1.0.0"
name: find-themes
when: Several sources have been distilled and the cross-cutting themes need extracting.
context:
  - context/theme-rubric.md
tools: []
cost_tier: T2
outputs: Themes
---

1. Take two or more `SourceDistillation`s as input.
2. Find claims that recur across sources (a theme needs at least two sources —
   see the rubric). Name the sources for each theme.
3. Note where sources agree, where they complement, and where they contradict
   (contradiction is itself a finding — surface it, don't smooth it over).
4. Return `Themes` (each theme: the cross-cutting claim, the sources supporting
   it, agreements/contradictions, confidence).
5. Never manufacture a theme from a single source — that's a key point, not a theme.