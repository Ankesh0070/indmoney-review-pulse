#!/usr/bin/env python3
"""
inject_data.py
Builds index.html (repo root) from dashboard/template.html by inlining:
  __CORE__    dashboard/pulse-core.js   (the JS twin of src/pulse.py)
  __CONFIG__  data/themes.json          (themes, keywords, actions - shared with Python)
  __DATA__    data/reviews_sample.csv   (normalised + redacted rows)
The result is one self-contained file: GitHub Pages serves it, no backend needed.
A PII guard aborts the build if anything that looks like personal data survives.
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pulse

ROOT = pulse.ROOT
cfg = pulse.load_config()
rows = pulse.load_rows(ROOT / "data" / "reviews_sample.csv", cfg)
data = [{k: r[k] for k in pulse.COLUMNS} for r in rows]

joined = " ".join(str(v) for r in data for v in r.values())
for pat in [r"\b[A-Z]{5}\d{4}[A-Z]\b", r"\b\d{10,}\b", r"[\w.+-]+@[\w-]+\.\w+", r"https?://"]:
    if re.search(pat, joined):
        raise SystemExit(f"PII-like pattern found ({pat}); aborting.")

def js_safe(s):                     # keep </script> and U+2028/9 from breaking the inline script
    return s.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")

tpl = (ROOT / "dashboard" / "template.html").read_text(encoding="utf-8")
core = (ROOT / "dashboard" / "pulse-core.js").read_text(encoding="utf-8")
config = json.loads((ROOT / "data" / "themes.json").read_text(encoding="utf-8"))
config.pop("_comment", None)
html = (tpl.replace("__CORE__", js_safe(core))
           .replace("__CONFIG__", js_safe(json.dumps(config, ensure_ascii=False)))
           .replace("__DATA__", js_safe(json.dumps(data, ensure_ascii=False))))
for tok in ("__CORE__", "__CONFIG__", "__DATA__"):
    if tok in html:
        raise SystemExit(f"unreplaced token {tok}")
with open(ROOT / "index.html", "w", encoding="utf-8", newline="\n") as f:
    f.write(html)
print(f"Wrote index.html ({len(html):,} bytes, {len(data)} reviews embedded)")
