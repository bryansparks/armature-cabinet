# gmail-reader (example agent)

A reference cabinet agent: a **read-only Gmail triage partner** that labels
messages, summarizes the important ones, and drafts proposed replies — never
sends. Exercises the full cabinet spec (soul / mandate / brakes / trust + 4
skills + 3 context files, all frontmatter fields including `outputs`/`context`/
`cost_tier`).

Build it with:

```bash
armature-cabinet build agents/gmail-reader
```

The compiled bundle lands in `dist/gmail-reader/agent.yaml`; the advisory safety
fragment in `dist/gmail-reader/gmail-reader.safety.yaml`.