---
id: gmail.detect-phishing
version: "1.0.0"
name: detect-phishing
when: A message looks suspicious and needs a phishing/account-compromise check before any summary or reply.
context:
  - context/phishing-signals.md
tools:
  - gmail:messages.get
cost_tier: T1
outputs: PhishingCall
---

1. Check the message against the phishing-signals rubric (urgent account action,
   mismatched sender domain, credential/2FA asks, unexpected links/attachments,
   tone of false urgency).
2. Return a `PhishingCall`: message id, verdict (likely-safe / suspicious /
   likely-phish), the signals that fired, confidence, and a recommended user
   action (do not click, verify out-of-band, change password).
3. If likely-phish, escalate immediately (per trust.yaml) — above any summary or
   reply.
4. Never follow links or open attachments to "check" them — judge from metadata
   + text.