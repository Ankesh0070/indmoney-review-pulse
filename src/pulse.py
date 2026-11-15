#!/usr/bin/env python3
"""
pulse.py - shared core of the Review Pulse pipeline (v3).

Everything numeric lives here: PII redaction, theme classification, weekly stats,
priority scoring, signals (spike / sustained / improving detection) and trending
phrases. The browser dashboard re-implements the exact same logic in
dashboard/pulse-core.js; tests/parity.js asserts the two agree on every number.

Rounding note: Python's round() is banker's rounding, JS Math.round() is
half-up. We use rhu() (round half up) everywhere so both runtimes match.
"""
import csv, json, math, re, datetime, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEMES_PATH = ROOT / "data" / "themes.json"
DEFAULT_WEIGHTS = (0.50, 0.35, 0.15)   # negativity, volume, momentum
MAX_WEEKS = 12

# ----------------------------------------------------------------- helpers
def rhu(x):            # round half up -> int
    return int(math.floor(x + 0.5))

def r2(x):             # round half up to 2 dp
    return rhu(x * 100) / 100.0

def sentiment(rating):
    return "neg" if rating <= 2 else ("pos" if rating >= 4 else "neu")

def load_config(path=THEMES_PATH):
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for t in cfg["themes"]:
        t["_rx"] = [(_kw_rx(k), 2 if " " in k.strip() else 1) for k in t["keywords"]]
    cfg["_stop"] = set(cfg["stopwords"])
    return cfg

def _kw_rx(kw):
    kw = kw.lower().strip()
    exact = kw.endswith("$")
    kw = kw.rstrip("$")
    pat = r"\b" + re.escape(kw).replace(r"\ ", r"\s+")
    if exact:
        pat += r"\b"
    return re.compile(pat)

# ----------------------------------------------------------------- PII redaction
# Order matters. Mirrors REDACTIONS in dashboard/pulse-core.js.
REDACTIONS = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[email]"),
    (re.compile(r"https?://\S+"), "[link]"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "[pan]"),
    (re.compile(r"\b(?:folio|a/c|acc|account)\s*(?:no\.?|number)?\s*[:#]?\s*\d{4,}", re.I), "[account]"),
    (re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"), "[id]"),
    (re.compile(r"(?:\+?91[\s-]?)?\b[6-9]\d{9}\b"), "[phone]"),
    (re.compile(r"\b\d{9,18}\b"), "[number]"),
    (re.compile(r"@\w{3,}"), "[handle]"),
]

def redact(text):
    hits = 0
    for rx, tag in REDACTIONS:
        text, n = rx.subn(tag, text)
        hits += n
    return text, hits

# ----------------------------------------------------------------- classification
def classify(text, cfg):
    low = text.lower()
    best, best_s = None, 0
    for t in cfg["themes"]:
        s = sum(w for rx, w in t["_rx"] if rx.search(low))
        if s > best_s:
            best, best_s = t["name"], s
    return best

# ----------------------------------------------------------------- dates / weeks
_FMTS = ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y")

def parse_date(s):
    s = str(s).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime.date(int(m[1]), int(m[2]), int(m[3]))
    for f in _FMTS:
        try:
            return datetime.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None

def week_start(d):
    return d - datetime.timedelta(days=d.weekday())      # Monday

def week_label(start):
    end = start + datetime.timedelta(days=6)
    return f"{start:%b %d}-{end:%d}"

# ----------------------------------------------------------------- import / normalise
HEADERS = {
    "date":   ["date", "review date", "at", "submitted", "last updated", "review submit date and time", "created", "review last update date and time"],
    "rating": ["rating", "star rating", "score", "stars"],
    "text":   ["text", "review text", "content", "body", "review", "review body"],
    "title":  ["title", "review title", "subject", "review summary"],
    "source": ["source", "store", "platform"],
    "theme":  ["theme"],
    "id":     ["review_id", "id", "review id"],
}

def _pick(row, field):
    lower = {k.strip().lower(): v for k, v in row.items() if k}
    for h in HEADERS[field]:
        if h in lower and str(lower[h]).strip() != "":
            return str(lower[h]).strip()
    return ""

def normalise(raw_rows, cfg, default_source="Unknown", keep_theme=True):
    """Raw dicts (any common export layout) -> clean, redacted, themed rows + report."""
    rep = collections.Counter()
    out, seen = [], set()
    for raw in raw_rows:
        rep["in"] += 1
        d = parse_date(_pick(raw, "date"))
        try:
            rating = int(round(float(_pick(raw, "rating"))))
        except ValueError:
            rating = 0
        text = _pick(raw, "text")
        if d is None:
            rep["dropped_no_date"] += 1; continue
        if not 1 <= rating <= 5:
            rep["dropped_no_rating"] += 1; continue
        if not text and not _pick(raw, "title"):
            rep["dropped_empty"] += 1; continue
        rid = _pick(raw, "id")
        if rid:
            if rid in seen:
                rep["dropped_duplicate_id"] += 1; continue
            seen.add(rid)
        title, h1 = redact(_pick(raw, "title"))
        text, h2 = redact(text)
        rep["redactions"] += h1 + h2
        theme = _pick(raw, "theme") if keep_theme else ""
        valid = {t["name"] for t in cfg["themes"]}
        if theme not in valid:
            theme = classify(title + " " + text, cfg) or ""
            rep["auto_themed"] += 1
        if not theme:
            rep["unclassified"] += 1
        src = _pick(raw, "source") or default_source
        out.append({"review_id": rid or f"R{len(out)+1:05d}", "date": d.isoformat(),
                    "week": week_label(week_start(d)), "source": src, "rating": rating,
                    "title": title, "text": text, "theme": theme})
    out.sort(key=lambda r: (r["date"], r["review_id"]))
    rep["out"] = len(out)
    return out, dict(rep)

COLUMNS = ["review_id", "date", "week", "source", "rating", "title", "text", "theme"]

def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def load_rows(path, cfg):
    rows, _ = normalise(read_csv(path), cfg, default_source="App Store")
    return rows

# ----------------------------------------------------------------- analysis
def _terms(text, stop):
    toks = re.findall(r"[a-z']+", text.lower())
    ok = [t for t in toks if len(t) >= 3 and t not in stop]
    terms = set(ok)
    for a, b in zip(toks, toks[1:]):
        if len(a) >= 3 and len(b) >= 3 and a not in stop and b not in stop:
            terms.add(a + " " + b)
    return terms

def trending(cur_rows, base_rows, stop, k=6):
    if not base_rows or not cur_rows:
        return []
    cd = [_terms(r["title"] + " " + r["text"], stop) for r in cur_rows]
    bd = [_terms(r["title"] + " " + r["text"], stop) for r in base_rows]
    cc = collections.Counter(t for d in cd for t in d)
    bc = collections.Counter(t for d in bd for t in d)
    cand = []
    for t, c in cc.items():
        if c < 2:
            continue
        b = bc.get(t, 0)
        lift = ((c + 1) / (len(cd) + 2)) / ((b + 1) / (len(bd) + 2))
        if lift >= 1.2:
            cand.append((c * math.log(lift), t, c, b, lift))
    cand.sort(key=lambda x: (-x[0], x[1]))
    chosen = []
    for _, t, c, b, lift in cand:
        # a word is redundant if some phrase containing it appears in exactly as many reviews
        if " " not in t and any(" " in o[1] and t in o[1].split() and o[2] == c for o in cand):
            continue
        chosen.append({"term": t, "count": c, "base": b, "lift": r2(lift)})
        if len(chosen) == k:
            break
    return chosen

def _signals(themes, tstats, avg_cur, avg_prev, n_prev, n_cur, pi):
    sig = []
    for t in themes:
        cs = tstats[t]["counts"]
        cur = cs[pi]
        base = cs[max(0, pi - 8):pi]
        if len(base) >= 3 and cur >= 3:
            mean = sum(base) / len(base)
            sd = math.sqrt(sum((x - mean) ** 2 for x in base) / len(base))
            z = (cur - mean) / max(sd, 0.75)
            if z >= 1.5:
                sig.append({"type": "spike", "severity": "high" if z >= 2.5 else "medium", "theme": t,
                            "text": f"{t}: {cur} mentions vs ~{mean:.1f} typical ({z:.1f} sigma above)"})
        ns, ng = tstats[t]["counts"], tstats[t]["negPct"]
        if pi >= 2 and all(ns[i] >= 2 and ng[i] >= 75 for i in (pi - 2, pi - 1, pi)):
            sig.append({"type": "sustained", "severity": "medium", "theme": t,
                        "text": f"{t}: 75%+ negative for 3 straight weeks"})
        if pi >= 4 and ns[pi] >= 2 and ns[pi - 4] >= 2 and ng[pi - 4] - ng[pi] >= 20:
            sig.append({"type": "improving", "severity": "good", "theme": t,
                        "text": f"{t}: negativity down {ng[pi-4]-ng[pi]} pts vs 4 weeks ago"})
    if pi >= 1 and n_cur and n_prev:
        d = r2(avg_cur - avg_prev)
        if d <= -0.3:
            sig.append({"type": "rating_drop", "severity": "medium", "theme": "",
                        "text": f"Average rating fell {abs(d):.2f} week over week"})
        elif d >= 0.3:
            sig.append({"type": "rating_gain", "severity": "good", "theme": "",
                        "text": f"Average rating rose {d:.2f} week over week"})
    rank = {"high": 0, "medium": 1, "good": 2}
    sig.sort(key=lambda s: rank[s["severity"]])        # stable
    return sig[:6]

def analyze(rows, cfg, weights=DEFAULT_WEIGHTS, source="All", week=None, max_weeks=MAX_WEEKS):
    names = [t["name"] for t in cfg["themes"]]
    actions = {t["name"]: t["action"] for t in cfg["themes"]}
    if not rows:
        raise SystemExit("No reviews to analyse.")
    for r in rows:
        r["_ws"] = week_start(parse_date(r["date"]))
    lo, hi = min(r["_ws"] for r in rows), max(r["_ws"] for r in rows)
    n_weeks = (hi - lo).days // 7 + 1
    if n_weeks > max_weeks:
        lo = hi - datetime.timedelta(days=7 * (max_weeks - 1)); n_weeks = max_weeks
    starts = [lo + datetime.timedelta(days=7 * i) for i in range(n_weeks)]
    labels = [week_label(s) for s in starts]
    idx = {s: i for i, s in enumerate(starts)}
    rows = [r for r in rows if r["_ws"] in idx]
    sources = sorted({r["source"] for r in rows})
    view = [r for r in rows if source in (None, "All") or r["source"] == source]
    by_w = [[] for _ in starts]
    for r in view:
        by_w[idx[r["_ws"]]].append(r)
    pi = labels.index(week) if week else len(labels) - 1
    pi = max(pi, 0)
    prev_i = pi - 1 if pi > 0 else None

    def st(items):
        n = len(items)
        if not n:
            return {"n": 0, "avg": None, "negPct": 0}
        avg = r2(sum(i["rating"] for i in items) / n)
        neg = sum(1 for i in items if sentiment(i["rating"]) == "neg")
        return {"n": n, "avg": avg, "negPct": rhu(100 * neg / n)}

    tw = {t: [[r for r in by_w[w] if r["theme"] == t] for w in range(n_weeks)] for t in names}
    tstats = {t: {"counts": [len(x) for x in tw[t]], "negPct": [st(x)["negPct"] for x in tw[t]]} for t in names}
    cur, prev = by_w[pi], (by_w[prev_i] if prev_i is not None else [])
    Scur, Sprev = st(cur), st(prev)
    delta = r2((Scur["avg"] or 0) - (Sprev["avg"] if Sprev["avg"] is not None else (Scur["avg"] or 0))) + 0.0
    cc = {t: tstats[t]["counts"][pi] for t in names}
    pc = {t: (tstats[t]["counts"][prev_i] if prev_i is not None else 0) for t in names}
    maxc = max(max(cc.values()), 1)
    wsum = sum(weights) or 1
    wn, wv, wm = (w / wsum for w in weights)

    def prio(t):
        negPct = st(tw[t][pi])["negPct"]
        vol = 100 * cc[t] / maxc
        mom = cc[t] - pc[t]
        momS = max(0, min(100, 50 + mom * 9))
        return rhu(wn * negPct + wv * vol + wm * momS), mom, negPct

    info = {}
    for t in names:
        p, mom, negPct = prio(t)
        s = st(tw[t][pi])
        info[t] = {"theme": t, "priority": p, "count": cc[t], "prev": pc[t], "wow": mom,
                   "avg": s["avg"] if s["avg"] is not None else 0, "negPct": negPct}
    ranked = sorted(names, key=lambda t: (-info[t]["priority"], names.index(t)))
    top = [t for t in ranked if cc[t] > 0][:3]

    lead = top[0] if top else ranked[0]
    li = info[lead]
    mover = max(names, key=lambda t: info[t]["wow"])
    faller = min(names, key=lambda t: info[t]["wow"])
    headline = (f"{lead} is the week's top priority "
                f"({li['count']} mentions, {li['negPct']}% negative"
                + (f", up {li['wow']} WoW" if li["wow"] > 0 else "") + ").")
    if info[mover]["wow"] >= 2 and mover != lead:
        headline += f" {mover} is rising fastest (+{info[mover]['wow']} WoW)."
    if info[faller]["wow"] <= -2:
        headline += f" {faller} is easing ({info[faller]['wow']} WoW)."

    def quote(t):
        c = sorted(tw[t][pi], key=lambda r: (r["rating"], len(r["text"])))[0]
        tx = c["text"]
        if len(tx) > 140:
            tx = tx[:137].rsplit(" ", 1)[0] + "..."
        return {"text": tx, "rating": c["rating"], "source": c["source"], "theme": t}

    base_neg = [r for w in range(max(0, pi - 4), pi) for r in by_w[w] if sentiment(r["rating"]) == "neg"]
    cur_neg = [r for r in cur if sentiment(r["rating"]) == "neg"]
    dist = [sum(1 for r in cur if r["rating"] == k) for k in range(1, 6)]
    avg_series = [st(by_w[w])["avg"] for w in range(n_weeks)]
    return {
        "pulse_week": labels[pi], "prev_week": labels[prev_i] if prev_i is not None else None,
        "year": (starts[pi] + datetime.timedelta(days=6)).year,
        "weeks": labels, "source": source, "sources": sources,
        "weights": [round(wn, 4), round(wv, 4), round(wm, 4)],
        "kpi": {"n": Scur["n"], "avg": Scur["avg"] or 0, "avg_prev": Sprev["avg"] if Sprev["avg"] is not None else (Scur["avg"] or 0),
                "delta": delta, "negPct": Scur["negPct"],
                "src": dict(collections.Counter(r["source"] for r in cur)),
                "unclassified": sum(1 for r in cur if not r["theme"])},
        "headline": headline,
        "top_themes": [info[t] for t in top],
        "all_priorities": [info[t] for t in ranked],
        "trend": {t: tstats[t] for t in names},
        "pulse_avg": avg_series,
        "pulse_neg": [st(by_w[w])["negPct"] for w in range(n_weeks)],
        "pulse_vol": [len(by_w[w]) for w in range(n_weeks)],
        "rating_dist": dist,
        "quotes": [quote(t) for t in top],
        "actions": [actions[t] for t in top],
        "signals": _signals(names, tstats, Scur["avg"] or 0, Sprev["avg"] or 0, Sprev["n"], Scur["n"], pi),
        "trending": trending(cur_neg, base_neg, cfg["_stop"]),
    }

# ----------------------------------------------------------------- note + email
def count_words(s):
    return len(re.findall(r"\b\w+\b", s))

def _arrow(d):
    return "▲" if d > 0 else ("▼" if d < 0 else "=")

def build_note(p, n_signals=2, short_footer=False):
    k, d = p["kpi"], p["kpi"]["delta"]
    md = ["# INDmoney — Weekly Review Pulse",
          f"**Week of {p['pulse_week']}, {p['year']}** · {k['n']} reviews · "
          f"avg {k['avg']:.2f} {_arrow(d)} ({d:+.2f} WoW) · {k['negPct']}% negative\n",
          f"**Headline.** {p['headline']}\n"]
    sig = p["signals"][:n_signals]
    if sig:
        md.append("## Signals")
        md += [f"- {s['text']}" for s in sig]
        md.append("")
    md.append("## Top 3 themes")
    for i, t in enumerate(p["top_themes"], 1):
        w = f"+{t['wow']}" if t["wow"] > 0 else str(t["wow"])
        md.append(f"{i}. **{t['theme']}** — priority {t['priority']}/100 · {t['count']} mentions ({w} WoW) "
                  f"· avg {t['avg']:.2f}★ · {t['negPct']}% negative")
    md.append("")
    md.append("## In users' words")
    for q in p["quotes"]:
        md.append(f"> \"{q['text']}\" — {q['rating']}★, {q['source']} · *{q['theme']}*")
    md.append("")
    md.append("## Three action ideas")
    for i, a in enumerate(p["actions"], 1):
        md.append(f"{i}. {a}")
    md.append("")
    md.append("---")
    md.append("*Public review exports, no PII.*" if short_footer else
              "*Source: public App Store + Play Store review exports (redacted sample, 12-week window). No PII. Max 5 themes; ranked by priority score.*")
    return "\n".join(md)

def fit_note(p, limit=250):
    """Richest variant of the note that still fits the word budget."""
    for n, short in ((2, False), (2, True), (1, True), (0, True)):
        note = build_note(p, n, short)
        if count_words(note) <= limit:
            return note
    return note

def build_email(p):
    k, d = p["kpi"], p["kpi"]["delta"]
    subj = f"INDmoney Weekly Review Pulse — {p['pulse_week']} (avg {k['avg']:.2f}{_arrow(d)}, {k['negPct']}% neg)"
    lines = ["Hi team,", "",
             f"This week's INDmoney review pulse ({p['pulse_week']}, {p['year']}), from public App Store + Play Store reviews.",
             f"{k['n']} reviews, avg {k['avg']:.2f} ({d:+.2f} WoW), {k['negPct']}% negative.", "",
             "HEADLINE", p["headline"], ""]
    if p["signals"]:
        lines += ["SIGNALS"] + [f"- {s['text']}" for s in p["signals"]] + [""]
    lines += ["TOP 3 THEMES (by priority = negativity x volume x momentum)"]
    for i, t in enumerate(p["top_themes"], 1):
        lines.append(f"{i}. {t['theme']} — priority {t['priority']}/100, {t['count']} mentions, {t['negPct']}% neg")
    lines += ["", "WHAT USERS SAID"]
    for q in p["quotes"]:
        lines.append(f"- \"{q['text']}\" ({q['rating']}*, {q['source']})")
    if p["trending"]:
        lines += ["", "TRENDING IN COMPLAINTS", ", ".join(x["term"] for x in p["trending"])]
    lines += ["", "THREE ACTION IDEAS"]
    for i, a in enumerate(p["actions"], 1):
        lines.append(f"{i}. {a}")
    lines += ["", "One-pager (PDF) and source CSV attached. No PII included.", "", "— Auto-generated by Review Pulse"]
    return "Subject: " + subj + "\n\n" + "\n".join(lines)
