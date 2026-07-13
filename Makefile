# Review Pulse — INDmoney
# Workflow: Import -> Group -> Generate Note -> Draft Email
.PHONY: all data note pdf dashboard clean install

all: data note pdf dashboard ## Run the whole pipeline

install: ## Install Python deps
	pip install -r requirements.txt --break-system-packages

data: ## Build the redacted reviews CSV (data/reviews_sample.csv)
	python3 src/build_reviews.py

note: ## Generate weekly_note.md, email_draft.txt, pulse_data.json (output/)
	python3 src/build_note.py

pdf: ## Render the one-page weekly_note.pdf (output/)
	python3 src/build_pdf.py

dashboard: ## Inject reviews into the template -> index.html (served by Pages)
	python3 scripts/inject_data.py

clean: ## Remove generated artifacts
	rm -f index.html output/weekly_note.md output/weekly_note.pdf \
	      output/email_draft.txt output/pulse_data.json
