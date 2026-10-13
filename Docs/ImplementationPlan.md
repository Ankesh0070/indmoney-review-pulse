# Implementation Plan: INDmoney Mutual Fund FAQ Assistant

**Project Code**: PROJECT-INDMONEY-MF-FAQ
**Document Version**: 1.0.0
**Derived From**: [Architecture.md](Architecture.md)
**Status**: Phases 0–6 complete (this is a retrospective build log, not a forward estimate — the assistant is already functional and tested)

---

## Table of Contents

1. [Phase Overview](#phase-overview)
2. [Phase 0 — Scoping & Corpus Authoring](#phase-0--scoping--corpus-authoring)
3. [Phase 1 — Answer Engine & Routing Logic](#phase-1--answer-engine--routing-logic)
4. [Phase 2 — Chat UI (Single-File Prototype)](#phase-2--chat-ui-single-file-prototype)
5. [Phase 3 — Manual QA & Bug-Fix Passes (v2 / v3)](#phase-3--manual-qa--bug-fix-passes-v2--v3)
6. [Phase 4 — Visual & UX Polish Pass](#phase-4--visual--ux-polish-pass)
7. [Phase 5 — Multi-File Restructuring](#phase-5--multi-file-restructuring)
8. [Phase 6 — Verification & Testing](#phase-6--verification--testing)
9. [Technology Stack Summary](#technology-stack-summary)
10. [Risk Register & Mitigations](#risk-register--mitigations)
11. [Future Phases (Not Started)](#future-phases-not-started)

---

## Phase Overview

| Phase | Name | Status | Key Deliverable |
|-------|------|--------|-----------------|
| **0** | Scoping & Corpus Authoring | ✅ Complete | 4 schemes, 8 fact types, 22 verified sources (`data/sources.csv`) |
| **1** | Answer Engine & Routing Logic | ✅ Complete | `window.MFFAQ.answer()` — fixed-order PII/advice/performance/statement/fact router |
| **2** | Chat UI (single-file prototype) | ✅ Complete | Working `index.html` — bubbles, composer, light/dark theme, typing indicator |
| **3** | Manual QA & bug-fix passes | ✅ Complete | 17 fixes (v2: #1–#10, v3: #11–#17) — see §3 below |
| **4** | Visual & UX polish pass | ✅ Complete | Avatar, timestamps, entrance animation, gradient wash, scroll-to-latest button |
| **5** | Multi-file restructuring | ✅ Complete | Split into `css/styles.css`, `js/corpus.js`, `js/engine.js`, `js/ui.js` |
| **6** | Verification & testing | ✅ Complete | Console logic sweep (10 query types) + live browser click-through, 2 themes |

---

## Phase 0 — Scoping & Corpus Authoring

### Objective
Pick a narrow, defensible scope — one AMC, four schemes, a fixed set of fact types — and hand-verify every fact against its official source before any code is written.

### Tasks

| # | Task | Output |
|---|------|--------|
| 0.1 | Choose product theme (INDmoney) and AMC (HDFC Mutual Fund) | README §Scope |
| 0.2 | Select 4 schemes covering distinct categories (Large Cap, Flexi Cap, Mid Cap, ELSS) so lock-in/tax rules differ meaningfully | `js/corpus.js` → `SCHEMES` |
| 0.3 | Define 8 fact types: expense ratio, exit load, entry load, minimum SIP, lock-in, riskometer, benchmark, category | `js/corpus.js` → `fact()` switch in engine |
| 0.4 | Collect and verify 22 official source URLs (AMC scheme pages, CAMS, KFintech, MF Central, AMFI, SEBI) | `data/sources.csv` |
| 0.5 | Write the facts-only disclaimer (short pill, footer line, full About-screen text) | `data/disclaimer.md` |
| 0.6 | Decide the "why no live TER number" policy — link out instead of quoting a volatile figure | README §5, ProblemStatement §5 |

### Exit Criteria
- [x] Every scheme has a name, category, benchmark, min-SIP, and source URL
- [x] Every source URL in `sources.csv` is marked verified (`yes`/`partial`)
- [x] Disclaimer text exists in both UI-pill and full-screen form

---

## Phase 1 — Answer Engine & Routing Logic

### Objective
Build the deterministic router described in [Architecture.md §3](Architecture.md#3-routing-order-the-core-design-decision) — PII guard first, then comparison/advice/performance guards, then statement detection, then fact lookup.

### Tasks

| # | Task | Output |
|---|------|--------|
| 1.1 | PII regex set: PAN, Aadhaar, email, phone, 11–18 digit account/folio, "OTP" | `hasPII()` |
| 1.2 | Scheme detection returning an array (not just first match), to support comparison detection | `detectSchemes()` |
| 1.3 | Fact detection returning an ordered, de-duplicated array, to support multi-fact answers | `detectFacts()` |
| 1.4 | Statement-vs-tax-question disambiguation | `detectStatement()` |
| 1.5 | Advice/suitability regex (good/bad/best/recommend/should-I/superlatives) | `ADVICE` |
| 1.6 | Performance/returns regex (CAGR, "how much will I earn", NAV prediction) | `PERF` |
| 1.7 | Fact generator — one `switch` branch per fact type, ELSS-specific exceptions for exit load and lock-in | `fact(scheme, type)` |
| 1.8 | Core router assembling all of the above in fixed order | `answer(raw)` |
| 1.9 | Expose a console-testable API | `window.MFFAQ = { answer, fact, detectScheme, detectSchemes, detectFacts, hasPII }` |

### Exit Criteria
- [x] `MFFAQ.answer("exit load of HDFC Mid Cap Fund")` returns the correct fact + citation
- [x] `MFFAQ.hasPII("my PAN is ABCDE1234F")` → `true`
- [x] A PII-containing message never reaches fact lookup, regardless of what else it asks

---

## Phase 2 — Chat UI (Single-File Prototype)

### Objective
Ship a working, presentable chat interface fast as a single `index.html` (inline `<style>` + `<script>`), to validate the engine end-to-end before investing in polish or restructuring.

### Tasks

| # | Task | Output |
|---|------|--------|
| 2.1 | Top bar with logo, brand, theme toggle | `.topbar` |
| 2.2 | Scrollable message list, chat-bubble layout (user right/violet, bot left/neutral) | `.messages`, `.bubble` |
| 2.3 | Refusal styling distinct from normal answers (amber, bordered) | `.msg.bot.refuse` |
| 2.4 | Source citation chip + "Last updated from sources" stamp | `.src`, `.updated` |
| 2.5 | Suggestion chips (3 canned questions), hidden after first message | `.chip`, `#suggestions` |
| 2.6 | Composer: input + send button + Enter-to-send + debounce guard | `#q`, `#sendBtn`, `ask()` |
| 2.7 | Typing indicator (3-dot animation, synthetic 450ms delay) | `.typing .dot` |
| 2.8 | Light/dark theme via CSS custom properties, persisted to `localStorage` | `:root`, `data-theme` |

### Exit Criteria
- [x] All 4 schemes × 8 facts answerable through the UI
- [x] Theme toggle persists across reload
- [x] Suggestion chips correctly trigger `ask()`

---

## Phase 3 — Manual QA & Bug-Fix Passes (v2 / v3)

### Objective
Stress-test the regex-based router against ambiguous and adversarial phrasing, and fix what breaks. This phase's fixes are preserved as comments directly in `js/engine.js` (FIX LOG) for future maintainers.

### v2 fixes (10)
| # | Bug | Fix |
|---|-----|-----|
| 1 | `fact()` had no safe default branch | Added a "which fact would you like?" default |
| 2 | `PERF` regex over-matched | Narrowed to explicit return/CAGR/profit language |
| 3 | `\bload\b` alone false-matched unrelated sentences | Dropped the bare-word rule |
| 4 | `start.*sip` over-matched | Dropped in favour of the `min(imum)? sip` pattern |
| 5 | No entry-load fact type existed | Added `entry_load` case + concept fallback |
| 6 | `\bflexi\b` needed a dedicated word-boundary rule | Added to `detectSchemes()` |
| 7 | Dark mode had no notice/contrast pass | Dark theme tokens introduced |
| 8 | Default system font looked generic | Switched to Inter via Google Fonts |
| 9 | Welcome message felt too verbose on load | Collapsed intro copy |
| 10 | Rapid double-submit via Enter + click | Added a 300ms `sending` debounce guard |

### v3 fixes (7)
| # | Bug | Fix |
|---|-----|-----|
| 11 | "good/bad" advice language only matched at sentence start | Now matches anywhere in the sentence |
| 12 | "which fund is cheapest/highest" wasn't recognised as a comparison | Superlative + fund/scheme/expense/return → comparison refusal |
| 13 | Multi-fact questions (e.g. "exit load and lock-in") only answered the first fact | `detectFacts()` returns *all* matches; router composes one paragraph per fact |
| 14 | "HDFC Flexi Cap vs HDFC Mid Cap" fell through to a single-scheme fact answer | 2+ schemes + vs/compare/better → explicit comparison refusal |
| 15 | "how is capital gains **tax** calculated" was mis-routed to the statement-download guide | `detectStatement()` now excludes tax-calculation phrasing |
| 16 | No generic answer existed for benchmark/min-SIP/category asked without a scheme | Added fallback entries to `CONCEPTS` |
| 17 | PII account-number rule flagged short numeric codes (9+ digits) as false positives | Tightened to 11–18 digits (realistic folio/account length) |

### Exit Criteria
- [x] All 17 fixes verified against the specific phrasing that triggered them (see `data/sample_qa.md` item 12 for the "I will return later" regression test)

---

## Phase 4 — Visual & UX Polish Pass

### Objective
Elevate the working prototype from functional to production-feeling without changing any answer logic.

### Tasks

| # | Task | Output |
|---|------|--------|
| 4.1 | Bot avatar badge (violet, amber on refusals) next to every bot message | `.avatar` |
| 4.2 | Per-message timestamps | `.time`, `timeLabel()` |
| 4.3 | Message entrance animation (fade + slide) | `@keyframes msgIn` |
| 4.4 | Source-citation chip rewritten to wrap instead of mid-domain-truncate | `.src span { overflow-wrap: anywhere }` |
| 4.5 | "New messages" jump button, driven by a live scroll listener (not message-timing heuristics — see Phase 4 bug below) | `.scroll-btn`, `nearBottom()` |
| 4.6 | Subtle radial-gradient background wash, composer focus ring, button micro-interactions | `--bg-wash`, `.composer-inner:focus-within` |
| 4.7 | Tab favicon (inline SVG data URI, no extra asset file) | `<link rel="icon">` |

### Bug caught during this phase
An initial version of the "jump to latest" button computed visibility from a `wasNearBottom` snapshot taken *before* a reply was appended, racing against the browser's scroll-position reflow after the synthetic typing delay — it could strand a new reply below the fold with no visible indicator. Fixed by decoupling the button entirely from message-send timing: it now toggles purely off a live `scroll` event listener on the chat container. See [EdgeCases.md §UI](EdgeCases.md#ui--rendering).

---

## Phase 5 — Multi-File Restructuring

### Objective
Split the single `index.html` prototype into a maintainable project without changing behaviour, so content (`corpus.js`), logic (`engine.js`), and rendering (`ui.js`) can be edited independently.

### Tasks

| # | Task | Output |
|---|------|--------|
| 5.1 | Extract `<style>` block | `css/styles.css` |
| 5.2 | Extract `window.MFFAQ_DATA` | `js/corpus.js` |
| 5.3 | Extract routing/answer logic, wrap in an IIFE to avoid polluting globals, expose `LAST_UPDATED` on the public API | `js/engine.js` |
| 5.4 | Extract DOM wiring, read `LAST_UPDATED` from `window.MFFAQ` instead of a shared script scope | `js/ui.js` |
| 5.5 | Reduce `index.html` to markup + `<link>`/`<script src>` tags only | `index.html` |
| 5.6 | Update `README.md` to document the new file layout and dependency direction | `README.md` |

### Exit Criteria
- [x] Byte-for-byte identical answer behaviour before and after the split (verified in Phase 6)
- [x] No global-scope leakage from `engine.js` beyond the intended `window.MFFAQ` object

---

## Phase 6 — Verification & Testing

### Objective
Confirm the restructured, polished assistant behaves identically to the validated prototype, by actually running it — not just reading the code.

### Tasks

| # | Task | Method |
|---|------|--------|
| 6.1 | Static file server (no bundler, matches the "no build step" README claim) | `npx serve .` |
| 6.2 | Console error check on load | `read_console_messages` → 0 errors |
| 6.3 | Logic sweep across 10 representative query types (fact, multi-fact, advice, performance, PII, comparison, statement, no-scheme concept, gibberish, the v2 "return" regression) | `MFFAQ.answer(q)` for each, diffed against expected output |
| 6.4 | Live UI click-through: type a real question, send, verify bubble/citation/timestamp render | Browser automation |
| 6.5 | Theme toggle verified in both light and dark | Screenshot comparison |

### Exit Criteria
- [x] 0 console errors
- [x] All 10 sweep queries match expected routing and copy
- [x] Visual click-through confirms rendering matches the pre-restructure prototype

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Markup** | Plain HTML5 | `index.html` — structure only |
| **Styling** | Plain CSS3 (custom properties for theming) | `css/styles.css` |
| **Logic** | Vanilla JavaScript (ES6+, no framework) | `js/corpus.js`, `js/engine.js`, `js/ui.js` |
| **Font** | Google Fonts (Inter) | Loaded via `@import` in CSS |
| **Persistence** | `localStorage` | Theme preference only — no user data stored |
| **Hosting** | Any static file host (GitHub Pages, `file://`, or a local static server for development) | No backend, no database, no API keys |
| **Testing** | Manual console sweep + browser click-through | No automated test framework yet (see Future Phases) |

---

## Risk Register & Mitigations

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| R1 | **Stale source links** (AMC/registrar restructures its site) | 🟠 High | `data/sources.csv` tracks verification status per URL; periodic manual re-check recommended (no automated link checker yet) |
| R2 | **Regex false positives/negatives on novel phrasing** | 🟡 Medium | Deterministic matching degrades gracefully to a clarifying question rather than guessing — see [EdgeCases.md](EdgeCases.md) |
| R3 | **TER/NAV/riskometer go stale** (these change monthly) | 🟡 Medium | By design, the engine never caches these numbers — it always links to the live official page instead |
| R4 | **PII regex over/under-matching** | 🟠 High | Already tuned once (v3 fix #17 narrowed account-number matching); any further tuning needs a regression test against `data/sample_qa.md` |
| R5 | **No automated regression suite** | 🟡 Medium | Console sweep in Phase 6 is manual; promoting it to a scripted test (e.g. a plain Node script asserting on `MFFAQ.answer()`) is listed under Future Phases |

---

## Future Phases (Not Started)

These are explicitly **out of scope** for the current build and are listed here only for roadmap clarity — none of the implemented phases above depend on them.

| Phase | Name | Notes |
|-------|------|-------|
| 7 | Automated regression test script | Promote the Phase 6 manual console sweep into a scripted `node test.js` asserting on `MFFAQ.answer()` outputs |
| 8 | Live TER/NAV fetch (optional) | Would require a backend proxy (CORS) to read AMC pages server-side — changes the "no backend" architecture decision and needs its own ADR |
| 9 | Embeddings-based retrieval upgrade | Only worth doing if the corpus grows beyond a size where keyword rules stay maintainable — see ProblemStatement §5 for why this was deliberately deferred |
| 10 | CI pipeline (lint/format check on `js/*.js`) | Not yet set up; low priority given the project has no build step |
| 11 | GitHub Pages deployment | README already documents the steps; not yet executed for this specific copy of the project |
