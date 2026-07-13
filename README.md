# Review Pulse — INDmoney

Turn the last **12 weeks** of public **App Store + Play Store** reviews into a one-page **weekly pulse**: a priority-ranked view of top themes, real user quotes, and three action ideas — plus a ready-to-send **email draft**. Built for the LIP challenge. Chosen product: **INDmoney** (carried over from challenge 4).

> Public review exports only · No PII anywhere · Max 5 themes · Note ≤ 250 words

The prototype is a single self-contained `index.html` — no backend, no build step to view it. The Python pipeline regenerates the note, PDF, email draft, and the dashboard's embedded data for any new week.

---

## Demo

```bash
# View the dashboard — no install needed
open index.html              # macOS  (use "start index.html" on Windows)
# or serve it
python3 -m http.server 8000  # then visit http://localhost:8000
```

Switch the **Pulse week**, filter by **Source** (All / App Store / Play Store), toggle **light/dark**, tap a theme to read the underlying reviews, set a **Send to** address, and use **Copy email** / **Open in Gmail**.

> The email buttons use the browser clipboard and Gmail-compose URL — these work when you open `index.html` in a real browser or via GitHub Pages. Inside a sandboxed iframe the code falls back to copying the Gmail link so nothing fails silently.

### Deploy free on GitHub Pages
1. Push this repo to GitHub.
2. **Settings → Pages → Build and deployment → Source: “Deploy from a branch”**, branch `main`, folder `/ (root)`.
3. Your dashboard goes live at `https://<username>.github.io/<repo>/`.

`index.html` lives at the repo root specifically so Pages serves it directly.

---

## Repository structure

```
indmoney-review-pulse/
├── index.html                 # PROTOTYPE — dashboard with data injected (served by Pages)
├── README.md
├── LICENSE                    # MIT
├── .gitignore
├── requirements.txt           # reportlab, pypdf
├── Makefile                   # make all | data | note | pdf | dashboard | clean
├── data/
│   └── reviews_sample.csv     # redacted reviews (~243 rows, 12 weeks) — the INPUT
├── src/
│   ├── build_reviews.py       # builds the reviews CSV (seeded, deterministic)
│   ├── build_note.py          # CSV -> priority pulse -> note.md, email.txt, pulse_data.json
│   └── build_pdf.py           # pulse_data.json -> weekly_note.pdf (one-pager)
├── scripts/
│   └── inject_data.py         # injects CSV into the template -> index.html
├── dashboard/
│   └── template.html          # dashboard source (has the __DATA__ token)
├── output/                    # generated artifacts
│   ├── weekly_note.md         # the ≤250-word note
│   ├── weekly_note.pdf        # designed one-pager
│   ├── email_draft.txt        # subject + body, to a self alias
│   └── pulse_data.json        # computed stats (shared by note + PDF)
├── docs/
│   └── theme-legend.md
└── .github/workflows/build.yml  # CI: runs the pipeline + smoke checks on every push
```

**Why the split:** `data/` is the only input, `src/` + `scripts/` is the logic, `dashboard/template.html` is the view, and `output/` + `index.html` are generated. The dashboard, the note, and the PDF all compute from the **same logic** and are verified to produce identical numbers (avg, negativity, top themes, priority scores).

---

## Quick start (regenerate everything)

```bash
make install      # pip install -r requirements.txt
make all          # data -> note -> pdf -> dashboard
```

Or step by step (the workflow is **Import → Group → Generate Note → Draft Email**):

```bash
python3 src/build_reviews.py     # Import: build data/reviews_sample.csv
python3 src/build_note.py        # Generate note + email -> output/
python3 src/build_pdf.py         # Render output/weekly_note.pdf
python3 scripts/inject_data.py   # Refresh index.html for the dashboard
```

The “pulse week” is auto-detected as the most recent week in the CSV; week-over-week deltas compare to the prior week.

---

## How to re-run for a new week

1. **Import.** Export reviews for the new window — App Store Connect → *Ratings & Reviews* CSV, and Play Console → *Reviews* export (**public exports only, no scraping behind logins**). Overwrite `data/reviews_sample.csv`, keeping the columns `review_id, date, week, source, rating, title, text, theme`, and strip any reviewer name/handle on the way in.
2. **Group.** Tag each review with one of the 5 themes in [`docs/theme-legend.md`](docs/theme-legend.md) (keyword map, or let an LLM classify into exactly those 5 buckets).
3. **Generate.** `make note pdf dashboard` (or run the three scripts above).

---

## What makes it more than a counter

Themes are ranked by a **priority score (0–100)**:

```
priority = 0.50 × negativity%  +  0.35 × volume_share  +  0.15 × momentum
```

so a small-but-spiking issue can outrank a large-but-stable one. The dashboard adds a 12-week sentiment pulse chart, an auto-generated headline, a priority board (all 5 themes ranked), a week-over-week movers panel, per-theme trend sparklines, tap-to-expand drill-downs, and a live source filter. See [`docs/theme-legend.md`](docs/theme-legend.md) for the scoring detail.

---

## Notes on the data

`data/reviews_sample.csv` is a **synthetic, redacted sample** modeled on recurring public-review patterns for INDmoney (withdrawal/payout delays, fee surprises, support, app stability, KYC), with weekly volumes shaped into a realistic arc. It contains **no real usernames, emails, phone numbers, PAN/Aadhaar, account or folio numbers**, and both `src/build_reviews.py` and `scripts/inject_data.py` run a regex PII guard that aborts if any such pattern appears. Swap in your own public export for a live pulse — the pipeline is unchanged.

## Constraints honored
- **Public review exports only** — no scraping behind logins.
- **No PII** in any artifact (dashboard, CSV, note, email).
- **≤ 5 themes**; the note shows the **top 3** by priority.
- **Note ≤ 250 words** (currently 241; enforced in CI).

> Educational prototype. Not affiliated with INDmoney, Apple, or Google.
