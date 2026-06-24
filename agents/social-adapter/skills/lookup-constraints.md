---
id: social.lookup-constraints
version: "1.0.0"
name: lookup-constraints
when: A platform's constraints (length, aspect ratio, format, tone) need looking up before adapting.
context:
  - context/platform-constraints.md
tools:
  - instagram:media.constraints
  - x:media.constraints
  - snapchat:media.constraints
cost_tier: T1
outputs: PlatformConstraints
---

1. Take a platform name (instagram | x | snapchat).
2. Fetch its current constraints per the reference: text length, image aspect
   ratio + format, safe zones, tone norms, hashtag/mention limits, disclosure
   rules.
3. Return a `PlatformConstraints` (platform, text limit, aspect ratio, format,
   tone notes, hashtag limits, disclosure rules).
4. If a constraint has changed since the rubric was written, note the delta —
   don't silently use a stale limit.