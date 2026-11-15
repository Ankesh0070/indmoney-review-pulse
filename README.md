# Review Pulse — INDmoney

Turn the last **12 weeks** of public **App Store + Play Store** reviews into a one-page **weekly pulse**: priority-ranked themes, real user quotes, three action ideas, early-warning **signals**, and a ready-to-send **email draft**. Built for the LIP challenge. Product: **INDmoney**.

> Public review exports only · No PII anywhere · Max 5 themes · Note ≤ 250 words

The dashboard is a single self-contained `index.html` — no backend. You can **drop your own review CSV straight onto it**; redaction, theme assignment and every number are computed locally in your browser (nothing is uploaded).

---

## What's new in v3

| Feature | Where |
|---|---|
| **Import your own export** — drag & drop App Store Connect / Play Console CSVs (columns auto-mapped) | dashboard + `src/import_reviews.py` |
| **PII redaction on import** — emails, phones, PAN, Aadhaar-style IDs, folio/account numbers, @handles, links | both |
| **Auto-themer** — keyword scorer, editable in `data/themes.json` (reproduces all 243 sample labels) | both |
| **Signals** — mention spikes vs trailing 8 weeks (σ-based), 3-week sustained negativity, real improvements, rating drops | note, email, PDF, dashboard |
| **Trending phrases** in negative reviews vs the previous 4 weeks; click one to see the reviews | dashboard, email, PDF |
| **What-if priority weights** — sliders re-rank themes live | dashboard |
| **Review explorer** — search, theme/rating/scope filters, export filtered CSV | dashboard |
| **Click any week** on the chart (or ← / →), shareable URL hash, source filter built from the data | dashboard |
| **Exports** — note `.md`, JSON, cleaned CSV, Slack-formatted summary, print-to-PDF | dashboard |
| Rating-mix histogram, accessible controls, print stylesheet, remembered dark mode | dashboard |
| **One core, two runtimes** — `src/pulse.py` and `dashboard/pulse-core.js` are tested to agree byte-for-byte on note, email and every number | `tests/` |
| Windows-safe (UTF-8 everywhere, no `rm`, no `make` required) | `scripts/build_all.py` |

---

## Quick start

```bash
pip install -r requirements.txt
python scripts/build_all.py --test       # note -> pdf -> dashboard, then all tests
# open index.html  (or: python -m http.server 8000)
```

`make all` / `make test` do the same where `make` exists. `build_all.py` never overwrites your data; use `--sample` to regenerate the synthetic CSV.

### Deploy free on GitHub Pages
Push, then **Settings → Pages → Deploy from a branch → `main` / root**. `index.html` is at the repo root on purpose.

---

## Using your own reviews

**In the browser (fastest):** open `index.html`, click **Import reviews CSV** (or drop files anywhere on the page). Tag the store through the filename (`playstore…`, `appstore…`) or a `source` column. You get the full dashboard, note, email, Slack text and cleaned CSV for that data.

**In the pipeline (for the PDF + committed outputs):**

```bash
python src/import_reviews.py "appstore.csv=App Store" "playstore.csv=Play Store"
python scripts/build_all.py --test
```

Recognised headers include `date / Review Date / Review Last Update Date and Time`, `rating / Star Rating`, `text / Review Text / Body`, `title / Review Title`, `source / Store`. Reviewer name columns are never read. Rows without a valid date or 1–5 rating are skipped and counted in the report.

Public exports only (App Store Connect → *Ratings & Reviews*, Play Console → *Reviews*) — no scraping behind logins.

---

## How it works

```
data/reviews_sample.csv ─► src/pulse.py ─► output/pulse_data.json ─► weekly_note.md · email_draft.txt · weekly_note.pdf
                       └► dashboard/pulse-core.js (same logic) ─► index.html
data/themes.json  = themes + keywords + action ideas (shared by both)
```

**Priority** (0–100, weights adjustable in the dashboard):

```
priority = 0.50 × negativity%  +  0.35 × volume_share  +  0.15 × momentum
```
`negativity%` = share of 1–2★ this week · `volume_share` = mentions vs busiest theme · `momentum` = week-over-week change in mentions (±9 pts per mention, clamped 0–100).

**Signals**: *spike* = this week's mentions ≥ 1.5σ above the trailing 8-week mean (≥ 3 mentions; σ floored at 0.75 so tiny counts don't fire); *sustained* = ≥ 75% negative for 3 straight weeks; *improving* = negativity down ≥ 20 pts vs 4 weeks ago; plus ±0.30 average-rating moves.

**Trending phrases**: words and two-word phrases in this week's 1–2★ reviews ranked by `count × ln(lift)` against the previous 4 weeks (smoothed), redundant words folded into their phrase.

**Note budget**: `fit_note` picks the richest variant (signals + full footer → shorter footer → fewer signals) that stays ≤ 250 words.

## Repository structure

```
index.html                 generated dashboard (served by Pages)
data/reviews_sample.csv    INPUT (redacted; schema: review_id,date,week,source,rating,title,text,theme)
data/themes.json           themes, keywords, actions, stopwords
src/pulse.py               shared core: redaction, classifier, stats, priority, signals, trending, note, email
src/build_note.py          CSV -> output/{pulse_data.json, weekly_note.md, email_draft.txt}
src/build_pdf.py           pulse_data.json -> output/weekly_note.pdf (one page)
src/import_reviews.py      raw exports -> redacted, themed CSV
src/build_reviews.py       deterministic synthetic sample generator
dashboard/template.html    UI;  dashboard/pulse-core.js  browser twin of pulse.py
scripts/inject_data.py     inlines core + config + data into index.html (PII guard)
scripts/build_all.py       cross-platform runner
tests/test_pulse.py        19 Python unit tests;  tests/parity.js  JS-vs-Python equivalence + behaviour checks
```

## Notes on the data
The bundled CSV is a **synthetic, redacted sample** shaped to tell a realistic story (withdrawal delays spiking in the last 3 weeks, app stability recovering after an update, a mid-window fee controversy). Because it is built from a small set of phrasings, trending phrases there are repetitive; real exports are far more varied. The keyword themer is deliberately simple and transparent — tune `data/themes.json` if your data disagrees, or swap in an LLM classifier restricted to the same 5 labels.

## Constraints honoured
Public exports only · no PII in any artifact (guard aborts the build) · ≤ 5 themes (top 3 in the note) · note ≤ 250 words (enforced in code and CI).

> Educational prototype. Not affiliated with INDmoney, Apple, or Google.
