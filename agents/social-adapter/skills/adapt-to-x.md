---
id: social.adapt-to-x
version: "1.0.0"
name: adapt-to-x
when: A message + image need one X-native version (<=280 chars, 16:9 image, plain voice).
context:
  - context/platform-constraints.md
  - context/adaptation-rubric.md
tools:
  - x:media.constraints
  - image:resize
  - image:crop
  - image:format
cost_tier: T2
outputs: PlatformVersion
---

1. Look up X's constraints (280-char limit, 16:9 image, plain-text voice,
   hashtag/mention norms).
2. Trim the message to the limit per the adaptation rubric — preserve the claim,
   cut everything that isn't the claim. One hashtag max, only if the message
   implies it.
3. Reshape the image to 16:9 (resize/crop/format). Keep the subject.
4. Return a `PlatformVersion` (platform: x, the <=280-char text, image ref +
   reshape notes, what was cut and why, confidence the substance holds).
5. If 280 chars can't hold the claim without distortion, flag it — don't mangle.