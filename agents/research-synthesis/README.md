# research-synthesis (example agent)

A reference cabinet agent: a **research-synthesis partner** (`researcher`
role-type) that takes one or more papers/articles/X posts and returns a short,
sourced brief of key points + cross-cutting themes, with each insight framed as
an actionable option the user can choose to pursue or ignore. Never acts.

Exercises parts of the spec the gmail-reader example doesn't: the
`armature_role_type: researcher` override, web/pdf tools, and skills with **no
tools** (the empty-tools path). Build it with:

```bash
armature-cabinet build agents/research-synthesis
```