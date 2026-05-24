import json
import io
from datetime import datetime

import streamlit as st
from openai import OpenAI

# =========================
# OpenAI client
# =========================

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =========================
# System prompt
# =========================

SYSTEM_PROMPT = """
You are Segment Stitcher, an expert financial reporting analyst specializing in SEC segment disclosures.

Your job:
- Take extracted segment information from multiple 10-K/10-Q filings for the same company over time.
- Infer how management’s reportable segments have changed (renames, splits, merges, reclassifications, discontinued operations).
- Produce a consistent, time-series view of segments and a mapping from each original segment label to a canonical segment name.

Context you will receive:
- A structured JSON object with:
  - company_name: string
  - filings: array of filings, each with:
    - filing_id: string (e.g., "2022 10-K")
    - period_end: string (ISO date)
    - segments: array of segments, each with:
      - label: string (segment name as reported)
      - revenue: number or null
      - operating_income: number or null
      - other_metrics: object (key-value pairs, may be empty)
- The filings are already ordered from oldest to newest.

Your tasks:
1. Analyze how segment labels evolve over time.
2. Identify likely:
   - Renames (same business, new label)
   - Splits (one segment becomes multiple)
   - Merges (multiple segments combined)
   - Discontinued or immaterial segments
3. Define a set of canonical_segment_names that best represent the economic reality over time.
4. Map each original segment label in each filing to:
   - a canonical_segment_name, and
   - a change_type: one of ["unchanged", "rename", "split", "merge", "discontinued", "new"].
5. Explain your reasoning in concise natural language, focusing on:
   - evidence from metrics (revenue, operating income, trends)
   - wording similarities in labels
   - appearance/disappearance patterns across years.

Output format (MUST be valid JSON):
{
  "canonical_segments": [
    {
      "canonical_segment_name": string,
      "description": string
    }
  ],
  "mappings": [
    {
      "filing_id": string,
      "original_label": string,
      "canonical_segment_name": string,
      "change_type": "unchanged" | "rename" | "split" | "merge" | "discontinued" | "new",
      "rationale": string
    }
  ],
  "global_explanation": string
}

Constraints and style:
- Be conservative: do not force a mapping if evidence is weak; in that case, set canonical_segment_name to "Unclear" and explain why.
- Never invent numeric values; only reason from the metrics provided.
- Prefer stable canonical names that make sense to a financial analyst.
- Keep rationales short but specific (1–3 sentences).
- If filings are inconsistent or incomplete, explicitly call that out in global_explanation.
"""

# =========================
# Helpers: parsing / normalization
# =========================


def parse_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s == "" or s.lower() in {"na", "n/a", "none"}:
        return None
    s = s.replace(",", "").replace("$", "")
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def normalize_label(label: str) -> str:
    if label is None:
        return ""
    s = str(label).strip()
    # remove common footnote markers
    for marker in ["*", "†"]:
        s = s.replace(marker, "")
    return " ".join(s.split())


def is_total_or_elimination(label: str) -> bool:
    l = label.lower()
    return any(
        kw in l
        for kw in [
            "total",
            "consolidated",
            "eliminations",
            "intersegment",
            "corporate",
        ]
    )


# =========================
# Grounding payload builder
# =========================


def build_grounding_payload(company_name: str, filings_data: list[dict]) -> dict:
    filings = []
    for filing in filings_data:
        segments = []
        for i, row in enumerate(filing["segments_raw"]):
            label = normalize_label(row.get("label_raw", ""))
            if not label or is_total_or_elimination(label):
                continue

            revenue = parse_number(row.get("revenue_raw"))
            op_inc = parse_number(row.get("operating_income_raw"))

            other_metrics = {}
            for k, v in row.items():
                if k not in ["label_raw", "revenue_raw", "operating_income_raw"]:
                    other_metrics[k] = parse_number(v)

            other_metrics["segment_order"] = i

            segments.append(
                {
                    "label": label,
                    "revenue": revenue,
                    "operating_income": op_inc,
                    "other_metrics": other_metrics,
                }
            )

        filings.append(
            {
                "filing_id": filing["filing_id"],
                "period_end": filing["period_end"],
                "segments": segments,
            }
        )

    return {
        "company_name": company_name,
        "filings": filings,
    }


# =========================
# LLM call
# =========================


def run_segment_stitcher(system_prompt: str, grounding_payload: dict):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "You are given structured segment data for multiple filings.\n"
                        "Here is the JSON context:\n"
                        f"{json.dumps(grounding_payload, indent=2)}\n\n"
                        "Return valid JSON following the schema in the system prompt."
                    ),
                },
            ],
            temperature=0.2,
        )

        raw_output = response.choices[0].message.content
        stitched = json.loads(raw_output)
        return stitched, raw_output, None

    except json.JSONDecodeError:
        return None, raw_output, "Model returned invalid JSON."

    except Exception as e:
        return None, None, str(e)


# =========================
# Placeholder extraction logic
# =========================
# Replace this with your real extraction from PDFs / your existing src modules.


def dummy_extract_segments_from_pdf(file_bytes: bytes) -> list[dict]:
    """
    TEMPORARY: Replace with your real extraction.
    Returns a list of rows like:
      {"label_raw": "...", "revenue_raw": "...", "operating_income_raw": "..."}
    """
    # For now, just return a fake single segment so the LLM pipeline is testable.
    return [
        {
            "label_raw": "Example Segment",
            "revenue_raw": "1000",
            "operating_income_raw": "150",
        }
    ]


# =========================
# Streamlit UI
# =========================


def main():
    st.set_page_config(page_title="Segment Stitcher", layout="wide")
    st.title("Segment Stitcher")
    st.write(
        "Upload multiple 10-K/10-Q filings for a single company. "
        "The app will build a grounded segment view and ask an LLM to reconcile segments over time."
    )

    company_name = st.text_input("Company name", value="Example Co.")

    uploaded_files = st.file_uploader(
        "Upload filings (PDF)", type=["pdf"], accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("Upload at least one filing to begin.")
        return

    filings_data = []

    st.subheader("Filings")
    for idx, uploaded in enumerate(uploaded_files):
        col1, col2 = st.columns(2)
        with col1:
            filing_id = st.text_input(
                f"Filing label for file {idx+1}",
                value=f"Filing {idx+1}",
                key=f"filing_id_{idx}",
            )
        with col2:
            period_end_str = st.text_input(
                f"Period end (YYYY-MM-DD) for file {idx+1}",
                value="2023-12-31",
                key=f"period_end_{idx}",
            )

        # Extract segments (replace dummy with your real extraction)
        file_bytes = uploaded.read()
        segments_raw = dummy_extract_segments_from_pdf(file_bytes)

        st.markdown(f"**Detected {len(segments_raw)} segment row(s)** (dummy extraction).")
        st.json(segments_raw)

        filings_data.append(
            {
                "filing_id": filing_id,
                "period_end": period_end_str,
                "segments_raw": segments_raw,
            }
        )

    grounding_payload = build_grounding_payload(company_name, filings_data)

    st.subheader("Grounding payload (model input)")
    st.json(grounding_payload)

    if st.button("Run Segment Stitcher"):
        with st.spinner("Analyzing segments with LLM..."):
            stitched, raw_output, error = run_segment_stitcher(
                SYSTEM_PROMPT, grounding_payload
            )

        if error:
            st.error(f"Error: {error}")
            if raw_output:
                st.text_area("Raw model output", raw_output, height=300)
        else:
            st.success("LLM analysis complete!")

            st.subheader("Canonical Segments")
            st.json(stitched.get("canonical_segments", []))

            st.subheader("Mappings")
            st.json(stitched.get("mappings", []))

            st.subheader("Global Explanation")
            st.write(stitched.get("global_explanation", ""))

            with st.expander("Raw model output"):
                st.text_area("Raw", raw_output, height=300)


if __name__ == "__main__":
    main()

   
