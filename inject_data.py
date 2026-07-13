#!/usr/bin/env python3
"""
inject_data.py
Reads data/reviews_sample.csv + dashboard/template.html and writes index.html
(at the repo root) with the reviews embedded in place of the __DATA__ token.
This index.html is what GitHub Pages serves — fully self-contained, no backend.
Runs a PII guard before writing.
"""
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "reviews_sample.csv"
TEMPLATE = ROOT / "dashboard" / "template.html"
OUT = ROOT / "index.html"

rows = [{"date": r["date"], "week": r["week"], "source": r["source"],
         "rating": int(r["rating"]), "title": r["title"], "text": r["text"],
         "theme": r["theme"]} for r in csv.DictReader(open(CSV))]

# PII guard
joined = " ".join(str(v) for r in rows for v in r.values())
for pat in [r"[A-Z]{5}\d{4}[A-Z]", r"\b\d{12}\b", r"\b\d{10}\b", r"[\w.\-]+@[\w.\-]+\.\w+"]:
    if re.search(pat, joined):
        raise SystemExit(f"PII-like pattern found ({pat}); aborting.")

html = TEMPLATE.read_text().replace("__DATA__", json.dumps(rows, ensure_ascii=False))
if "__DATA__" in html:
    raise SystemExit("template missing __DATA__ token")
OUT.write_text(html)
print(f"Wrote {OUT.name} ({len(html)} bytes, {len(rows)} reviews embedded)")
