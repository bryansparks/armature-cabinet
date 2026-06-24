# Phishing / account-compromise signals

Judge from metadata + message text. Never follow links or open attachments to
"check."

- **Urgent account action** — "your account will be closed," "verify
  immediately," fake security alerts. Real services rarely demand urgency.
- **Mismatched sender** — display name says "Google" but the domain isn't
  google.com; reply-to differs from from.
- **Credential / 2FA asks** — any message requesting a password, code, or
  "confirmation" of credentials. Always suspicious.
- **Unexpected links/attachments** — links to lookalike domains, attachments the
  user wasn't expecting (invoices from unknown vendors, "shared document").
- **False urgency / fear** — threats, limited-time pressure, "act now or lose
  access."
- **Account-action the user didn't initiate** — password-change notices, login
  alerts for sessions the user didn't start. These may be real warnings OR the
  start of a compromise; either way, escalate, don't summarize-and-dismiss.

Verdict scale: likely-safe / suspicious / likely-phish. When in doubt,
suspicious + escalate — the cost of a false alarm is low; the cost of dismissing
a real phish is high.