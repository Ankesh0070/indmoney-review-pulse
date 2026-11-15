# Review Pulse — INDmoney
# Workflow: Import -> Group -> Generate Note -> Draft Email
# No make on Windows? Use:  python scripts/build_all.py [--sample] [--test]
PYTHON ?= python3
.PHONY: all sample note pdf dashboard test clean install

all: note pdf dashboard ## Rebuild outputs from data/reviews_sample.csv (does NOT overwrite your data)

install: ## Install Python deps
	$(PYTHON) -m pip install -r requirements.txt

sample: ## Regenerate the synthetic sample CSV (overwrites data/reviews_sample.csv)
	$(PYTHON) src/build_reviews.py

note: ## weekly_note.md, email_draft.txt, pulse_data.json
	$(PYTHON) src/build_note.py

pdf: ## one-page weekly_note.pdf
	$(PYTHON) src/build_pdf.py

dashboard: ## index.html (served by GitHub Pages)
	$(PYTHON) scripts/inject_data.py

test: ## Python unit tests + JS/Python parity check
	$(PYTHON) -m unittest discover -s tests -v
	node tests/parity.js

clean: ## Remove generated artifacts
	$(PYTHON) scripts/build_all.py --clean
