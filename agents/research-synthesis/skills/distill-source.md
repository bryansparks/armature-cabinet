---
id: research.distill-source
version: "1.0.0"
name: distill-source
when: A single paper, article, or post needs its key points distilled, with claims separated from speculation.
context:
  - context/distillation-rubric.md
tools:
  - web:url.fetch
  - pdf:read
  - x:post.get
cost_tier: T2
outputs: SourceDistillation
---

1. Fetch/read the source the user gave (URL, PDF, or X post id).
2. Extract the key points per the rubric: for each, the claim, the evidence
   (or "speculation — no evidence offered"), and the passage it rests on.
3. Note the source type, author, and date so it's citable later.
4. Return a `SourceDistillation` (source ref, key points with claim/evidence/
   passage, an overall "what this source is actually saying" one-liner,
   confidence, what would change the call).
5. If a claim can't be traced to a passage, flag it — never fabricate a citation.