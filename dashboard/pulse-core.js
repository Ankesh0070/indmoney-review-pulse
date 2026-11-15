/* pulse-core.js - browser/Node twin of src/pulse.py.
   Pure functions, no DOM. Inlined into index.html at build time (see scripts/inject_data.py)
   and loaded by tests/parity.js, which asserts it matches the Python output. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.PulseCore = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";
  const DEFAULT_WEIGHTS = [0.50, 0.35, 0.15], MAX_WEEKS = 12;
  const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const rhu = x => Math.floor(x + 0.5);
  const r2 = x => rhu(x * 100) / 100;
  const sentiment = r => r <= 2 ? "neg" : (r >= 4 ? "pos" : "neu");
  const pad = n => String(n).padStart(2, "0");

  // ---- config
  function prepare(cfg) {
    const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    cfg.themes.forEach(t => {
      t._rx = t.keywords.map(k => {
        k = k.toLowerCase().trim();
        const exact = k.endsWith("$"); if (exact) k = k.replace(/\$+$/, "");
        return [new RegExp("\\b" + esc(k).replace(/\s+/g, "\\s+") + (exact ? "\\b" : "")), k.includes(" ") ? 2 : 1];
      });
    });
    cfg._stop = new Set(cfg.stopwords);
    return cfg;
  }

  // ---- PII redaction (same order as REDACTIONS in pulse.py)
  const REDACTIONS = [
    [/[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g, "[email]"],
    [/https?:\/\/\S+/g, "[link]"],
    [/\b[A-Z]{5}\d{4}[A-Z]\b/g, "[pan]"],
    [/\b(?:folio|a\/c|acc|account)\s*(?:no\.?|number)?\s*[:#]?\s*\d{4,}/gi, "[account]"],
    [/\b\d{4}\s\d{4}\s\d{4}\b/g, "[id]"],
    [/(?:\+?91[\s-]?)?\b[6-9]\d{9}\b/g, "[phone]"],
    [/\b\d{9,18}\b/g, "[number]"],
    [/@\w{3,}/g, "[handle]"],
  ];
  function redact(text) {
    let hits = 0;
    for (const [rx, tag] of REDACTIONS) text = text.replace(rx, () => { hits++; return tag; });
    return [text, hits];
  }

  function classify(text, cfg) {
    const low = text.toLowerCase();
    let best = null, bestS = 0;
    for (const t of cfg.themes) {
      let s = 0; for (const [rx, w] of t._rx) if (rx.test(low)) s += w;
      if (s > bestS) { best = t.name; bestS = s; }
    }
    return best;
  }

  // ---- CSV
  function parseCSV(text) {
    if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
    const rows = []; let row = [], f = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c;
      } else if (c === '"') q = true;
      else if (c === ",") { row.push(f); f = ""; }
      else if (c === "\n" || c === "\r") { if (c === "\r" && text[i + 1] === "\n") i++; row.push(f); rows.push(row); row = []; f = ""; }
      else f += c;
    }
    if (f !== "" || row.length) { row.push(f); rows.push(row); }
    const head = (rows.shift() || []).map(h => h.trim());
    return rows.filter(r => r.some(x => x.trim() !== "")).map(r => Object.fromEntries(head.map((h, i) => [h, r[i] === undefined ? "" : r[i]])));
  }
  const csvCell = v => { v = String(v == null ? "" : v); return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
  const COLUMNS = ["review_id","date","week","source","rating","title","text","theme"];
  const toCSV = rows => [COLUMNS.join(",")].concat(rows.map(r => COLUMNS.map(c => csvCell(r[c])).join(","))).join("\n") + "\n";

  // ---- dates / weeks (UTC math, Monday-start weeks)
  function parseDate(s) {
    s = String(s).trim(); let m;
    if ((m = s.match(/^(\d{4})-(\d{2})-(\d{2})/))) return Date.UTC(+m[1], +m[2] - 1, +m[3]);
    if ((m = s.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})/))) return Date.UTC(+m[3], +m[2] - 1, +m[1]);
    if ((m = s.match(/^(\d{4})\/(\d{1,2})\/(\d{1,2})/))) return Date.UTC(+m[1], +m[2] - 1, +m[3]);
    const t = Date.parse(s); if (isNaN(t)) return null;
    const d = new Date(t); return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate());
  }
  const DAY = 86400000;
  const weekStart = ms => ms - ((new Date(ms).getUTCDay() + 6) % 7) * DAY;
  const iso = ms => { const d = new Date(ms); return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate()); };
  const weekLabel = ws => { const a = new Date(ws), b = new Date(ws + 6 * DAY); return MON[a.getUTCMonth()] + " " + pad(a.getUTCDate()) + "-" + pad(b.getUTCDate()); };

  // ---- import / normalise
  const HEADERS = {
    date: ["date","review date","at","submitted","last updated","review submit date and time","created","review last update date and time"],
    rating: ["rating","star rating","score","stars"],
    text: ["text","review text","content","body","review","review body"],
    title: ["title","review title","subject","review summary"],
    source: ["source","store","platform"], theme: ["theme"], id: ["review_id","id","review id"],
  };
  function pick(row, field) {
    const low = {}; for (const k in row) low[k.trim().toLowerCase()] = row[k];
    for (const h of HEADERS[field]) if (h in low && String(low[h]).trim() !== "") return String(low[h]).trim();
    return "";
  }
  function normalise(raw, cfg, opts) {
    opts = opts || {}; const defSrc = opts.defaultSource || "Unknown", keep = opts.keepTheme !== false;
    const rep = { in: 0, redactions: 0, unclassified: 0, auto_themed: 0, dropped: 0 }, out = [], seen = new Set();
    const valid = new Set(cfg.themes.map(t => t.name));
    for (const r of raw) {
      rep.in++;
      const ms = parseDate(pick(r, "date")); const rating = Math.round(parseFloat(pick(r, "rating")));
      let text = pick(r, "text"), title = pick(r, "title");
      if (ms === null || !(rating >= 1 && rating <= 5) || (!text && !title)) { rep.dropped++; continue; }
      const id = pick(r, "id"); if (id) { if (seen.has(id)) { rep.dropped++; continue; } seen.add(id); }
      let h; [title, h] = redact(title); rep.redactions += h; [text, h] = redact(text); rep.redactions += h;
      let theme = keep ? pick(r, "theme") : "";
      if (!valid.has(theme)) { theme = classify(title + " " + text, cfg) || ""; rep.auto_themed++; }
      if (!theme) rep.unclassified++;
      out.push({ review_id: id || "R" + String(out.length + 1).padStart(5, "0"), date: iso(ms), week: weekLabel(weekStart(ms)),
        source: pick(r, "source") || defSrc, rating, title, text, theme });
    }
    out.sort((a, b) => a.date < b.date ? -1 : a.date > b.date ? 1 : (a.review_id < b.review_id ? -1 : a.review_id > b.review_id ? 1 : 0));
    rep.out = out.length; return [out, rep];
  }

  // ---- analysis
  function terms(text, stop) {
    const toks = text.toLowerCase().match(/[a-z']+/g) || [];
    const set = new Set(); const ok = t => t.length >= 3 && !stop.has(t);
    toks.forEach(t => ok(t) && set.add(t));
    for (let i = 0; i + 1 < toks.length; i++) if (ok(toks[i]) && ok(toks[i + 1])) set.add(toks[i] + " " + toks[i + 1]);
    return set;
  }
  function trending(cur, base, stop, k) {
    k = k || 6; if (!cur.length || !base.length) return [];
    const count = rows => { const m = new Map(); rows.forEach(r => terms(r.title + " " + r.text, stop).forEach(t => m.set(t, (m.get(t) || 0) + 1))); return m; };
    const cc = count(cur), bc = count(base), cand = [];
    cc.forEach((c, t) => {
      if (c < 2) return; const b = bc.get(t) || 0;
      const lift = ((c + 1) / (cur.length + 2)) / ((b + 1) / (base.length + 2));
      if (lift >= 1.2) cand.push([c * Math.log(lift), t, c, b, lift]);
    });
    cand.sort((x, y) => y[0] - x[0] || (x[1] < y[1] ? -1 : x[1] > y[1] ? 1 : 0));
    const chosen = [];
    for (const [, t, c, b, lift] of cand) {
      if (!t.includes(" ") && cand.some(o => o[1].includes(" ") && o[1].split(" ").includes(t) && o[2] === c)) continue;
      chosen.push({ term: t, count: c, base: b, lift: r2(lift) }); if (chosen.length === k) break;
    }
    return chosen;
  }
  function signals(names, ts, avgCur, avgPrev, nPrev, nCur, pi) {
    const sig = [];
    for (const t of names) {
      const cs = ts[t].counts, ng = ts[t].negPct, cur = cs[pi], base = cs.slice(Math.max(0, pi - 8), pi);
      if (base.length >= 3 && cur >= 3) {
        const mean = base.reduce((a, b) => a + b, 0) / base.length;
        const sd = Math.sqrt(base.reduce((a, b) => a + (b - mean) ** 2, 0) / base.length);
        const z = (cur - mean) / Math.max(sd, 0.75);
        if (z >= 1.5) sig.push({ type: "spike", severity: z >= 2.5 ? "high" : "medium", theme: t,
          text: `${t}: ${cur} mentions vs ~${mean.toFixed(1)} typical (${z.toFixed(1)} sigma above)` });
      }
      if (pi >= 2 && [pi - 2, pi - 1, pi].every(i => cs[i] >= 2 && ng[i] >= 75))
        sig.push({ type: "sustained", severity: "medium", theme: t, text: `${t}: 75%+ negative for 3 straight weeks` });
      if (pi >= 4 && cs[pi] >= 2 && cs[pi - 4] >= 2 && ng[pi - 4] - ng[pi] >= 20)
        sig.push({ type: "improving", severity: "good", theme: t, text: `${t}: negativity down ${ng[pi - 4] - ng[pi]} pts vs 4 weeks ago` });
    }
    if (pi >= 1 && nCur && nPrev) {
      const d = r2(avgCur - avgPrev);
      if (d <= -0.3) sig.push({ type: "rating_drop", severity: "medium", theme: "", text: `Average rating fell ${Math.abs(d).toFixed(2)} week over week` });
      else if (d >= 0.3) sig.push({ type: "rating_gain", severity: "good", theme: "", text: `Average rating rose ${d.toFixed(2)} week over week` });
    }
    const rank = { high: 0, medium: 1, good: 2 };
    return sig.sort((a, b) => rank[a.severity] - rank[b.severity]).slice(0, 6);
  }

  function analyze(allRows, cfg, o) {
    o = o || {}; const weights = o.weights || DEFAULT_WEIGHTS, source = o.source || "All", maxW = o.maxWeeks || MAX_WEEKS;
    const names = cfg.themes.map(t => t.name), actions = Object.fromEntries(cfg.themes.map(t => [t.name, t.action]));
    if (!allRows.length) return null;
    const ws = allRows.map(r => weekStart(parseDate(r.date)));
    let lo = Math.min(...ws), hi = Math.max(...ws);
    let nW = Math.round((hi - lo) / (7 * DAY)) + 1;
    if (nW > maxW) { lo = hi - 7 * DAY * (maxW - 1); nW = maxW; }
    const starts = Array.from({ length: nW }, (_, i) => lo + 7 * DAY * i), labels = starts.map(weekLabel);
    const idx = new Map(starts.map((s, i) => [s, i]));
    const rows = allRows.map((r, i) => Object.assign({}, r, { _wi: idx.has(ws[i]) ? idx.get(ws[i]) : -1 })).filter(r => r._wi >= 0);
    const sources = [...new Set(rows.map(r => r.source))].sort();
    const view = rows.filter(r => source === "All" || r.source === source);
    const byW = Array.from({ length: nW }, () => []); view.forEach(r => byW[r._wi].push(r));
    let pi = o.week ? labels.indexOf(o.week) : nW - 1; if (pi < 0) pi = nW - 1;
    const prevI = pi > 0 ? pi - 1 : null;

    const st = items => {
      const n = items.length; if (!n) return { n: 0, avg: null, negPct: 0 };
      const neg = items.filter(i => sentiment(i.rating) === "neg").length;
      return { n, avg: r2(items.reduce((s, i) => s + i.rating, 0) / n), negPct: rhu(100 * neg / n) };
    };
    const tw = {}, ts = {};
    names.forEach(t => { tw[t] = byW.map(w => w.filter(r => r.theme === t)); ts[t] = { counts: tw[t].map(x => x.length), negPct: tw[t].map(x => st(x).negPct) }; });
    const cur = byW[pi], prev = prevI !== null ? byW[prevI] : [], Sc = st(cur), Sp = st(prev);
    const delta = r2((Sc.avg || 0) - (Sp.avg !== null ? Sp.avg : (Sc.avg || 0))) + 0;
    const cc = {}, pc = {}; names.forEach(t => { cc[t] = ts[t].counts[pi]; pc[t] = prevI !== null ? ts[t].counts[prevI] : 0; });
    const maxc = Math.max(1, ...Object.values(cc));
    const wsum = weights.reduce((a, b) => a + b, 0) || 1, [wn, wv, wm] = weights.map(w => w / wsum);
    const info = {};
    names.forEach(t => {
      const s = st(tw[t][pi]), mom = cc[t] - pc[t], vol = 100 * cc[t] / maxc, momS = Math.max(0, Math.min(100, 50 + mom * 9));
      info[t] = { theme: t, priority: rhu(wn * s.negPct + wv * vol + wm * momS), count: cc[t], prev: pc[t], wow: mom, avg: s.avg !== null ? s.avg : 0, negPct: s.negPct };
    });
    const ranked = names.slice().sort((a, b) => info[b].priority - info[a].priority || names.indexOf(a) - names.indexOf(b));
    const top = ranked.filter(t => cc[t] > 0).slice(0, 3);
    const lead = top.length ? top[0] : ranked[0], li = info[lead];
    const mover = names.reduce((a, b) => info[b].wow > info[a].wow ? b : a), faller = names.reduce((a, b) => info[b].wow < info[a].wow ? b : a);
    let headline = `${lead} is the week's top priority (${li.count} mentions, ${li.negPct}% negative` + (li.wow > 0 ? `, up ${li.wow} WoW` : "") + ").";
    if (info[mover].wow >= 2 && mover !== lead) headline += ` ${mover} is rising fastest (+${info[mover].wow} WoW).`;
    if (info[faller].wow <= -2) headline += ` ${faller} is easing (${info[faller].wow} WoW).`;
    const quote = t => {
      const c = tw[t][pi].slice().sort((a, b) => a.rating - b.rating || a.text.length - b.text.length)[0];
      let tx = c.text; if (tx.length > 140) tx = tx.slice(0, 137).replace(/\s+\S*$/, "") + "...";
      return { text: tx, rating: c.rating, source: c.source, theme: t };
    };
    const baseNeg = []; for (let w = Math.max(0, pi - 4); w < pi; w++) byW[w].forEach(r => sentiment(r.rating) === "neg" && baseNeg.push(r));
    const curNeg = cur.filter(r => sentiment(r.rating) === "neg");
    const srcCount = {}; cur.forEach(r => srcCount[r.source] = (srcCount[r.source] || 0) + 1);
    return {
      pulse_week: labels[pi], prev_week: prevI !== null ? labels[prevI] : null, year: new Date(starts[pi] + 6 * DAY).getUTCFullYear(),
      weeks: labels, source, sources, weights: weights.map(w => w / wsum), _pi: pi,
      kpi: { n: Sc.n, avg: Sc.avg || 0, avg_prev: Sp.avg !== null ? Sp.avg : (Sc.avg || 0), delta, negPct: Sc.negPct, src: srcCount, unclassified: cur.filter(r => !r.theme).length },
      headline, top_themes: top.map(t => info[t]), all_priorities: ranked.map(t => info[t]), trend: ts,
      pulse_avg: byW.map(w => st(w).avg), pulse_neg: byW.map(w => st(w).negPct), pulse_vol: byW.map(w => w.length),
      rating_dist: [1, 2, 3, 4, 5].map(k => cur.filter(r => r.rating === k).length),
      quotes: top.map(quote), actions: top.map(t => actions[t]),
      signals: signals(names, ts, Sc.avg || 0, Sp.avg || 0, Sp.n, Sc.n, pi),
      trending: trending(curNeg, baseNeg, cfg._stop),
      _byTheme: tw, _cur: cur, _byW: byW,
    };
  }

  // ---- note + email (mirror build_note / build_email in pulse.py)
  const words = s => (s.match(/\b\w+\b/g) || []).length;
  const arrow = d => d > 0 ? "▲" : (d < 0 ? "▼" : "=");
  const sgn = (d, n) => (d >= 0 ? "+" : "-") + Math.abs(d).toFixed(n);
  function buildNote(p, nSig, shortFooter) {
    const k = p.kpi, d = k.delta;
    const md = ["# INDmoney — Weekly Review Pulse",
      `**Week of ${p.pulse_week}, ${p.year}** · ${k.n} reviews · avg ${k.avg.toFixed(2)} ${arrow(d)} (${sgn(d, 2)} WoW) · ${k.negPct}% negative\n`,
      `**Headline.** ${p.headline}\n`];
    const sig = p.signals.slice(0, nSig);
    if (sig.length) { md.push("## Signals"); sig.forEach(s => md.push("- " + s.text)); md.push(""); }
    md.push("## Top 3 themes");
    p.top_themes.forEach((t, i) => md.push(`${i + 1}. **${t.theme}** — priority ${t.priority}/100 · ${t.count} mentions (${t.wow > 0 ? "+" + t.wow : t.wow} WoW) · avg ${t.avg.toFixed(2)}★ · ${t.negPct}% negative`));
    md.push(""); md.push("## In users' words");
    p.quotes.forEach(q => md.push(`> "${q.text}" — ${q.rating}★, ${q.source} · *${q.theme}*`));
    md.push(""); md.push("## Three action ideas");
    p.actions.forEach((a, i) => md.push(`${i + 1}. ${a}`));
    md.push(""); md.push("---");
    md.push(shortFooter ? "*Public review exports, no PII.*" : "*Source: public App Store + Play Store review exports (redacted sample, 12-week window). No PII. Max 5 themes; ranked by priority score.*");
    return md.join("\n");
  }
  function fitNote(p, limit) {
    limit = limit || 250; let note;
    for (const [n, s] of [[2, false], [2, true], [1, true], [0, true]]) { note = buildNote(p, n, s); if (words(note) <= limit) return note; }
    return note;
  }
  function buildEmail(p) {
    const k = p.kpi, d = k.delta;
    const subj = `INDmoney Weekly Review Pulse — ${p.pulse_week} (avg ${k.avg.toFixed(2)}${arrow(d)}, ${k.negPct}% neg)`;
    const L = ["Hi team,", "", `This week's INDmoney review pulse (${p.pulse_week}, ${p.year})${p.source !== "All" ? " — " + p.source + " only" : ""}, from public App Store + Play Store reviews.`,
      `${k.n} reviews, avg ${k.avg.toFixed(2)} (${sgn(d, 2)} WoW), ${k.negPct}% negative.`, "", "HEADLINE", p.headline, ""];
    if (p.signals.length) { L.push("SIGNALS"); p.signals.forEach(s => L.push("- " + s.text)); L.push(""); }
    L.push("TOP 3 THEMES (by priority = negativity x volume x momentum)");
    p.top_themes.forEach((t, i) => L.push(`${i + 1}. ${t.theme} — priority ${t.priority}/100, ${t.count} mentions, ${t.negPct}% neg`));
    L.push("", "WHAT USERS SAID"); p.quotes.forEach(q => L.push(`- "${q.text}" (${q.rating}*, ${q.source})`));
    if (p.trending.length) L.push("", "TRENDING IN COMPLAINTS", p.trending.map(x => x.term).join(", "));
    L.push("", "THREE ACTION IDEAS"); p.actions.forEach((a, i) => L.push(`${i + 1}. ${a}`));
    L.push("", "One-pager (PDF) and source CSV attached. No PII included.", "", "— Auto-generated by Review Pulse");
    return { subject: subj, body: L.join("\n") };
  }

  return { prepare, redact, classify, parseCSV, toCSV, normalise, analyze, fitNote, buildNote, buildEmail, words, COLUMNS, DEFAULT_WEIGHTS };
});
