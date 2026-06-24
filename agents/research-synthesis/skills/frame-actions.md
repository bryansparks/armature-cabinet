---
id: research.frame-actions
version: "1.0.0"
name: frame-actions
when: The key points and themes need to be framed as actionable options the user can choose to pursue or ignore.
context:
  - context/action-framing-rubric.md
tools: []
cost_tier: T1
outputs: ActionOptions
---

1. Take the key points + themes as input.
2. For each insight worth acting on, frame an option per the rubric: the insight,
   a concrete "if you wanted to act on this" step, and the assumption the action
   rests on.
3. Keep options genuinely optional — the user may ignore all of them. Don't rank
   or push; present, don't prescribe.
4. Return `ActionOptions` (each: insight, the action step, the assumption,
   confidence, what would change it).
5. If an action would require a commitment the user should decide, flag it rather
   than drafting the commitment.