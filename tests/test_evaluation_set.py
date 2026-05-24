import json


def test_evaluation_dataset_is_valid():
    with open("data/evaluation/segment_reconciliation.json", "r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert isinstance(data, dict)
    assert "items" in data
    assert len(data["items"]) > 0
    example = data["items"][0]
    assert "filings" in example
    assert "expected_mapping" in example
    assert "expected_renames" in example
