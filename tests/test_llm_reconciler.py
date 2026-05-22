import json

from reconciliation.llm_reconciler import parse_reconcile_response


def test_parse_reconcile_response():
    example_message = {
        "function_call": {
            "name": "reconcile_segments",
            "arguments": json.dumps(
                {
                    "mapping": [
                        {
                            "filing": "filing1.pdf",
                            "segment": "Cloud",
                            "canonical": "Infrastructure & Cloud",
                            "confidence": 0.92,
                            "rationale": "The definition refers to distributed cloud infrastructure and matches the product-level reporting.",
                        }
                    ],
                    "renames": [
                        {
                            "from_segment": "Cloud",
                            "to_segment": "Infrastructure & Cloud",
                            "from_filing": "filing1.pdf",
                            "to_filing": "filing2.pdf",
                            "explanation": "Cloud appears to be an alias for Infrastructure in the later filing.",
                        }
                    ],
                    "summary": "Mapped Cloud to Infrastructure & Cloud for consistent reporting.",
                }
            ),
        }
    }

    payload = parse_reconcile_response(example_message)
    assert payload["mapping"][0]["canonical"] == "Infrastructure & Cloud"
    assert payload["renames"][0]["from_segment"] == "Cloud"
