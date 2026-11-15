#!/usr/bin/env python3
"""
import_reviews.py - the "Import" + "Group" steps for REAL data.

Takes raw public review exports (App Store Connect CSV, Google Play Console CSV, or
anything with date / rating / text columns), then:
  1. maps the columns (many common header names are recognised)
  2. REDACTS PII (emails, phones, PAN, Aadhaar-like ids, account/folio numbers, @handles, links)
  3. auto-assigns each review to one of the 5 themes (keywords in data/themes.json)
  4. writes data/reviews_sample.csv in the pipeline's schema

Usage (tag a file's store with FILE=SOURCE):
  python src/import_reviews.py "appstore.csv=App Store" "playstore.csv=Play Store"
  python src/import_reviews.py export.csv               # uses a source column, else "Unknown"
  python src/import_reviews.py export.csv --out data/my.csv --ignore-theme

Reviews matching no theme are kept (blank theme) and counted in the report.
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pulse

ap = argparse.ArgumentParser()
ap.add_argument("inputs", nargs="+", help='CSV files, optionally "path=Source Name"')
ap.add_argument("--out", default=str(pulse.ROOT / "data" / "reviews_sample.csv"))
ap.add_argument("--ignore-theme", action="store_true", help="re-classify even if the file has a theme column")
a = ap.parse_args()

cfg = pulse.load_config()
all_rows, total = [], {}
for spec in a.inputs:
    path, _, src = spec.partition("=")
    rows, rep = pulse.normalise(pulse.read_csv(path), cfg, default_source=src or "Unknown",
                                keep_theme=not a.ignore_theme)
    if src:
        for r in rows:
            r["source"] = src
    print(f"{path}: {rep}")
    all_rows += rows
    for k, v in rep.items():
        total[k] = total.get(k, 0) + v
all_rows.sort(key=lambda r: (r["date"], r["review_id"]))
pulse.write_csv(all_rows, a.out)
print(f"\nWrote {len(all_rows)} reviews -> {a.out}")
print(f"PII redactions applied: {total.get('redactions', 0)} | unclassified: {total.get('unclassified', 0)}")
print("Next: python src/build_note.py && python src/build_pdf.py && python scripts/inject_data.py")
