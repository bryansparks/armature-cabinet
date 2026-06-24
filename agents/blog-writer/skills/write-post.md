---
id: blog.write-post
version: "1.0.0"
name: write-post
when: A message needs a short blog post entry (headline + a few paragraphs) that elaborates it without fabricating.
context:
  - context/post-rubric.md
tools: []
cost_tier: T1
outputs: BlogPost
---

1. Take the message + a chosen headline (from write-headline) as input.
2. Write the post per the rubric: headline, the claim, the elaboration (3-6
   paragraphs), a CTA if the message has one.
3. Every claim traces to the source message — no fabricated benefits, quotes,
   or stats. Elaborate; don't invent.
4. Default to a clear-neutral voice unless a voice/audience was specified.
5. Return `BlogPost` (headline, the post body, source message ref, confidence
   every claim is supported, brand-safety flag if any).
6. If the message is too thin to support a non-fabricated post, flag it rather
   than padding.