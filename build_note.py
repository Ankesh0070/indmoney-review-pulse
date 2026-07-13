#!/usr/bin/env python3
"""
build_note.py (v2)
Reads data/reviews_sample.csv -> computes a smarter weekly pulse and writes:
  weekly_note.md, weekly_note pieces, email_draft.txt, pulse_data.json

Smarter than raw counts: themes are ranked by a PRIORITY score that blends
how negative they are, how much volume they carry, and week-over-week momentum,
so a small-but-spiking issue can outrank a large-but-stable one.
No PII is read, written, or displayed.
"""
import csv, json, collections, datetime, statistics, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/"output"; OUT.mkdir(exist_ok=True)

CSV=str(ROOT/"data"/"reviews_sample.csv")
SELF_ALIAS="me+indmoney-pulse@myteam.example"

rows=list(csv.DictReader(open(CSV)))
for r in rows: r["rating"]=int(r["rating"])

# weeks ordered by first date
wfirst={}
for r in rows:
    wfirst.setdefault(r["week"], r["date"])
    if r["date"]<wfirst[r["week"]]: wfirst[r["week"]]=r["date"]
WEEKS=sorted({r["week"] for r in rows}, key=lambda w:wfirst[w])
PULSE=WEEKS[-1]; PREV=WEEKS[-2]
THEMES=sorted({r["theme"] for r in rows})

sent=lambda r: "neg" if r<=2 else ("pos" if r>=4 else "neu")
def sub(week=None, theme=None):
    return [r for r in rows if (week is None or r["week"]==week) and (theme is None or r["theme"]==theme)]
def st(items):
    n=len(items)
    avg=round(statistics.mean(i["rating"] for i in items),2) if n else 0
    neg=sum(1 for i in items if sent(i["rating"])=="neg")
    return {"n":n,"avg":avg,"negPct":round(100*neg/n) if n else 0}

cur=sub(PULSE); prev=sub(PREV)
Scur=st(cur); Sprev=st(prev)
delta=round(Scur["avg"]-Sprev["avg"],2)

counts_cur=collections.Counter(r["theme"] for r in cur)
counts_prev=collections.Counter(r["theme"] for r in prev)
maxc=max(counts_cur.values()) if counts_cur else 1

def priority(theme):
    c=counts_cur.get(theme,0); p=counts_prev.get(theme,0)
    negPct=st(sub(PULSE,theme))["negPct"]
    vol_score=100*c/maxc
    mom=c-p
    mom_score=max(0,min(100,50+mom*9))
    return round(0.50*negPct + 0.35*vol_score + 0.15*mom_score), c, p, negPct, mom

ranked=sorted(THEMES, key=lambda t:-priority(t)[0])
top3=ranked[:3]

# 12-week trend per theme (counts + negPct)
trend={}
for t in THEMES:
    counts=[]; negs=[]
    for w in WEEKS:
        s=st(sub(w,t)); counts.append(s["n"]); negs.append(s["negPct"])
    trend[t]={"counts":counts,"negPct":negs}

pulse_avg=[st(sub(w))["avg"] for w in WEEKS]
pulse_neg=[st(sub(w))["negPct"] for w in WEEKS]
pulse_vol=[st(sub(w))["n"] for w in WEEKS]
src=collections.Counter(r["source"] for r in cur)

# auto headline
lead=top3[0]; lp=priority(lead)
mover=max(THEMES,key=lambda t:priority(t)[4])  # biggest WoW rise
mv=priority(mover)
falls=min(THEMES,key=lambda t:priority(t)[4]); fv=priority(falls)
headline=(f"{lead} is the week's top priority "
          f"({lp[1]} mentions, {lp[3]}% negative"
          + (f", up {lp[4]} WoW" if lp[4]>0 else "") + ").")
if mv[4]>=2 and mover!=lead:
    headline+=f" {mover} is rising fastest (+{mv[4]} WoW)."
if fv[4]<=-2:
    headline+=f" {falls} is easing ({fv[4]} WoW)."

# quotes: lowest-rated, shortest, per top theme
def quote(theme):
    c=sorted(sub(PULSE,theme), key=lambda r:(r["rating"],len(r["text"])))
    r=c[0]; t=r["text"]
    if len(t)>140: t=t[:137].rsplit(" ",1)[0]+"..."
    return {"text":t,"rating":r["rating"],"source":r["source"],"theme":theme}
quotes=[quote(t) for t in top3]

ACTIONS={
 "Withdrawals & Fund Holds":"Ship a live withdrawal/redemption tracker with honest ETAs and auto-alerts when a payout slips past the promised date.",
 "Charges & Fees":"Show a full fee break-up on the confirm screen and post any fee change to an in-app changelog before it takes effect.",
 "Customer Support":"Add a priority escalation path with callback for stuck-money tickets and retire copy-paste macros on fund-hold cases.",
 "App Performance & Reliability":"Hold the post-update stability gains: keep gating releases on a crash-free-session threshold and watch OTP-login during market hours.",
 "Onboarding & KYC":"Make KYC status visible step-by-step with a clear retry on document-upload errors so users aren't stuck in a loop.",
}
actions=[ACTIONS[t] for t in top3]

data={
 "pulse_week":PULSE,"prev_week":PREV,"weeks":WEEKS,
 "kpi":{"n":Scur["n"],"avg":Scur["avg"],"avg_prev":Sprev["avg"],"delta":delta,
        "negPct":Scur["negPct"],"src":dict(src)},
 "headline":headline,
 "top_themes":[{"theme":t,"priority":priority(t)[0],"count":counts_cur.get(t,0),
                "prev":counts_prev.get(t,0),"wow":priority(t)[4],
                "avg":st(sub(PULSE,t))["avg"],"negPct":st(sub(PULSE,t))["negPct"]} for t in top3],
 "all_priorities":[{"theme":t,"priority":priority(t)[0],"count":counts_cur.get(t,0),
                    "wow":priority(t)[4],"negPct":st(sub(PULSE,t))["negPct"]} for t in ranked],
 "trend":trend,"pulse_avg":pulse_avg,"pulse_neg":pulse_neg,"pulse_vol":pulse_vol,
 "quotes":quotes,"actions":actions,
}
json.dump(data,open(OUT/"pulse_data.json","w"),indent=2)

# ---------- markdown note (<=250 words) ----------
arr="▲" if delta>0 else ("▼" if delta<0 else "=")
md=[]
md.append("# INDmoney — Weekly Review Pulse")
md.append(f"**Week of {PULSE}, 2026** · {Scur['n']} reviews · "
          f"avg {Scur['avg']:.2f} {arr} ({delta:+.2f} WoW) · {Scur['negPct']}% negative\n")
md.append(f"**Headline.** {headline}\n")
md.append("## Top 3 themes")
for i,t in enumerate(top3,1):
    pr=priority(t); wow=pr[4]; wows=f"+{wow}" if wow>0 else str(wow)
    md.append(f"{i}. **{t}** — priority {pr[0]}/100 · {pr[1]} mentions ({wows} WoW) · "
              f"avg {st(sub(PULSE,t))['avg']:.2f}★ · {pr[3]}% negative")
md.append("")
md.append("## In users' words")
for q in quotes:
    md.append(f"> \"{q['text']}\" — {q['rating']}★, {q['source']} · *{q['theme']}*")
md.append("")
md.append("## Three action ideas")
for i,a in enumerate(actions,1): md.append(f"{i}. {a}")
md.append("")
md.append("---")
md.append("*Source: public App Store + Play Store review exports (redacted sample, 12-week window). "
          "No PII. Max 5 themes; ranked by priority score.*")
note="\n".join(md)
open(OUT/"weekly_note.md","w").write(note)
print("Note words:",len(re.findall(r"\b\w+\b",note)))

# ---------- email draft ----------
subj=f"INDmoney Weekly Review Pulse — {PULSE} (avg {Scur['avg']:.2f}{arr}, {Scur['negPct']}% neg)"
body=f"""Hi team,

This week's INDmoney review pulse ({PULSE}, 2026), from public App Store + Play Store reviews.
{Scur['n']} reviews, avg {Scur['avg']:.2f} ({delta:+.2f} WoW), {Scur['negPct']}% negative.

HEADLINE
{headline}

TOP 3 THEMES (by priority = negativity x volume x momentum)
1. {top3[0]} — priority {data['top_themes'][0]['priority']}/100, {data['top_themes'][0]['count']} mentions, {data['top_themes'][0]['negPct']}% neg
2. {top3[1]} — priority {data['top_themes'][1]['priority']}/100, {data['top_themes'][1]['count']} mentions, {data['top_themes'][1]['negPct']}% neg
3. {top3[2]} — priority {data['top_themes'][2]['priority']}/100, {data['top_themes'][2]['count']} mentions, {data['top_themes'][2]['negPct']}% neg

WHAT USERS SAID
- "{quotes[0]['text']}" ({quotes[0]['rating']}*, {quotes[0]['source']})
- "{quotes[1]['text']}" ({quotes[1]['rating']}*, {quotes[1]['source']})
- "{quotes[2]['text']}" ({quotes[2]['rating']}*, {quotes[2]['source']})

THREE ACTION IDEAS
1. {actions[0]}
2. {actions[1]}
3. {actions[2]}

One-pager (PDF) and source CSV attached. No PII included.

— Auto-generated by Review Pulse"""
open(OUT/"email_draft.txt","w").write("Subject: "+subj+"\n\n"+body)
print("Subject:",subj)
print("Top3 by priority:",top3)
