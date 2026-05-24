# BUILD_LOG

## 2026-05-22

# BUILD_LOG

## 2026-05-24

- **Enhanced system prompt and schema design**: Replaced generic prompt with a comprehensive, domain-specific system prompt that explicitly instructs the LLM to:
  - Analyze segment evolution patterns (renames, splits, merges, discontinuations)
  - Define canonical segment names grounded in economic reality
  - Map each filing's segments with explicit change_type and evidence-based rationale
  - Reason about metrics (revenue, operating income) and label patterns
- **Improved JSON grounding**: Updated context rendering to build a structured JSON object with company_name, filing_id, period_end, and segment metrics (revenue, operating_income, other_metrics).
- **Extended function schema**: Expanded the schema to capture canonical_segments, detailed mappings with change_type enums (unchanged/rename/split/merge/discontinued/new), and global_explanation.
- **Updated response parsing**: Modified the app to handle the new response structure with canonical_segments, mappings, and global_explanation.
- **Enhanced UI display**: Updated Streamlit UI to show canonical segment definitions, filed-level mappings with change types and rationales.

## 2026-05-22

- Added OpenAI-powered segment reconciliation to replace TF-IDF-only mapping.
- Implemented JSON-schema grounded prompt engineering via OpenAI function calling.
- Added a system prompt and structured function return schema to keep the LLM output deterministic.
- Added fallback behavior to TF-IDF when `OPENAI_API_KEY` is not configured.
- Improved grounding by encoding extracted segment tables and definitions as structured JSON context.
- Added an evaluation dataset, evaluation script, and evaluation test to provide rubric evidence.
- Updated Streamlit UI to show reconciliation rationale and rename detection.
- Added `pytest` tests for LLM response parsing, fallback behavior, and evaluation dataset validity.
- Added Streamlit Cloud readiness with `.streamlit/config.toml` and deployment instructions.
