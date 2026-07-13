# Theme legend

Reviews are grouped into a maximum of **5 themes**. Sentiment is derived from the
star rating: **1–2★ = negative**, **3★ = neutral**, **4–5★ = positive**.

| Theme | Covers | Typical keywords |
|---|---|---|
| **Withdrawals & Fund Holds** | Money stuck on withdrawal/redemption, US-stock payout delays, failed fund switches, savings-pot withdrawals | withdraw, redeem, stuck, pending, credited, switch, payout |
| **Charges & Fees** | Brokerage, withdrawal fees, FX/conversion markup, surprise or changed fees, AMC | fee, charge, brokerage, FX, markup, AMC |
| **Customer Support** | Response time, generic/copy-paste replies, no resolution, no helpline | support, ticket, reply, helpline, agent, resolve, escalate |
| **App Performance & Reliability** | Crashes, slow sync, login/OTP failures, charts not loading | crash, sync, OTP, login, slow, lag, freeze |
| **Onboarding & KYC** | Account opening, KYC verification, document upload | KYC, onboarding, verify, PAN, Aadhaar, signup |

## Priority score

Themes in the weekly note are ranked by a priority score (0–100):

```
priority = 0.50 × negativity%  +  0.35 × volume_share  +  0.15 × momentum
```

- **negativity%** — share of the theme's reviews rated 1–2★ this week
- **volume_share** — the theme's mentions relative to the week's busiest theme
- **momentum** — week-over-week change in mentions (rising issues score higher)

This lets a small-but-spiking issue outrank a large-but-stable one — closer to how a
product team actually triages.
