/* ===========================================================
   INDmoney MF FAQ Assistant — CORPUS (data layer)
   -----------------------------------------------------------
   Small, hand-verified corpus. Every fact below was checked
   against the OFFICIAL page bound to it (see data/sources.csv).
   Keep this file as the single source of truth for content;
   the engine (js/engine.js) only reads from it.
   Last verified: 23 Jun 2026
   =========================================================== */

window.MFFAQ_DATA = (function () {
  const LAST_UPDATED = "23 Jun 2026";

  /* Official source URLs (verified during build) */
  const SRC = {
    largecap:  "https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct",
    flexicap:  "https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct",
    elss:      "https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver/direct",
    midcap:    "https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/direct",
    capgains:  "https://www.camsonline.com/Investors/Statements/Capital-Gain&Capital-Loss-statement",
    cas:       "https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement",
    factsheet: "https://www.hdfcfund.com/statutory-disclosure/downloads",
    amfi:      "https://www.amfiindia.com/investor-corner/investor-center/investor-education.html",
    sebi:      "https://investor.sebi.gov.in/"
  };

  /* Scheme registry (the 4 schemes in scope) */
  const SCHEMES = {
    largecap: { name:"HDFC Large Cap Fund (formerly HDFC Top 100 Fund)", cat:"Large Cap", bench:"NIFTY 100 TRI", minsip:"₹100", src:SRC.largecap },
    flexicap: { name:"HDFC Flexi Cap Fund", cat:"Flexi Cap", bench:"NIFTY 500 TRI", minsip:"₹100", src:SRC.flexicap },
    midcap:   { name:"HDFC Mid Cap Fund (formerly HDFC Mid-Cap Opportunities Fund)", cat:"Mid Cap", bench:"NIFTY Midcap 150 TRI", minsip:"₹100", src:SRC.midcap },
    elss:     { name:"HDFC ELSS Tax Saver", cat:"ELSS (tax-saving)", bench:"NIFTY 500 TRI", minsip:"₹500", src:SRC.elss }
  };

  /* Generic concept facts (used when no scheme is named) */
  const CONCEPTS = {
    exit_load:    { a:"An exit load is a fee charged when you redeem or switch out units before a specified period (commonly 1% within 1 year). Entry loads are not permitted in India.", src:SRC.amfi, srcLabel:"AMFI — Investor Education" },
    expense_ratio:{ a:"The Total Expense Ratio (TER) is the annual cost of running a scheme, shown as a percentage of average net assets and capped under SEBI limits. Direct plans have a lower TER than Regular plans.", src:SRC.amfi, srcLabel:"AMFI — Investor Education" },
    lock_in:      { a:"A lock-in period is a fixed duration during which units cannot be redeemed. ELSS (tax-saving) funds have a statutory 3-year lock-in.", src:SRC.amfi, srcLabel:"AMFI — Investor Education" },
    riskometer:   { a:"The riskometer is a SEBI-mandated product label showing a scheme's risk on a six-level scale from Low to Very High. It is reviewed and disclosed monthly.", src:SRC.amfi, srcLabel:"AMFI — Investor Education" }
  };

  /* Statement guides */
  const STATEMENTS = {
    capgains: { a:"HDFC Mutual Fund is serviced by the registrar CAMS, so you can request a Capital Gain/Loss Statement (realised gains on a FIFO basis, split into short-term and long-term) from the official CAMS page. It is emailed to the address registered in your folio — you don't enter any PAN or details here.", src:SRC.capgains, srcLabel:"CAMS — Capital Gain/Loss Statement" },
    cas:      { a:"For a Consolidated Account Statement (CAS) covering holdings across all your fund houses, use the official CAMS/KFintech CAS service or MF Central. Requests are processed against your registered email/PAN on those official portals, not in this chat.", src:SRC.cas, srcLabel:"CAMS — Consolidated Account Statement" }
  };

  /* Refusals & redirects (safe, polite, each with an educational link) */
  const REFUSALS = {
    advice:      { refuse:true, a:"I can only share facts from official sources — I can't give buy / sell, \"is it good\", \"best fund\", or suitability opinions. For unbiased investor education, see SEBI's Investor portal or AMFI.", src:SRC.sebi, srcLabel:"SEBI Investor Education" },
    performance: { refuse:true, a:"I don't compute, predict or compare returns. Past performance and benchmark comparisons are published in the scheme's official factsheet — please refer to that.", src:SRC.factsheet, srcLabel:"HDFC MF — Factsheets & downloads" },
    pii:         { refuse:true, a:"For your safety I don't accept or store personal data such as PAN, Aadhaar, bank/account numbers, OTPs, email or phone numbers. Please remove those details — I can still answer general scheme facts.", src:SRC.sebi, srcLabel:"SEBI investor safety" }
  };

  return { LAST_UPDATED, SRC, SCHEMES, CONCEPTS, STATEMENTS, REFUSALS };
})();
