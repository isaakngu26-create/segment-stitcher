import json
import os

try:
    import openai
    from openai import OpenAI
    from openai.error import AuthenticationError, OpenAIError
except Exception:
    openai = None
    OpenAI = None
    AuthenticationError = Exception
    OpenAIError = Exception

from .semantic_matcher import match_segments as tfidf_match_segments

SYSTEM_PROMPT = """You are Segment Stitcher, an expert financial reporting analyst specializing in SEC segment disclosures.

Your job:
- Take extracted segment information from multiple 10-K/10-Q filings for the same company over time.
- Infer how management's reportable segments have changed (renames, splits, merges, reclassifications, discontinued operations).
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

FUNCTION_SCHEMA = {
    "name": "reconcile_segments",
    "description": "Map segment labels to canonical names and identify change types across filings.",
    "parameters": {
        "type": "object",
        "properties": {
            "canonical_segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "canonical_segment_name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["canonical_segment_name", "description"],
                },
            },
            "mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "filing_id": {"type": "string"},
                        "original_label": {"type": "string"},
                        "canonical_segment_name": {"type": "string"},
                        "change_type": {
                            "type": "string",
                            "enum": ["unchanged", "rename", "split", "merge", "discontinued", "new"],
                        },
                        "rationale": {"type": "string"},
                    },
                    "required": ["filing_id", "original_label", "canonical_segment_name", "change_type", "rationale"],
                },
            },
            "global_explanation": {"type": "string"},
        },
        "required": ["canonical_segments", "mappings", "global_explanation"],
    },
}


def _openai_api_key():
    if OpenAI is None:
        return None
    key = os.getenv("OPENAI_API_KEY")
    return key


def _render_context(tables, definitions):
    filings = []
    for filename, table in tables.items():
        segments = []
        segment_list = table.get("segments", [])
        values = table.get("values", [])
        
        for i, segment_label in enumerate(segment_list):
            segment_obj = {
                "label": segment_label,
                "revenue": values[i] if i < len(values) else None,
                "operating_income": None,
                "other_metrics": {},
            }
            segments.append(segment_obj)
        
        filing_obj = {
            "filing_id": filename,
            "period_end": table.get("period", "Unknown"),
            "segments": segments,
        }
        filings.append(filing_obj)
    
    return json.dumps(
        {
            "company_name": "Unknown",
            "filings": filings,
        },
        indent=2,
        ensure_ascii=False,
    )


def _parse_function_response(choice_message):
    function_call = None
    if isinstance(choice_message, dict):
        function_call = choice_message.get("function_call")
    else:
        function_call = getattr(choice_message, "function_call", None)

    if not function_call:
        raise ValueError("No function call returned from the LLM.")

    arguments = None
    if isinstance(function_call, dict):
        arguments = function_call.get("arguments")
    else:
        arguments = getattr(function_call, "arguments", None)

    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    return arguments


def reconcile_segments(tables=None, definitions=None, grounding_payload=None):
    """
    Reconcile segment labels across filings using OpenAI LLM or TF-IDF fallback.
    
    Args:
        tables: (deprecated) Dict of segment tables keyed by filename
        definitions: (deprecated) Dict of segment definitions keyed by filename
        grounding_payload: (preferred) Structured grounding object from build_grounding_payload()
        
    Returns:
        Tuple of (canonical_map, reconciliation_details)
    """
    # Handle the case where grounding_payload is provided (preferred path)
    if grounding_payload is not None:
        if not _openai_api_key():
            fallback = tfidf_match_segments(tables or {}, definitions or {})
            return (
                fallback,
                {
                    "summary": "OPENAI_API_KEY is not configured. Using TF-IDF fallback for segment reconciliation.",
                    "mapping": [],
                    "renames": [],
                },
            )

        # Use the grounding_payload directly
        context_json = json.dumps(grounding_payload, indent=2, ensure_ascii=False)
        
        user_prompt = (
            "Analyze the extracted segments from multiple SEC filings and produce a time-series reconciliation. "
            "Use the JSON context provided to identify canonical segment names, change types, and detailed rationale.\n\n"
            f"Context:\n{context_json}"
        )
    else:
        # Fallback path for backward compatibility with old calling style (tables, definitions)
        if not tables or not definitions:
            return {}, {"summary": "No filings or definitions available.", "mapping": [], "renames": []}

        if not _openai_api_key():
            fallback = tfidf_match_segments(tables, definitions)
            return (
                fallback,
                {
                    "summary": "OPENAI_API_KEY is not configured. Using TF-IDF fallback for segment reconciliation.",
                    "mapping": [],
                    "renames": [],
                },
            )

        # For backward compatibility, use the old _render_context
        context_json = _render_context(tables, definitions)
        
        user_prompt = (
            "Analyze the extracted segments from multiple SEC filings and produce a time-series reconciliation. "
            "Use the JSON context provided to identify canonical segment names, change types, and detailed rationale.\n\n"
            f"Context:\n{context_json}"
        )

    # Use the new OpenAI client (OpenAI.chat.completions.create)
    client = OpenAI(api_key=_openai_api_key())
    try:
        client = OpenAI(api_key=_openai_api_key())
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            functions=[FUNCTION_SCHEMA],
            function_call={"name": FUNCTION_SCHEMA["name"]},
            temperature=0.0,
        )
    except AuthenticationError as exc:
        fallback = tfidf_match_segments(tables or {}, definitions or {})
        return (
            fallback,
            {
                "summary": "OpenAI authentication failed. Using TF-IDF fallback. Please check OPENAI_API_KEY in Streamlit secrets.",
                "mapping": [],
                "renames": [],
                "error": str(exc),
            },
        )
    except OpenAIError as exc:
        fallback = tfidf_match_segments(tables or {}, definitions or {})
        return (
            fallback,
            {
                "summary": "OpenAI request failed. Using TF-IDF fallback.",
                "mapping": [],
                "renames": [],
                "error": str(exc),
            },
        )

    # Response is now a Pydantic model, not a dict
    choice = response.choices[0].message
    payload = _parse_function_response(choice)
    
    # Build a simple canonical map for backward compatibility with the app
    mappings = payload.get("mappings", [])
    canonical_map = {}
    for mapping in mappings:
        original_label = mapping.get("original_label")
        canonical_name = mapping.get("canonical_segment_name")
        if original_label and canonical_name:
            canonical_map[original_label] = canonical_name

    return canonical_map, {
        "canonical_segments": payload.get("canonical_segments", []),
        "mappings": mappings,
        "global_explanation": payload.get("global_explanation", ""),
        "summary": payload.get("global_explanation", "OpenAI provided reconciliation results."),
    }


def parse_reconcile_response(choice_message):
    return _parse_function_response(choice_message)
