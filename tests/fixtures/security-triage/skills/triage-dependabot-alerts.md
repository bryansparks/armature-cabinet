---
id: appsec.triage-dependabot-alerts
version: "0.1.0"
name: triage-dependabot-alerts
when: A repository has open Dependabot alerts that need prioritizing.
# --- thick ---
tools:
  - github:dependabot.list_alerts        # resolved via the org GitHub App
  - github:advisories.get
  - github:dependency-graph.get
context:
  - context/severity-rubric.md
  - context/finding-schema.md
cost_tier: T2
outputs: Finding[]
---

1. List open Dependabot alerts for the target repo(s).
2. For each, pull the advisory and the dependency path from the dependency graph.
3. Apply `rank-findings` (gate, then rank) using the severity rubric.
4. Drop anything not reachable from a shipped entry point into a "review later"
   bucket — present it, but below the fold.
5. Return a `Finding[]` shortlist: top items first, each with severity, the
   reachability call, and a one-line "why this one" pointing at the evidence.
