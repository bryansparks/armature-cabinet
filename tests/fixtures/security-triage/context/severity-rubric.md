# Severity rubric — exploitability x blast radius

Rank on the product of two axes, not on CVSS in isolation.

**Exploitability** — how readily a real attacker reaches it:
- High: reachable from an unauthenticated, internet-facing path
- Medium: reachable but behind auth or on an internal network
- Low: not reachable from shipped code, or requires improbable preconditions

**Blast radius** — what falls if it goes:
- High: customer data, credentials, or production control plane
- Medium: a single service or a non-critical data store
- Low: dev tooling, test fixtures, ephemeral environments

The shortlist a human sees is the High-High and High-Medium corner. Everything
else is presented below the fold, not hidden.
