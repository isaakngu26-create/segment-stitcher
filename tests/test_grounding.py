"""
Unit tests for the grounding pipeline.
"""
import pytest
from datetime import datetime
from src.grounding.grounding_builder import (
    normalize_label,
    is_total_or_elimination,
    parse_number,
    build_grounding_payload,
)


class TestNormalization:
    """Test label and number normalization functions."""
    
    def test_normalize_label(self):
        """Test segment label normalization."""
        assert normalize_label("North America Consumer*") == "North America Consumer"
        assert normalize_label("  Europe   ") == "Europe"
        assert normalize_label("EMEA†") == "EMEA"
        assert normalize_label("Asia-Pacific(1)") == "Asia-Pacific"
        assert normalize_label("") == ""
        assert normalize_label("Multiple   Spaces") == "Multiple Spaces"
    
    def test_is_total_or_elimination(self):
        """Test detection of non-segment rows."""
        assert is_total_or_elimination("Total") == True
        assert is_total_or_elimination("Consolidated Total") == True
        assert is_total_or_elimination("Eliminations") == True
        assert is_total_or_elimination("Inter-segment eliminations") == True
        assert is_total_or_elimination("North America") == False
        assert is_total_or_elimination("Consumer") == False
        assert is_total_or_elimination("Corporate") == False
    
    def test_parse_number(self):
        """Test numeric value parsing."""
        assert parse_number("12,345.67") == 12345.67
        assert parse_number("(1,234)") == -1234.0
        assert parse_number("$5,000") == 5000.0
        assert parse_number("5000") == 5000.0
        assert parse_number(5000) == 5000.0
        assert parse_number("N/A") is None
        assert parse_number(None) is None
        assert parse_number("") is None
        assert parse_number("-1000") == -1000.0


class TestGroundingPayload:
    """Test grounding payload construction."""
    
    def test_build_grounding_payload_basic(self):
        """Test basic grounding payload construction."""
        filings = [
            {
                "filename": "2022 10-K.pdf",
                "company": "Apple Inc.",
                "period": "December 31, 2022",
                "form_type": "10-K",
            }
        ]
        
        segment_tables = {
            "2022 10-K.pdf": {
                "segments": ["iPhone", "Services", "Other"],
                "values": [71000, 68000, 28000],
                "raw_segments": [
                    {
                        "label_raw": "iPhone",
                        "revenue_raw": "71000",
                    },
                    {
                        "label_raw": "Services",
                        "revenue_raw": "68000",
                    },
                    {
                        "label_raw": "Other",
                        "revenue_raw": "28000",
                    },
                ],
            }
        }
        
        payload = build_grounding_payload("Apple Inc.", filings, segment_tables)
        
        assert payload["company_name"] == "Apple Inc."
        assert len(payload["filings"]) == 1
        assert payload["filings"][0]["filing_id"] == "December 31, 2022 10-K"
        assert len(payload["filings"][0]["segments"]) == 3
        assert payload["filings"][0]["segments"][0]["label"] == "iPhone"
        assert payload["filings"][0]["segments"][0]["revenue"] == 71000.0
    
    def test_build_grounding_payload_filters_totals(self):
        """Test that totals are filtered from segments."""
        filings = [
            {
                "filename": "2022 10-K.pdf",
                "company": "Apple Inc.",
                "period": "December 31, 2022",
                "form_type": "10-K",
            }
        ]
        
        segment_tables = {
            "2022 10-K.pdf": {
                "segments": ["iPhone", "Total"],
                "values": [71000, 167000],
                "raw_segments": [
                    {
                        "label_raw": "iPhone",
                        "revenue_raw": "71000",
                    },
                    {
                        "label_raw": "Total",
                        "revenue_raw": "167000",
                    },
                ],
            }
        }
        
        payload = build_grounding_payload("Apple Inc.", filings, segment_tables)
        
        # Total should be filtered out
        assert len(payload["filings"][0]["segments"]) == 1
        assert payload["filings"][0]["segments"][0]["label"] == "iPhone"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
