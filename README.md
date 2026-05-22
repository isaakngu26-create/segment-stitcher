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
- The reconciliation layer uses OpenAI to infer canonical segment labels and explain segment renames
- Download the reconciled result as CSV

## OpenAI integration

If you set `OPENAI_API_KEY` in your environment, the app will use the OpenAI API to perform segment reconciliation using a JSON schema-grounded prompt. If the key is missing, the app falls back to TF-IDF matching.

Example:
```bash
export OPENAI_API_KEY="your-api-key"
streamlit run src/app.py
```

On Streamlit Community Cloud, add `OPENAI_API_KEY` to the app secrets.

## Streamlit Cloud deployment

1. Push this repository to GitHub
2. Open https://share.streamlit.io
3. Select `isaakngu26-create/segment-stitcher`
4. Set branch to `main` and main file to `src/app.py`
5. Add `OPENAI_API_KEY` as a secret if you want LLM-backed reconciliation

## Testing

Run tests with:
```bash
pytest
```

## Notes

The project now includes an LLM-backed reconciliation stage, function-calling JSON grounding, and tests to validate the parser logic and fallback behavior.
