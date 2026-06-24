---
id: video.write-script
version: "1.0.0"
name: write-script
when: A hook needs a full short-video script (beats, VO/captions, shot list) for YouTube Shorts or TikTok.
context:
  - context/script-rubric.md
tools: []
cost_tier: T2
outputs: Script
---

1. Take a hook (from ideate-hooks) + the source message + a platform (YouTube
   Shorts or TikTok).
2. Write the script per the rubric: hook (3s), problem/setup, payoff, CTA —
   15-60 seconds, paced for the platform.
3. Include VO/caption text + on-screen text cues + a shot list (what to show
   each beat).
4. Return `Script` (platform, duration, the script with beats + shot cues,
   source message ref, confidence it lands, brand-safety flag if any).
5. Every claim in the script traces to the source message — no fabricated
   benefits.