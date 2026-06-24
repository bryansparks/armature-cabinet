---
id: video.ideate-shots
version: "1.0.0"
name: ideate-shots
when: A script needs a shot/visual idea list (what to show each beat, b-roll, on-screen text).
context:
  - context/shot-rubric.md
tools: []
cost_tier: T2
outputs: ShotList
---

1. Take a script (from write-script) as input.
2. Per beat, ideate the visual per the rubric: b-roll, on-screen text, a focal
   subject, pacing notes.
3. Keep visuals shootable + honest — no mockups that imply a claim the message
   doesn't make.
4. Return `ShotList` (per beat: the visual idea, b-roll suggestion, on-screen
   text, pacing, confidence it's shootable + on-message).
5. Flag any shot that would misrepresent the product or over-claim.