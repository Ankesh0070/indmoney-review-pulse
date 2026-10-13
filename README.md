# INDmoney · Mutual Fund FAQ Assistant (Facts-only)

**🔗 Live prototype: [ankesh0070.github.io/indmoney-review-pulse](https://ankesh0070.github.io/indmoney-review-pulse/)**

A small, citation-first FAQ assistant that answers **factual** questions about mutual fund schemes using **official public pages only**. Every answer carries exactly one source link. It refuses opinion/portfolio questions, redirects performance questions to the official factsheet, and never accepts personal data. Themed with INDmoney's violet identity, with a light/dark toggle.

Built for the LIP milestone *"Mutual Fund FAQs (Facts-Only Q&A)"*. Chosen product: **INDmoney**.

> ⚠️ Educational prototype. Not investment advice. Not affiliated with INDmoney, HDFC Mutual Fund, CAMS, AMFI or SEBI.

---

## Demo

No build, no dependencies, no server required — plain HTML/CSS/JS loaded as static files.

```bash
# Just open the file — that's it
open index.html            # macOS   (Windows: start index.html, Linux: xdg-open index.html)
```
Or double-click `index.html` in your file manager.

### Deploy free on GitHub Pages
1. Push this repo to GitHub.
2. **Settings → Pages → Build and deployment → Source: "Deploy from a branch"**, branch `main`, folder `/ (root)`.
3. Your assistant goes live at `https://<username>.github.io/<repo>/`.

---

## Repository structure

```
indmoney-mf-faq/
├── index.html            # markup only — loads css/ and js/
├── css/
│   └── styles.css        # theme tokens (light/dark), layout, chat bubbles, composer
├── js/
│   ├── corpus.js         # window.MFFAQ_DATA — the fact corpus + source URLs (edit content here)
│   ├── engine.js          # window.MFFAQ — routing/answer logic, reads only from corpus.js
│   └── ui.js               # DOM rendering, composer, theme toggle, reads only from window.MFFAQ
├── data/
│   ├── sources.csv       # 22 official URLs used, with the fact each covers
│   ├── sample_qa.md      # sample queries with answers + links
│   └── disclaimer.md     # the facts-only disclaimer shown in the UI
├── README.md
├── LICENSE               # MIT
└── .gitignore
```

Each JS file has one job and reads only from the layer below it: `ui.js` → `window.MFFAQ` (engine.js) → `window.MFFAQ_DATA` (corpus.js). To edit a fact or add a source, change `js/corpus.js` only — `engine.js` and `ui.js` never need to change for a content update.

## Scope

**Product / theme:** INDmoney · **AMC for the corpus:** HDFC Mutual Fund

| Scheme | Category | Benchmark | Min SIP | Exit load | Lock-in |
|---|---|---|---|---|---|
| HDFC Large Cap Fund (ex–Top 100) | Large Cap | NIFTY 100 TRI | ₹100 | 1% < 1 yr | None |
| HDFC Flexi Cap Fund | Flexi Cap | NIFTY 500 TRI | ₹100 | 1% < 1 yr | None |
| HDFC Mid Cap Fund (ex–Mid-Cap Opportunities) | Mid Cap | NIFTY Midcap 150 TRI | ₹100 | 1% < 1 yr | None |
| HDFC ELSS Tax Saver | ELSS | NIFTY 500 TRI | ₹500 | Nil | 3 yrs (statutory) |

**Fact types:** expense ratio (TER), exit load, minimum SIP, lock-in, riskometer, benchmark, category, and how to download capital-gains / consolidated statements.

**Sources:** AMC scheme pages (hdfcfund.com), the SEBI-registered registrar CAMS / KFintech, MF Central, AMFI and SEBI investor pages — full list in [`data/sources.csv`](data/sources.csv).

---

## How it works (W1–W3)

**W1 — Thinking like a model.** Each query is routed in a fixed order: (1) PII check → (2) advice/opinion → (3) performance/returns → (4) statement guides → (5) scheme + fact lookup. First match wins, so a risky query is caught before any fact is emitted. If the fact is clear but the scheme isn't (or vice-versa), it asks one clarifying question instead of guessing.

**W2 — Prompting / wording.** Answers are ≤3 sentences, plain active voice, no hedging. Refusals stay polite and always offer a relevant educational link. Every answer appends `Last updated from sources:` for transparency.

**W3 — RAG (small corpus).** Retrieval is deterministic keyword + intent matching over the structured corpus in `js/corpus.js`, each fact pre-bound to one official URL. Deterministic retrieval guarantees the citation is correct and rules out hallucinated numbers — which matters more than fluency for a facts-only tool.

**Why expense ratio links out instead of quoting a number.** TER changes monthly and differs between Direct and Regular plans; third-party sites disagreed widely during research (0.58%–1.46% for the same fund). Rather than risk a stale figure, the assistant points to the official scheme page / factsheet where the live TER is published. This also keeps the tool free of performance claims.

---

## Constraints honoured

- **Public sources only** — AMC / registrar / SEBI / AMFI pages; no app back-end, no third-party blogs as sources.
- **No PII** — PAN, Aadhaar, account numbers, OTPs, emails and phone numbers are detected and refused; nothing is stored or transmitted.
- **No performance claims** — does not compute or compare returns; redirects to the official factsheet.
- **Clarity** — answers ≤3 sentences, one citation each, "Last updated from sources" stamp.

---

## Quick test in the browser console

The engine is exposed as `window.MFFAQ`:

```js
MFFAQ.answer("exit load of HDFC Mid Cap Fund");   // -> {a, src, srcLabel}
MFFAQ.answer("should I buy HDFC Flexi Cap?");     // -> refusal (advice)
MFFAQ.hasPII("my PAN is ABCDE1234F");             // -> true
```

---

## Known limits

- Corpus is intentionally small (4 schemes, ~8 fact types). Out-of-scope queries return a help prompt, not a guess.
- No live data: TER, NAV and riskometer can change; those route to the official page rather than caching numbers. The `Last updated from sources` date is when sources were last checked (23 Jun 2026).
- Matching is keyword/intent based, not embeddings — robust for listed phrasings, degrades to a clarifying question on unusual wording.
- Statements are not generated here — it only links to the official CAMS/KFintech/MF Central flows, which run their own identity checks (by design, since those need PII the assistant won't touch).
- Some regulator/industry links are cited at their official landing pages; deep-link paths on those sites change over time.
- **Not investment advice. Facts only.**

---

## License

[MIT](LICENSE).
