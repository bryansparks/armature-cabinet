---
id: social.adapt-to-snapchat
version: "1.0.0"
name: adapt-to-snapchat
when: A message + image need one Snapchat-native version (9:16 vertical, short overlay text, Snap tone).
context:
  - context/platform-constraints.md
  - context/adaptation-rubric.md
tools:
  - snapchat:media.constraints
  - image:resize
  - image:crop
  - image:format
  - image:safezone
cost_tier: T2
outputs: PlatformVersion
---

1. Look up Snapchat's constraints (9:16 vertical, short overlay text, safe zones
   for text, Snap-native tone).
2. Reduce the message to a short overlay line per the adaptation rubric — the
   hook, nothing more; the image carries the rest.
3. Reshape the image to 9:16 (resize/crop/format). Keep the subject in the safe
   zone so the overlay text doesn't cover it.
4. Return a `PlatformVersion` (platform: snapchat, overlay text, image ref +
   reshape notes, what was cut and why, confidence the substance holds).
5. If the message can't reduce to an overlay without losing the point, flag it.