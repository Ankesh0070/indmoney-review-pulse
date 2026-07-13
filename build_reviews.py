#!/usr/bin/env python3
"""
build_reviews.py  (v2)
Builds data/reviews_sample.csv — a redacted, PII-free sample of INDmoney
App Store + Play Store reviews spanning the last 12 weeks (~240 reviews).

The weekly volumes/sentiment are shaped to tell a realistic story:
  - Withdrawals & Fund Holds  : rising, sharp spike in the last 3 weeks (payout incident)
  - App Performance           : high early, steadily improves after a mid-window update
  - Charges & Fees            : mid-window controversy spike, then settles
  - Customer Support          : steadily elevated
  - Onboarding & KYC          : low volume, mostly positive

Synthetic + representative: phrasings are paraphrased from common public review
patterns. No usernames, emails, phone numbers, PAN/Aadhaar, account/folio numbers.
Columns: review_id, date, week, source, rating, title, text, theme
"""
import csv, random, datetime, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
(ROOT/"data").mkdir(exist_ok=True)
DATA = ROOT/"data"/"reviews_sample.csv"

random.seed(7)

WEEK_END = datetime.date(2026, 6, 21)              # Sunday, latest full week
N_WEEKS = 12
WEEKS = []
for i in range(N_WEEKS - 1, -1, -1):               # oldest -> newest
    end = WEEK_END - datetime.timedelta(weeks=i)
    start = end - datetime.timedelta(days=6)
    WEEKS.append((start, end))
LABEL = [f"{ws.strftime('%b %d')}-{we.strftime('%d')}" for ws, we in WEEKS]

# ------------------------------------------------------------------ templates
T = {
 "Withdrawals & Fund Holds": {"neg":[
    ("Money stuck on withdrawal","Requested a US stock withdrawal over a week ago and it still shows pending. The credit date keeps getting pushed."),
    ("Funds blocked after switch","Tried switching a mutual fund and the amount is now stuck between the old and new fund. Neither side shows it."),
    ("Withdrawal delayed again","Second time my withdrawal took more than ten days to reach my bank. No clear status anywhere in the app."),
    ("Cannot withdraw from savings","Instant withdrawal from the savings feature failed and the money has not come back to my wallet."),
    ("Redemption pending too long","Redeemed units four days back and the status is still processing. It used to be much faster."),
    ("Where is my money","Sold US stocks and the amount has not been credited. The timeline shown in the app is not accurate."),
    ("Payout date keeps changing","Promised credit date moved three times. Hard to plan when the money is just stuck."),
    ("Bank says nothing received","App shows the withdrawal as completed but my bank has not received anything for days."),
 ],"pos":[
    ("Fast payout this time","My last withdrawal hit the bank the same day. Big improvement over earlier."),
    ("Smooth redemption","Redeemed a mutual fund and got the money within the expected window. No issues."),
    ("Quick settlement","US stock sale settled on time and the funds reached my account as shown."),
 ]},
 "Charges & Fees": {"neg":[
    ("Surprise withdrawal fee","I joined when there was no withdrawal fee and now I am being charged one. Not communicated clearly."),
    ("FX markup too high","The currency conversion charge on US funding eats into returns. Wish it was shown upfront."),
    ("Unexpected brokerage","Charged brokerage I did not expect on a small trade. The fee breakup is hard to find."),
    ("Fees keep changing","The charges structure seems to change often and I am never told in advance."),
    ("Hidden charges","Found a charge on my statement that was never shown at the time of the transaction."),
    ("Conversion cost unclear","Could not figure out the real cost of adding dollars because the markup is buried."),
 ],"pos":[
    ("Zero AMC is great","Free demat with no annual maintenance charge is the main reason I stay."),
    ("Cheap mutual fund investing","Direct mutual funds with no commission saves me a lot over the year."),
    ("Low cost for US stocks","Fractional US investing from a small amount with low fees is very useful."),
    ("Fair pricing overall","Brokerage is reasonable and the free fund switching is a nice touch."),
 ]},
 "Customer Support": {"neg":[
    ("Generic replies only","Raised a ticket and got copy-paste responses. Nobody actually solved the problem."),
    ("No one picks up","There is no working helpline. Email replies are slow and do not address the issue."),
    ("Support sent me in circles","They told me to contact my bank even though the bank confirmed nothing was received."),
    ("Ticket closed without fix","My complaint was marked resolved but the underlying issue is still there."),
    ("Slow response","Waited three days for a reply on a fund that is stuck. Too slow for money matters."),
    ("No real escalation","There is no way to escalate a stuck transaction to someone who can actually act."),
 ],"pos":[
    ("Agent actually helped","The support agent followed up and got my issue sorted within a day."),
    ("Quick chat resolution","Used in-app chat and the query about my SIP was answered clearly."),
    ("Good follow-up","Got a callback and the person understood the problem and fixed it."),
 ]},
 "App Performance & Reliability": {"neg":[
    ("App keeps syncing","Every time I open the app it gets stuck on syncing and I cannot place an order."),
    ("Login OTP issues","The OTP does not arrive half the time and I get locked out during market hours."),
    ("Crashes on portfolio","The app crashes when I open the portfolio tab after the latest update."),
    ("Slow and laggy","There is a delay between tapping buy and the order screen loading. Risky during volatility."),
    ("Charts not loading","Live charts freeze and prices do not refresh during busy market sessions."),
    ("Stuck on splash","App hangs on the loading screen and I have to force close and retry."),
 ],"pos":[
    ("Clean all-in-one view","Love seeing Indian stocks, US stocks and mutual funds with net worth in one place."),
    ("Smooth after update","The latest version feels faster and the home screen loads quickly now."),
    ("Great tracking","Net worth tracking across accounts is genuinely useful and well designed."),
    ("Stable now","No crashes since the recent update and syncing is much quicker."),
    ("Fast and snappy","Orders place instantly and the charts load without lag for me now."),
 ]},
 "Onboarding & KYC": {"neg":[
    ("KYC stuck in review","My KYC has been under verification for days with no update. Cannot start investing."),
    ("Document upload fails","The PAN upload step keeps erroring out and restarts the whole flow."),
    ("Account opening loop","Onboarding sent me back to the same screen repeatedly. Could not finish."),
 ],"pos":[
    ("KYC done in minutes","Paperless account opening was quick and I was investing the same day."),
    ("Easy signup","Setting up the demat account was simple and fully online. No branch visit."),
    ("Fast verification","KYC was approved within a few minutes using PAN and Aadhaar."),
    ("Smooth onboarding","Clean step-by-step signup and I understood each stage clearly."),
 ]},
}

# weekly VOLUME profile (len 12, oldest->newest) and NEG_RATIO profile
PROFILE = {
 "Withdrawals & Fund Holds":   ([3,3,2,3,4,3,4,5,6,7,8,9],
                                [.70,.70,.75,.70,.75,.78,.80,.82,.85,.88,.90,.90]),
 "App Performance & Reliability":([7,7,6,6,5,5,4,4,3,3,3,2],
                                [.70,.68,.65,.60,.55,.50,.45,.42,.40,.38,.35,.33]),
 "Charges & Fees":             ([2,2,3,5,7,6,4,3,3,4,4,4],
                                [.50,.55,.70,.80,.82,.78,.65,.60,.60,.65,.70,.72]),
 "Customer Support":           ([3,3,3,4,4,4,4,5,5,5,6,6],
                                [.72,.72,.74,.75,.76,.78,.78,.80,.80,.82,.82,.83]),
 "Onboarding & KYC":           ([3,3,2,3,2,3,3,2,3,2,3,3],
                                [.30,.32,.30,.35,.30,.33,.30,.30,.35,.30,.33,.33]),
}
SOURCES = ["App Store","Play Store"]

rows=[]; rid=1000
for theme,(vol,negr) in PROFILE.items():
    negpool=T[theme]["neg"]; pospool=T[theme]["pos"]
    for wi in range(N_WEEKS):
        v=vol[wi]; nr=negr[wi]
        n_neg=round(v*nr)
        n_pos=round((v-n_neg)*0.80)
        n_neu=v-n_neg-n_pos
        ws,we=WEEKS[wi]
        def add(pool,rating_fn,k):
            global rid
            for _ in range(k):
                title,text=random.choice(pool)
                rid+=1
                d=ws+datetime.timedelta(days=random.randint(0,6))
                rows.append([f"R{rid}",d.isoformat(),LABEL[wi],
                             random.choice(SOURCES),rating_fn(),title,text,theme])
        add(negpool, lambda: random.choices([1,2],weights=[3,2])[0], n_neg)
        add(negpool, lambda: 3, n_neu)
        add(pospool, lambda: random.choices([5,4],weights=[3,2])[0], n_pos)

rows.sort(key=lambda r:r[1])

# ----------------------------------------------------------------- PII guard
joined=" ".join(str(c) for r in rows for c in r)
for pat in [r"[A-Z]{5}\d{4}[A-Z]", r"\b\d{12}\b", r"\b\d{10}\b",
            r"[\w.\-]+@[\w.\-]+\.\w+", r"folio\s*\d+", r"a/c\s*\d+"]:
    assert not re.search(pat,joined,re.I), f"PII-like pattern: {pat}"

with open(DATA,"w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["review_id","date","week","source","rating","title","text","theme"])
    w.writerows(rows)

print(f"Wrote {len(rows)} reviews across {N_WEEKS} weeks")
print("Window:",WEEKS[0][0].isoformat(),"->",WEEKS[-1][1].isoformat())
print("Pulse week:",LABEL[-1])
