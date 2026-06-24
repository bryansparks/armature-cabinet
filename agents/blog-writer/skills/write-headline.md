---
id: blog.write-headline
version: "1.0.0"
name: write-headline
when: A message needs 3+ short-blog headline candidates.
context:
  - context/headline-rubric.md
tools: []
cost_tier: T1
outputs: Headlines
---

1. Take the marketing message as input.
2. Generate 3+ headline candidates per the rubric — clear over clever, the
   message's claim front-loaded, no clickbait.
3. Each headline must be faithful — it reflects the message, not an inflated
   version.
4. Return `Headlines` (each: the headline, why it fits, confidence it's faithful).
5. Flag any headline that over-claims or misleads.