# Label rubric

One label per message — pick the best fit, in this priority order:

- **suspicious** — phishing/account-compromise signals (see phishing-signals). Always wins.
- **action-required** — someone needs the user to do a thing, with a deadline.
- **needs-response** — a reply is expected; not necessarily urgent.
- **billing** — money: invoices, receipts, payment failures, subscription changes.
- **calendar** — meetings, invites, schedule changes.
- **personal** — a real person the user knows, not transactional.
- **newsletter** — bulk/automated content the user opted into (or didn't).
- **FYI** — informational, no action expected.

When two fit, pick the more actionable one
(action-required > needs-response > billing > calendar > personal > FYI > newsletter).
Suspicious overrides everything.