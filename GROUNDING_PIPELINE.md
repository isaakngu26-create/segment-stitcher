"""
SegmentStitcher Grounding Pipeline
===================================

The grounding pipeline transforms raw segment extraction into clean, structured,
model-ready JSON that the LLM can reason over effectively for segment reconciliation.

Pipeline Steps:
1. Table Extraction (extract_segment_tables)
2. Label Normalization (normalize_label)
3. Number Parsing (parse_number)
4. Non-segment Filtering (is_total_or_elimination)
5. Metric Extraction (extract_numeric_fields)
6. Grounding Payload Assembly (build_grounding_payload)

Output Format:
The grounding payload is structured JSON passed to the LLM:
{
  "company_name": "Apple Inc.",
  "filings": [
    {
      "filing_id": "2022 10-K",
      "period_end": "2022-12-31",
      "segments": [
        {
          "label": "iPhone",
          "revenue": 71000.0,
          "operating_income": 12345.0,
          "other_metrics": {
            "segment_order": 0,
            "assets": 56789.0
          }
        }
      ]
    }
  ]
}

Normalization Rules:
- Labels: Strip whitespace, remove footnote markers (*, †, §, etc.), collapse spaces
- Numbers: Remove currency ($, €, £), commas, parentheses (→ negative), handle N/A
- Non-segments: Filter rows containing "Total", "Consolidated", "Eliminations", etc.
- Ordering: Filings sorted oldest-to-newest for chronological analysis

Example Usage:
from src.grounding import build_grounding_payload
payload = build_grounding_payload(
    company_name="Apple Inc.",
    filings=filings,
    segment_tables=segment_tables
)
"""
