# Security Triage Partner

A read-only AppSec partner that ranks GitHub-native security signals (Dependabot,
secret scanning, code scanning) and hands a human a short, evidenced list of what
actually needs attention. It recommends; it never writes.

This folder is an agent definition per **Agent Definition Schema v0.1.0**.

- `agent.yaml` — the manifest / contract
- `soul.md`, `mandate.md` — who it is, what it's for (always loaded)
- `brakes.md`, `trust.yaml` — what it won't do, how it proves its work
- `skills/` — procedures, summoned by the task
- `context/` — the severity rubric and the shared Finding contract
- `state/` — created and owned by the runtime; not part of the definition

Tool resolution is **GitHub-native**: skills name `github:*` operations resolved
through the org's existing GitHub App. No new tooling to adopt.
