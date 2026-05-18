# SegmentStitcher

SegmentStitcher is a hybrid AI pipeline that extracts segment reporting, KPI tables, and segment definitions from SEC filings (10-K, 10-Q, earnings decks), detects changes in definitions over time, and builds a reconciled time-series dataset.

## What’s included

- `src/app.py` — Streamlit interface for file upload, processing, and CSV export
- `src/ingestion` — PDF ingestion and metadata extraction
- `src/extraction` — Segment table and definition extraction
- `src/reconciliation` — Semantic matching and change detection
- `src/output` — Time series assembly and CSV export

## Install

1. Create a Python virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app
```bash
streamlit run src/app.py
```

## Usage

- Upload one or more SEC filings in PDF format
- The app extracts segments, matches segment definitions, detects definition changes, and constructs a time-series table
- Download the reconciled result as CSV

## Notes

The current implementation uses PDF extraction heuristics and TF-IDF semantic matching. It is designed as a working scaffold and can be extended for production-grade financial document parsing.
