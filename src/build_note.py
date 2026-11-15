#!/usr/bin/env python3
"""
build_note.py (v3)
data/reviews_sample.csv -> output/{pulse_data.json, weekly_note.md, email_draft.txt}

All maths lives in src/pulse.py (mirrored in dashboard/pulse-core.js and checked by
tests/parity.js). Options:
  --csv PATH        input CSV (default data/reviews_sample.csv)
  --week LABEL      pulse week label, e.g. "Jun 15-21" (default: latest)
  --source NAME     All | App Store | Play Store (default All)
  --weights a,b,c   negativity,volume,momentum weights (default 0.5,0.35,0.15)
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pulse

ROOT = pulse.ROOT
OUT = ROOT / "output"; OUT.mkdir(exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--csv", default=str(ROOT / "data" / "reviews_sample.csv"))
ap.add_argument("--week"); ap.add_argument("--source", default="All")
ap.add_argument("--weights", default="0.5,0.35,0.15")
a = ap.parse_args()

cfg = pulse.load_config()
rows = pulse.load_rows(a.csv, cfg)
weights = tuple(float(x) for x in a.weights.split(","))
p = pulse.analyze(rows, cfg, weights=weights, source=a.source, week=a.week)

def put(name, text):
    with open(OUT / name, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

put("pulse_data.json", json.dumps(p, indent=2, ensure_ascii=False))
note = pulse.fit_note(p)
put("weekly_note.md", note)
put("email_draft.txt", pulse.build_email(p))

print("Note words:", pulse.count_words(note))
print(pulse.build_email(p).splitlines()[0])
print("Top3 by priority:", [t["theme"] for t in p["top_themes"]])
print("Signals:", len(p["signals"]), "| trending:", [t["term"] for t in p["trending"]])
