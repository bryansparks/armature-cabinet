# Audience rubric

Calibrate every message to its audience. The same incident reads differently
to each.

**Exec / leadership.** Wants impact, exposure, and what they need to decide or
approve. One paragraph. Lead with business impact, not mechanism. No acronyms
without a gloss.

**Engineering / on-call.** Wants mechanism, current hypothesis, and what's
being tried. Technical detail welcome. Lead with what's known and the active
mitigation.

**Customer / external.** Wants what's affected, what to do, and when to expect
resolution. Plain language, no internal tool names, no blame. Lead with the
user-visible impact and the workaround if any.

**Severity → cadence.** sev1: every 30 min, all audiences. sev2: hourly, exec
+ eng. sev3: every 4h, eng + customer-only-if-affected. sev4: summary at close.

**Tone.** Calm, factual, no reassurance that isn't backed by a signal.
`Unknown` is a valid and respected status — say it rather than fill the
silence.
