---
id: social.adapt-to-instagram
version: "1.0.0"
name: adapt-to-instagram
when: A message + image need one Instagram-native version (square or 4:5 card, caption, hashtags).
context:
  - context/platform-constraints.md
  - context/adaptation-rubric.md
tools:
  - instagram:media.constraints
  - image:resize
  - image:crop
  - image:format
cost_tier: T2
outputs: PlatformVersion
---

1. Look up Instagram's constraints (caption length, 1:1 or 4:5 aspect, format,
   hashtag norms).
2. Shorten/focus the message into a caption per the adaptation rubric — preserve
   the substance, cut the filler, keep the hook. Add hashtags only if the
   message implies them.
3. Reshape the supplied image to the aspect (resize/crop/format) — never generate
   a new image. Keep the subject in the safe zone.
4. Return a `PlatformVersion` (platform: instagram, caption, image ref +
   reshape notes, what was cut and why, confidence the substance holds).
5. If the caption limit or the crop would distort the message, flag it — don't
   produce a distorted version.