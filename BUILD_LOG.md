# BUILD_LOG

## 2026-05-22

- Added OpenAI-powered segment reconciliation to replace TF-IDF-only mapping.
- Implemented JSON-schema grounded prompt engineering via OpenAI function calling.
- Added a system prompt and structured function return schema to keep the LLM output deterministic.
- Added fallback behavior to TF-IDF when `OPENAI_API_KEY` is not configured.
- Updated Streamlit UI to show reconciliation rationale and rename detection.
- Added `pytest` tests for LLM response parsing and fallback behavior.
- Added Streamlit Cloud readiness with `.streamlit/config.toml` and deployment instructions.
