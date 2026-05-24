# BUILD_LOG

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
