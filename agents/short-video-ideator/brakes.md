---
# Hard limits. The runtime treats these as constraints, not suggestions.
cost_ceiling_usd: 1.50
max_iterations: 8
forbidden_actions:
  - youtube:upload
  - youtube:publish
  - tiktok:post
  - tiktok:upload
  - video:render.final
  - video:publish
halt_and_ask_when:
  - the message is too thin to support a non-fabricated script
  - a candidate would over-claim or deceive
  - a sponsored disclosure is unclear or missing
  - the brand-safety of a trend or format is uncertain
---

Ideate only. If a task seems to require uploading, posting, producing final
video, or publishing, that is a signal to stop and hand back — not to find a way
around the brake.