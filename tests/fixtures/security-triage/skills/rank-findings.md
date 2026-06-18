---
id: appsec.rank-findings
version: "1.0.0"
name: rank-findings
when: A set of raw security signals needs to be gated, then ordered for a human.
context:
  - context/severity-rubric.md
cost_tier: T2
outputs: Finding[]
# SHARED-SHELF CANDIDATE: source-agnostic, useful to any security partner.
# Vendored here today; later resolves from shelf://appsec/rank-findings@^1.0.
---

Two stages, deliberately separate:

**Gate.** Remove what doesn't deserve a human's attention: unreachable code paths,
dev-only dependencies, already-mitigated issues, known-accepted risks. The gate is
allowed to be aggressive — its failures are visible (something shows up that
shouldn't), unlike a ranking that silently buries a real finding.

**Rank.** Order survivors by exploitability x blast radius, not CVSS alone. A
medium CVE on an internet-facing auth path outranks a critical one in a script
that runs once a quarter behind the firewall.

Output is always the shared `Finding` shape so sources stay swappable — Dependabot
today, code scanning or a Dynatrace feed tomorrow, same downstream contract.
