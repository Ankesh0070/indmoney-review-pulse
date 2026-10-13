# Edge Cases & Failure Scenarios: INDmoney Mutual Fund FAQ Assistant

**Project Code**: PROJECT-INDMONEY-MF-FAQ
**Document Version**: 1.0.0

This document lists edge cases the assistant has actually encountered (and in most cases already fixed — see the FIX LOG in `js/engine.js`), organised by the layer they belong to. Each entry includes the triggering input, the impact if unhandled, and the mitigation in place today. Entries marked **[OPEN]** are known gaps, not yet mitigated.

---

## 1. PII Guard

### 1.1 Short numeric codes mis-flagged as account numbers
**Scenario**: Early versions of the account-number regex matched any 9+ digit run, which caught things like scheme codes or amounts that were not actually PII.
**Impact**: Legitimate factual questions containing a long number got refused as if they contained personal data — a false-positive refusal is almost as damaging to trust as a false-negative leak.
**Mitigation (FIX #17)**: Tightened the rule to 11–18 digits, matching realistic Indian folio/bank account number lengths. Short codes no longer trigger it.

### 1.2 PAN-shaped text that isn't actually a PAN
**Scenario**: The PAN regex (`[A-Za-z]{5}\d{4}[A-Za-z]`) is a shape match, not a checksum validator — any 5-letters/4-digits/1-letter token will match, including a coincidental one in an unrelated sentence.
**Impact [OPEN]**: A small risk of over-refusing on text that merely has PAN-shaped structure. Accepted as a deliberate trade-off — for a facts-only assistant, refusing a borderline-ambiguous input is the safe failure direction, not the dangerous one.
**Mitigation**: None planned; this is intentionally conservative.

### 1.3 PII check runs before anything else
**Scenario**: A message could simultaneously contain a PAN number *and* a scheme name *and* advice-seeking language (e.g. "my PAN is ABCDE1234F, should I buy HDFC Flexi Cap?").
**Impact if mis-ordered**: If advice detection ran first, the assistant would discuss investment suitability in the same breath as processing a PAN number.
**Mitigation**: `hasPII(t)` is the very first check in `answer()` — see [Architecture.md §3](Architecture.md#3-routing-order-the-core-design-decision). No other routing logic can execute once PII is detected.

---

## 2. Scheme & Fact Detection

### 2.1 The word "return" inside an unrelated sentence
**Scenario**: *"What is the lock-in for ELSS? I will return later"* — the word "return" is part of ordinary conversational phrasing, not a performance question.
**Impact**: Early version routed this to the performance refusal, blocking a perfectly valid lock-in question.
**Mitigation (FIX #2, confirmed in `data/sample_qa.md` item 12)**: The `PERF` regex was narrowed from a bare `\breturn\b` match to explicit patterns (`\breturns\b`, `return on`, `return from`, `how much will/would/can I earn`, etc.) that don't fire on casual use of the word "return".

### 2.2 "Capital gains tax" vs. "capital gains statement"
**Scenario**: *"How is capital gains tax calculated on HDFC ELSS?"* vs. *"How do I download my capital gains statement?"* — both contain "capital gains" but need completely different answers (one is out of scope entirely, the other is a registrar link).
**Impact**: A naive keyword match on "capital gain" alone would route a tax-calculation question to the statement-download guide, which doesn't answer the actual question asked.
**Mitigation (FIX #15)**: `detectStatement()` runs a separate `isTaxQ` check first (tax/taxed/taxation/LTCG/STCG + calculate/how/rate/treat/much) and skips the statement route if it matches.

### 2.3 Two schemes named without comparison intent
**Scenario**: *"exit load and lock-in of HDFC ELSS Tax Saver"* mentions only one scheme, but a question like *"what's the benchmark, HDFC Flexi Cap or HDFC Mid Cap"* names two.
**Impact**: Not every multi-scheme mention is a comparison request — the comparison refusal must not fire just because two scheme names appear.
**Mitigation (FIX #14)**: Comparison refusal requires **both** 2+ scheme matches **and** an explicit comparison cue (`vs`, `versus`, `compare`, `comparison`, `better`, `between`, or bare `or`). Two schemes named without any of those words falls through to the first-scheme fact lookup instead.

### 2.4 Multiple facts asked about one scheme
**Scenario**: *"exit load and lock-in of HDFC ELSS Tax Saver"* asks for two distinct facts in one message.
**Impact**: Early version's `fact()` call only ever received the first detected fact id, silently dropping the second question.
**Mitigation (FIX #13)**: `detectFacts()` returns every matched fact id (de-duplicated, in rule order); the router composes one paragraph per fact when 2+ are detected, with de-duplicated source chips in the UI (see [Architecture.md §4](Architecture.md#4-data-flow-example)).

### 2.5 ELSS has no exit load but does have a lock-in — the inverse is true for the other three schemes
**Scenario**: Asking "exit load of HDFC ELSS Tax Saver" needs a *different shaped answer* than asking the same question about any other scheme, because ELSS substitutes a statutory lock-in for an exit load entirely.
**Impact**: A single generic exit-load template would either wrongly claim ELSS has an exit load, or wrongly claim the other three schemes have a lock-in.
**Mitigation**: `fact()` branches explicitly on `scheme === "elss"` inside both the `exit_load` and `lock_in` cases, rather than trying to force one template to cover both shapes.

---

## 3. Advice / Comparison / Performance Guards

### 3.1 Advice language buried mid-sentence
**Scenario**: *"I've heard mixed things, is HDFC Flexi Cap actually a good fund for someone my age?"* — the advice-triggering phrase isn't at the start of the sentence.
**Impact**: An anchored regex (`^is it good`) would miss this and let it fall through to a fact answer that doesn't address what was actually asked (a suitability opinion).
**Mitigation (FIX #11)**: `ADVICE` matches "good/bad/wise/right/safe/reasonable" + a following noun (fund/choice/option/investment/etc.) **anywhere** in the string, not just at the start.

### 3.2 Superlative-based comparison without an explicit "vs"
**Scenario**: *"which fund has the lowest expense ratio"* — no scheme-vs-scheme comparison cue, but it's still implicitly asking the assistant to rank/compare.
**Impact**: Without specific handling, this could slip past both the advice guard and the 2-scheme comparison guard (since zero or one scheme is named) and get treated as an ordinary fact question.
**Mitigation (FIX #12)**: `ADVICE` includes a superlative pattern (`lowest/highest/cheapest/best/worst/top` + `fund/scheme/expense/ratio/return`) that catches this independent of how many schemes are named.

### 3.3 "Good" used about the expense ratio, not the fund itself
**Scenario**: *"Is the expense ratio of HDFC Mid Cap Fund good or too high?"* — the opinion word is attached to a specific metric, not the fund as a whole.
**Impact**: A pattern anchored only to "good fund" would miss "good expense ratio" and let through what is still a suitability/opinion question.
**Mitigation (FIX #11, extended)**: `ADVICE` also matches `(expense ratio|ter|fee) (good|bad|high|low|reasonable|cheap|expensive)` and the reverse word order, specifically for cost-related opinion framing.

---

## 4. Statement Guides

### 4.1 Statement requests never collect PII, by design
**Scenario**: A user might expect to type their folio number or email directly into the chat to "get" their statement faster.
**Impact**: If the assistant accepted that, it would be storing/transmitting exactly the kind of personal data it's designed to refuse.
**Mitigation**: Statement answers (`STATEMENTS.capgains`, `STATEMENTS.cas`) only ever explain *that* CAMS/KFintech/MF Central handle the identity-checked request on their own official portal — the assistant never asks for or accepts the PAN/email/folio itself. (If the user pastes it anyway, the PII guard in §1 catches it before this code path is even reached.)

### 4.2 CAS (cross-fund-house) vs. single-AMC capital-gains statement
**Scenario**: "consolidated account statement" and "capital gains statement" are different documents from different (sometimes overlapping) registrar flows.
**Impact**: Conflating them would send a user looking for a CAS to the wrong CAMS page.
**Mitigation**: `detectStatement()` keeps them as two distinct statement ids (`statement_capgains` vs `statement_cas`) with two distinct corpus entries and source URLs.

---

## 5. UI / Rendering

### 5.1 "New messages" button racing against message-send timing **(caught during Phase 4 polish, fixed)**
**Scenario**: An early implementation computed the jump-to-latest button's visibility from a `wasNearBottom` flag captured *before* a reply was rendered, intended to detect "was the user already reading old messages when this reply arrived." In practice, because every reply in this app is a direct response to the user's own just-sent message (which already force-scrolls to bottom), the snapshot timing was fragile and could show the button — or fail to reveal a new reply — inconsistently depending on reflow timing around the synthetic typing-indicator removal.
**Impact**: A new reply could render below the fold with the jump button not appearing, effectively hiding the answer from the user who just asked the question.
**Mitigation**: Decoupled the button entirely from send/receive timing. `addBot()` now always scrolls to the newest message unconditionally (correct, because the bot never speaks except in direct response to the user's own message). The button is instead driven purely by a live `scroll` event listener on `#chat`, checking actual current scroll position — correct by construction, with no timing assumptions. See [ImplementationPlan.md Phase 4](ImplementationPlan.md#phase-4--visual--ux-polish-pass).

### 5.2 Source-citation chip truncating mid-domain-name
**Scenario**: On narrow viewports, a long `srcLabel + hostname` string (e.g. "SEBI Investor Education · investor.sebi.gov.in") would hit `text-overflow: ellipsis` with `white-space: nowrap`, cutting the hostname to something like "investor.s…" — losing the information the citation exists to provide.
**Impact**: Defeats the purpose of showing a verifiable source domain at a glance.
**Mitigation**: Replaced the nowrap/ellipsis rule with `overflow-wrap: anywhere`, letting the chip wrap to two lines instead of losing text.

### 5.3 Empty or whitespace-only input
**Scenario**: User presses Enter or clicks send with an empty or whitespace-only composer.
**Impact**: Without a guard, this would add an empty user bubble and trigger a confusing "please type a question" bot reply for no visible input.
**Mitigation**: `ask()` checks `text.trim()` is non-empty before doing anything, silently no-op-ing on empty submissions.

### 5.4 Rapid double-submit (Enter + click, or double-Enter)
**Scenario**: A fast double-press of Enter, or pressing Enter and then immediately clicking Send before the first message finishes its 450ms typing-indicator delay.
**Impact**: Without a guard, two near-simultaneous `ask()` calls could interleave typing indicators or duplicate a message.
**Mitigation (FIX #10)**: A `sending` boolean guard with a 300ms cooldown blocks re-entrant `ask()` calls.

---

## 6. Data Freshness (accepted limitation, not a bug)

### 6.1 Expense ratio (TER), NAV, and riskometer classification all change over time
**Scenario**: TER is published monthly and differs between Direct/Regular plans; the riskometer is reviewed monthly; NAV changes daily.
**Impact if cached**: Any number baked into the static corpus would go stale within weeks and could actively mislead a user relying on it for a real decision.
**Mitigation**: These fact types deliberately **never return a cached number** — `fact(scheme, "expense_ratio")` and `fact(scheme, "riskometer")` always point to the live official page instead of quoting a figure. The `LAST_UPDATED` stamp ("Last updated from sources: 23 Jun 2026") tells the user when the *source links themselves* were last checked, not when any number was last correct — this distinction is intentional and documented in the README's "Known limits" section.

### 6.2 Source link rot **[OPEN]**
**Scenario**: AMC or registrar websites restructure their URLs (as `data/sources.csv` already notes for 2 entries marked `partial` rather than fully `yes`-verified).
**Impact**: A citation link could 404 if the target page moves.
**Mitigation**: None automated yet. `data/sources.csv`'s `verified_in_build` column exists specifically so a periodic manual re-check has a checklist to work from — see [ImplementationPlan.md Risk R1](ImplementationPlan.md#risk-register--mitigations).
