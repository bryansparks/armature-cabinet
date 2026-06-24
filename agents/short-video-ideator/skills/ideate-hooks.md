---
id: video.ideate-hooks
version: "1.0.0"
name: ideate-hooks
when: A message needs 3+ short-video hook angles (the first-3-seconds grab).
context:
  - context/hook-rubric.md
tools: []
cost_tier: T2
outputs: Hooks
---

1. Take the marketing message as input.
2. Generate 3+ hook angles per the rubric — each earns the first 3 seconds
   (a question, a pattern-interrupt, a bold claim from the message, a relatable
   frustration).
3. Each hook must be faithful to the message — no inventing a hook the message
   doesn't support.
4. Return `Hooks` (each: the hook line, the angle, why it earns the watch,
   confidence it lands the message).
5. Flag any hook that would over-claim or mislead.