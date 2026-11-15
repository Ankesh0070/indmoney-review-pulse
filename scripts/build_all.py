#!/usr/bin/env python3
"""
build_all.py - one cross-platform command (Windows / macOS / Linux, no make needed).

  python scripts/build_all.py              note -> pdf -> dashboard  (uses data/reviews_sample.csv as is)
  python scripts/build_all.py --sample     regenerate the synthetic sample first (OVERWRITES data/reviews_sample.csv)
  python scripts/build_all.py --test       also run the Python + JS test suites
  python scripts/build_all.py --clean      delete generated artifacts
"""
import argparse, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--sample", action="store_true"); ap.add_argument("--test", action="store_true"); ap.add_argument("--clean", action="store_true")
a = ap.parse_args()
env = dict(os.environ, PYTHONIOENCODING="utf-8")

def run(*cmd):
    print("\n$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, env=env)
    if r.returncode:
        sys.exit(r.returncode)

if a.clean:
    for p in ("index.html", "output/weekly_note.md", "output/weekly_note.pdf", "output/email_draft.txt", "output/pulse_data.json"):
        (ROOT / p).unlink(missing_ok=True)
    shutil.rmtree(ROOT / "tests" / "__pycache__", ignore_errors=True); shutil.rmtree(ROOT / "src" / "__pycache__", ignore_errors=True)
    print("cleaned"); sys.exit(0)

py = sys.executable
if a.sample:
    run(py, "src/build_reviews.py")
run(py, "src/build_note.py")
run(py, "src/build_pdf.py")
run(py, "scripts/inject_data.py")
if a.test:
    run(py, "-m", "unittest", "discover", "-s", "tests", "-v")
    node = shutil.which("node")
    if node:
        run(node, "tests/parity.js")
    else:
        print("node not found - skipped tests/parity.js")
print("\nDone. Open index.html")
