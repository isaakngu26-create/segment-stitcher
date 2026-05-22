from reconciliation.llm_reconciler import reconcile_segments


def test_reconcile_segments_fallback_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    tables = {"example.pdf": {"segments": ["Cloud"], "values": [100]}}
    definitions = {"example.pdf": {"Cloud": "Cloud infrastructure and services."}}

    mapping, context = reconcile_segments(tables, definitions)

    assert mapping["Cloud"] == "Cloud"
    assert "OPENAI_API_KEY" in context["summary"]
