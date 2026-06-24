---
id: research.write-brief
version: "1.0.0"
name: write-brief
when: The distillations, themes, and actions need to be assembled into one short, sourced brief.
tools: []
cost_tier: T2
outputs: SynthesisBrief
---

1. Take the `SourceDistillation`s, `Themes`, and `ActionOptions` as input.
2. Assemble one brief: sources (one line each), key points (sourced), themes
   (with supporting sources), and the action options.
3. Keep it short enough to read in one sitting — cut restatement and filler.
4. Every claim in the brief cites its source; every action option names its
   assumption.
5. Return a `SynthesisBrief` (the markdown brief, a one-line "the headline,"
   confidence, what's most uncertain). Do not submit, publish, or email it.