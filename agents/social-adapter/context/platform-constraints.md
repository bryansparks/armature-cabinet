# Platform constraints

The live values come from the platform's `media.constraints` tool; this is the
reference shape + the defaults when a tool isn't available. Verify before you
rely on a number.

- **Instagram** — caption ~2,200 chars (but the first ~125 show before "more");
  image 1:1 (square) or 4:5 (portrait); JPG/PNG; hashtags in the caption (≤30);
  sponsored content must disclose (#ad / "Paid partnership").
- **X** — text 280 chars; image 16:9, JPG/PNG/WebP, ≤5MB; one or two hashtags max
  (the platform penalizes hashtag stuffing); plain, direct voice.
- **Snapchat** — 9:16 vertical image/video; overlay text short (a line or two);
  keep text out of the top/bottom safe zones (UI chrome lives there); Snap tone
  is casual, fast, visual — the image does the work, the text is a caption.

If a tool returns a constraint that contradicts this rubric, trust the tool and
note the delta. Don't use a stale limit to cut a message.