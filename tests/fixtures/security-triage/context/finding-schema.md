# Finding — the shared output contract

Every triage skill emits a list of `Finding`. Keeping one shape across sources is
what lets the source adapter stay pluggable (Dependabot, secret scanning, code
scanning, or a future Dynatrace feed all reduce to this).

```python
class Finding(BaseModel):
    id: str                      # stable, source-prefixed (e.g. "dependabot:1234")
    source: str                  # dependabot | secret-scanning | code-scanning | ...
    title: str
    severity: Literal["critical", "high", "medium", "low"]
    reachable: bool | None       # None = not yet determined
    exploitability: Literal["high", "medium", "low"]
    blast_radius: Literal["high", "medium", "low"]
    evidence_url: str            # links back to the alert / advisory
    why: str                     # one line: why this rank
    confidence: float            # 0-1; below trust.yaml threshold -> escalate
```
