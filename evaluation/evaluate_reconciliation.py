import argparse
import json
import os

from src.reconciliation.llm_reconciler import reconcile_segments


def load_evaluation_set(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def build_input(item):
    tables = {}
    definitions = {}
    for filing in item["filings"]:
        tables[filing["filename"]] = {
            "segments": filing.get("segments", []),
            "rows": filing.get("rows", []),
        }
        definitions[filing["filename"]] = filing.get("definitions", {})
    return tables, definitions


def expected_map(item):
    return {
        (row["filing"], row["segment"]): row["canonical"]
        for row in item.get("expected_mapping", [])
    }


def score_mapping(predicted, expected):
    total = len(expected)
    correct = 0
    for key, expected_value in expected.items():
        if predicted.get(key[1]) == expected_value:
            correct += 1
    return correct, total


def run_evaluation(path):
    data = load_evaluation_set(path)
    print(f"Evaluation: {data.get('description', 'Unnamed set')}")
    print(f"OpenAI key present: {'OPENAI_API_KEY' in os.environ}")

    for item in data.get("items", []):
        print(f"\nRunning item: {item['id']}")
        tables, definitions = build_input(item)
        predicted, metadata = reconcile_segments(tables, definitions)
        expected = expected_map(item)

        correct, total = score_mapping(predicted, expected)
        accuracy = correct / total if total else 0.0

        print(f"  Summary: {metadata.get('summary')}")
        print(f"  Expected mapping count: {total}")
        print(f"  Correct canonical labels: {correct}/{total} ({accuracy:.0%})")
        print("  Predicted mapping:")
        for filing_segment, canonical in predicted.items():
            print(f"    {filing_segment} -> {canonical}")

    print("\nEvaluation complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate segment reconciliation predictions.")
    parser.add_argument(
        "path",
        nargs="?",
        default="data/evaluation/segment_reconciliation.json",
        help="Path to the evaluation JSON file.",
    )
    args = parser.parse_args()
    run_evaluation(args.path)
