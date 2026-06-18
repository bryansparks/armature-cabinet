---
id: appsec.triage-secret-scanning
version: "0.1.0"
name: triage-secret-scanning
when: A repository has secret-scanning alerts to assess.
tools:
  - github:secret-scanning.list_alerts
  - github:secret-scanning.get_alert
context:
  - context/finding-schema.md
cost_tier: T1            # potential live credentials — treat as trust-critical
outputs: Finding[]
---

1. List open secret-scanning alerts.
2. For each, judge whether the hit looks live vs. a test fixture, placeholder, or
   already-rotated value — using the location and surrounding context, never by
   echoing the secret itself.
3. Anything that looks live escalates immediately (see trust.yaml), above ranking.
4. Return a `Finding[]` with the live / likely-dead call and the evidence for it.
   Never reproduce the secret value in output — reference it by location only.
