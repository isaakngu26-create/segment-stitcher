import json
import os

try:
    import openai
except ImportError:
    openai = None

from .semantic_matcher import match_segments as tfidf_match_segments

SYSTEM_PROMPT = """
You are an expert financial analyst specializing in SEC segment reporting.
You will receive segment names and segment definitions extracted from multiple filings.
Use those definitions to identify canonical segment labels, detect value renames, and explain the reasoning in plain English.
Return the result via the defined function schema only, without extra prose.
"""

FUNCTION_SCHEMA = {
    "name": "reconcile_segments",
    "description": "Map segment labels to canonical names and identify renames across filings.",
    "parameters": {
        "type": "object",
        "properties": {
            "mapping": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "filing": {"type": "string"},
                        "segment": {"type": "string"},
                        "canonical": {"type": "string"},
                        "confidence": {"type": "number"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["filing", "segment", "canonical", "confidence", "rationale"],
                },
            },
            "renames": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "from_segment": {"type": "string"},
                        "to_segment": {"type": "string"},
                        "from_filing": {"type": "string"},
                        "to_filing": {"type": "string"},
                        "explanation": {"type": "string"},
                    },
                    "required": ["from_segment", "to_segment", "from_filing", "to_filing", "explanation"],
                },
            },
            "summary": {"type": "string"},
        },
        "required": ["mapping"],
    },
}


def _openai_api_key():
    if openai is None:
        return None
    key = os.getenv("OPENAI_API_KEY")
    if key:
        openai.api_key = key
    return key


def _render_context(tables, definitions):
    filings = []
    for filename, table in tables.items():
        filings.append({
            "filename": filename,
            "segments": table.get("segments", []),
        })

    definition_list = []
    for filename, defs in definitions.items():
        for label, definition in defs.items():
            definition_list.append({
                "filename": filename,
                "label": label,
                "definition": definition,
            })

    return json.dumps(
        {
            "filings": filings,
            "definitions": definition_list,
        },
        indent=2,
        ensure_ascii=False,
    )


def _parse_function_response(choice_message):
    function_call = choice_message.get("function_call")
    if not function_call:
        raise ValueError("No function call returned from the LLM.")
    return json.loads(function_call["arguments"])


def reconcile_segments(tables, definitions):
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

    user_prompt = (
        "Map the segment names in the filings to canonical segment names using the definitions. "
        "If a segment name is a rename or alias of another filing's segment, use the same canonical label. "
        "If no safe match exists, preserve the original segment label. "
        "Return the JSON payload using the declared function schema only.\n\n"
        f"Context:\n{_render_context(tables, definitions)}"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        functions=[FUNCTION_SCHEMA],
        function_call={"name": FUNCTION_SCHEMA["name"]},
        temperature=0.0,
    )

    choice = response["choices"][0]["message"]
    payload = _parse_function_response(choice)
    mapping_outputs = payload.get("mapping", [])
    canonical_map = {
        item["segment"]: item["canonical"] for item in mapping_outputs
    }

    return canonical_map, {
        "summary": payload.get("summary", "OpenAI provided reconciliation results."),
        "mapping": mapping_outputs,
        "renames": payload.get("renames", []),
    }


def parse_reconcile_response(choice_message):
    return _parse_function_response(choice_message)
