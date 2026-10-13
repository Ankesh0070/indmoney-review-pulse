/* ===========================================================
   INDmoney MF FAQ Assistant — ANSWER ENGINE
   -----------------------------------------------------------
   Reads facts from window.MFFAQ_DATA (js/corpus.js).
   Routing order (first match wins):
     1) PII guard  2) comparison/advice  3) performance/returns
     4) statement guides  5) scheme(s) x fact(s) lookup
   Every factual answer returns one official citation per fact.
   Exposes window.MFFAQ for the UI layer (js/ui.js) and for
   console/unit testing.

   FIX LOG
   v2: #1 fact() default · #2 PERF narrowed · #3 drop \bload\b ·
       #4 drop start.*sip · #5 entry_load · #6 \bflexi\b ·
       #7 dark notice · #8 Inter font · #9 collapse intro · #10 debounce
   v3: #11 advice "good/bad" anywhere in sentence (not just start)
       #12 "which fund lowest/highest/cheapest" = comparison refusal
       #13 MULTI-FACT: answer every fact asked, not just the first
       #14 MULTI-SCHEME / "compare X and Y": refuse comparison politely
       #15 "capital gains TAX" routes to tax info, not statement download
       #16 added CONCEPTS for benchmark, min_sip, category, riskometer-already
       #17 PII account rule tightened to >=11 digits (was 9, caught codes)
   =========================================================== */

(function () {
  const { LAST_UPDATED, SRC, SCHEMES, CONCEPTS, STATEMENTS, REFUSALS } = window.MFFAQ_DATA;

  /* ---- Fact generator (answer <= 3 sentences, 1 source) ---- */
  function fact(scheme, type) {
    const s = SCHEMES[scheme];
    switch (type) {
      case "expense_ratio":
        return { a:`The Total Expense Ratio (TER) of ${s.name} changes monthly and is lower for the Direct plan than the Regular plan, so the live figure is published on the official scheme page and the monthly factsheet. Please open the official page below for the current TER.`, src:s.src, srcLabel:"Official scheme page" };
      case "exit_load":
        if (scheme === "elss")
          return { a:`${s.name} does not levy an exit load. Instead, being an ELSS, it carries a statutory 3-year lock-in during which units cannot be redeemed.`, src:s.src, srcLabel:"Official scheme page" };
        return { a:`${s.name} charges an exit load of 1% if units are redeemed or switched out within 1 year of allotment, and Nil after 1 year. No entry load applies (entry loads are not permitted in India).`, src:s.src, srcLabel:"Official scheme page" };
      case "entry_load":
        return { a:`Entry loads are not permitted in India (SEBI banned them in 2009). ${s.name} does not charge any entry load.`, src:s.src, srcLabel:"Official scheme page" };
      case "min_sip":
        return { a:`The minimum SIP / application amount for ${s.name} is ${s.minsip} (additional purchases are also ${s.minsip}).`, src:s.src, srcLabel:"Official scheme page" };
      case "lock_in":
        if (scheme === "elss")
          return { a:`${s.name} has a statutory lock-in of 3 years from the date of allotment; each SIP instalment is locked for 3 years from its own date. Investments are eligible for deduction up to ₹1.5 lakh under Section 80C (old tax regime).`, src:s.src, srcLabel:"Official scheme page" };
        return { a:`${s.name} is an open-ended scheme with no lock-in — units can be redeemed on any business day. An exit load may apply if redeemed within 1 year.`, src:s.src, srcLabel:"Official scheme page" };
      case "riskometer":
        return { a:`${s.name} is classified as "Very High" risk on its product riskometer (per SEBI's product-labelling norms). The live riskometer image is shown on the official scheme page.`, src:s.src, srcLabel:"Official scheme page" };
      case "benchmark":
        return { a:`${s.name} is benchmarked against the ${s.bench}.`, src:s.src, srcLabel:"Official scheme page" };
      case "category":
        return { a:`${s.name} is an open-ended equity scheme in the ${s.cat} category.`, src:s.src, srcLabel:"Official scheme page" };
      default:
        return { a:`I can look up expense ratio, exit load, minimum SIP, lock-in, riskometer and benchmark for ${s.name}. Which one would you like?`, src:s.src, srcLabel:"Official scheme page" };
    }
  }

  /* ---- PII detection ---- */
  const PII = [
    { re:/\b[A-Za-z]{5}\d{4}[A-Za-z]\b/, t:"PAN" },
    { re:/\b\d{4}\s?\d{4}\s?\d{4}\b/, t:"Aadhaar" },
    { re:/\b[\w.+-]+@[\w-]+\.[\w.-]+\b/, t:"email" },
    { re:/\b(?:\+91[\-\s]?)?[6-9]\d{9}\b/, t:"phone" },
    { re:/\b\d{11,18}\b/, t:"account" },        /* FIX #17: 11+ digits (folio/account); short codes no longer flagged */
    { re:/\botp\b/i, t:"OTP" }
  ];
  function hasPII(t){ return PII.some(p => p.re.test(t)); }

  /* ---- Scheme detection: returns an ARRAY of matched scheme ids (FIX #14) ---- */
  function detectSchemes(t){
    const out = [];
    if (/\b(elss|tax\s*saver|taxsaver|80c|tax[-\s]?sav)/i.test(t)) out.push("elss");
    if (/\bflexi\b/i.test(t)) out.push("flexicap");
    if (/\b(mid[-\s]?cap|midcap|opportunit)/i.test(t)) out.push("midcap");
    if (/\b(large[-\s]?cap|largecap|top\s*100|top100)/i.test(t)) out.push("largecap");
    return out;
  }
  function detectScheme(t){ return detectSchemes(t)[0] || null; }  /* kept for back-compat / tests */

  /* ---- Fact detection: returns an ORDERED, de-duped ARRAY of fact ids (FIX #13) ---- */
  const FACT_RULES = [
    ["expense_ratio", /(expense|\bter\b|cost of (the )?fund|management fee)/i],
    ["entry_load",    /\bentry\s*load/i],
    ["exit_load",     /(exit\s*load|redeem.*(charge|fee|early))/i],
    ["lock_in",       /(lock[-\s]?in|lockin)/i],
    ["riskometer",    /(riskomet|risk\s*level|how\s*risky|risk\s*rating)/i],
    ["benchmark",     /(benchmark|index.*(track|against)|tracked against|compared.*index)/i],
    ["min_sip",       /(min(imum)?\s*(sip|investment|amount)|sip\s*amount|smallest\s*sip)/i],
    ["category",      /(category|what type of fund|what kind of fund)/i]
  ];
  function detectFacts(t){
    const out = [];
    for (const [id, re] of FACT_RULES) if (re.test(t)) out.push(id);
    return out;
  }

  /* ---- Statement detection (separated from tax questions) ---- */
  function detectStatement(t){
    /* FIX #15: a tax/calculation question is NOT a "download statement" request */
    const isTaxQ = /(tax|taxed|taxation|ltcg|stcg).*(calculat|how|rate|treat|much)|how.*(tax|taxed)/i.test(t);
    if (/(capital[-\s]?gain|cap\s*gain|gains?\s*statement)/i.test(t) && !isTaxQ) return "statement_capgains";
    if (/\btax\s*statement\b/i.test(t)) return "statement_capgains";
    if (/(consolidated|cas\b|account\s*statement|download.*statement|statement.*download|get.*statement)/i.test(t)) return "statement_cas";
    return null;
  }

  /* ---- Advice / comparison / performance detection ---- */
  /* FIX #11: "good/bad/worth/suitable" anywhere; FIX #12: superlatives = comparison */
  const ADVICE = /(should i|should we|is it (a )?(good|bad|wise|smart|safe)|\b(good|bad|wise|right|safe|low|high|reasonable) (fund|choice|option|idea|investment|for|enough|or)|worth (it|buying|investing)|better (than|fund|option)|best (fund|scheme|option)|which (fund|scheme|one).*(better|best|good|buy|cheap|low|high)|\b(lowest|highest|cheapest|best|worst|top)\b.*(fund|scheme|expense|ratio|return)|recommend|suggest|buy or sell|shall i (buy|invest)|do you (suggest|recommend|think)|safe to invest|will it (grow|rise|fall|do well)|invest now|is .* (a )?good (fund|investment|choice)|(expense ratio|ter|fee) (good|bad|high|low|reasonable|cheap|expensive)|(good|bad|high|low|reasonable|cheap|expensive) (expense|ter|ratio|fee))/i;
  const PERF = /(\breturns\b|\breturn on\b|\breturn from\b|cagr|how much (will|would|can) i (earn|get|make)|profit|past performance|compare.*returns|nav (today|tomorrow|will)|future value|how much.*grow|outperform)/i;

  /* ---- Generic concepts (FIX #16: fill the gaps) ---- */
  CONCEPTS.entry_load = CONCEPTS.entry_load || { a:"Entry loads are not permitted in India — SEBI banned them in 2009. No mutual fund scheme charges an entry load.", src:SRC.amfi, srcLabel:"AMFI — Investor Education" };
  CONCEPTS.benchmark  = { a:"A benchmark is a market index a scheme is measured against (for example NIFTY 100 TRI or NIFTY 500 TRI). It shows whether the fund tracks, beats or lags the market — name a scheme and I'll give its benchmark.", src:SRC.amfi, srcLabel:"AMFI — Investor Education" };
  CONCEPTS.min_sip    = { a:"The minimum SIP is the smallest amount you can invest per instalment; it is set by each scheme (commonly ₹100–₹500). Name a scheme and I'll give its exact minimum.", src:SRC.amfi, srcLabel:"AMFI — Investor Education" };
  CONCEPTS.category   = { a:"Mutual fund categories (large-cap, flexi-cap, mid-cap, ELSS, etc.) are defined by SEBI based on where the scheme invests. Name a scheme and I'll give its category.", src:SRC.sebi, srcLabel:"SEBI — Investor Education" };

  /* ---- Helpers for multi-answer composition ---- */
  function uniq(arr){ return [...new Set(arr)]; }

  /* ---- Core router ---- */
  function answer(raw){
    const t = (raw || "").trim();
    if (!t) return { a:"Please type a factual question about one of the four covered schemes.", src:null };

    if (hasPII(t)) return REFUSALS.pii;

    const schemes = detectSchemes(t);
    const facts = detectFacts(t);

    /* FIX #14: two-or-more schemes + a "compare/vs" cue = comparison → refuse politely */
    if (schemes.length >= 2 && /\b(vs\.?|versus|compare|comparison|or|better|between)\b/i.test(t)) {
      return { refuse:true, a:`I give facts one scheme at a time and don't compare or rank funds. Ask me about a single scheme — e.g. "${facts[0] ? facts[0].replace('_',' ') : 'exit load'} of ${SCHEMES[schemes[0]].name.split(' (')[0]}".`, src:SRC.amfi, srcLabel:"AMFI — Investor Education" };
    }

    if (ADVICE.test(t)) return REFUSALS.advice;
    if (PERF.test(t))   return REFUSALS.performance;

    /* statements (after advice/perf, before fact lookup) */
    const stmt = detectStatement(t);
    if (stmt === "statement_capgains") return STATEMENTS.capgains;
    if (stmt === "statement_cas")      return STATEMENTS.cas;

    const sc = schemes[0] || null;

    /* FIX #13: multiple facts for one scheme → compose one reply per fact, sources listed */
    if (sc && facts.length >= 2) {
      const parts = uniq(facts).map(f => fact(sc, f));
      const a = parts.map(p => p.a).join("\n\n");
      return { a, multi:parts, src:SCHEMES[sc].src, srcLabel:"Official scheme page" };
    }

    if (sc && facts.length === 1) return fact(sc, facts[0]);

    if (sc && facts.length === 0) {
      const s = SCHEMES[sc];
      return { a:`For ${s.name} I can give facts on: expense ratio, exit load, minimum SIP, lock-in, riskometer and benchmark. Which one would you like? (Benchmark: ${s.bench}.)`, src:s.src, srcLabel:"Official scheme page" };
    }

    /* no scheme named */
    if (!sc && facts.length >= 1) {
      const f = facts[0];
      if (CONCEPTS[f]) return CONCEPTS[f];
      return { a:`Sure — which scheme? I cover HDFC Large Cap, HDFC Flexi Cap, HDFC Mid Cap and HDFC ELSS Tax Saver. For example: "minimum SIP of HDFC ELSS Tax Saver".`, src:null };
    }

    return { a:`I answer facts about four HDFC schemes — expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, and how to download statements. Try: "exit load of HDFC Mid Cap Fund" or "ELSS lock-in".`, src:null };
  }

  /* Expose the engine for the UI layer, console testing, and reuse */
  window.MFFAQ = { answer, fact, detectScheme, detectSchemes, detectFacts, hasPII, LAST_UPDATED };
})();
