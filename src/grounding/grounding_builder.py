"""
Build a normalized, structured grounding payload for LLM segment reconciliation.

Pipeline:
1. Normalize segment labels (remove whitespace, footnote markers)
2. Parse numeric values (remove currency, commas, parentheses)
3. Filter out non-segment rows (totals, eliminations)
4. Enrich with metadata and metrics
5. Assemble into model-ready JSON
6. Optionally retrieve prior canonical segments
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


# ============================================================================
# Normalization Functions
# ============================================================================

def normalize_label(label: str) -> str:
    """
    Normalize a segment label by removing whitespace, footnote markers, etc.
    
    Examples:
        "North America Consumer*" -> "North America Consumer"
        "  Europe   " -> "Europe"
        "EMEA†" -> "EMEA"
    """
    if not label:
        return ""
    
    # Strip leading/trailing whitespace
    label = label.strip()
    
    # Remove footnote markers and superscripts
    label = re.sub(r'[*†‡§¶†‡]|\([0-9]+\)$', '', label)
    
    # Collapse multiple spaces
    label = re.sub(r'\s+', ' ', label)
    
    return label.strip()


def is_total_or_elimination(label: str) -> bool:
    """
    Determine if a segment label is a total, elimination, or non-segment row.
    
    Examples:
        "Total" -> True
        "Consolidated Total" -> True
        "Eliminations" -> True
        "Corporate" -> False (may be a valid segment)
        "North America" -> False
    """
    normalized = label.lower()
    
    # Patterns that indicate non-segment rows
    non_segment_patterns = [
        r'^\s*total',
        r'^\s*consolidated',
        r'^\s*eliminations?',
        r'^\s*inter-?segment',
        r'^\s*adjustments?',
        r'^\s*unallocated',
        r'^\s*all other',
    ]
    
    for pattern in non_segment_patterns:
        if re.search(pattern, normalized):
            return True
    
    return False


def parse_number(value: Any) -> Optional[float]:
    """
    Parse a value (string or number) into a float, handling common formatting.
    
    Examples:
        "12,345.67" -> 12345.67
        "(1,234)" -> -1234.0
        "$5,000" -> 5000.0
        "N/A" -> None
        None -> None
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    
    # If already a number, try to convert
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    # Convert to string and clean
    if not isinstance(value, str):
        value = str(value)
    
    value = value.strip()
    if not value or value.lower() in ['n/a', 'na', 'n.a.', '-', '—', 'n.m.']:
        return None
    
    # Check for negative (parentheses notation)
    is_negative = value.startswith('(') and value.endswith(')')
    
    # Remove currency symbols, commas, parentheses
    cleaned = value.replace('$', '').replace('€', '').replace('£', '')
    cleaned = cleaned.replace(',', '').replace('(', '').replace(')', '')
    cleaned = cleaned.strip()
    
    try:
        result = float(cleaned)
        return -result if is_negative else result
    except ValueError:
        return None


def extract_numeric_fields(row: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    Extract numeric fields from a row dict, looking for common column names.
    
    Returns:
        {
            "revenue": float or None,
            "operating_income": float or None,
            "other_metrics": {additional numeric fields}
        }
    """
    revenue = None
    operating_income = None
    other_metrics = {}
    
    # Common patterns for revenue
    revenue_patterns = ['revenue', 'sales', 'net revenue', 'operating revenue']
    # Common patterns for operating income
    op_income_patterns = ['operating income', 'operating profit', 'operating earnings', 'ebit']
    # Patterns to skip
    skip_patterns = ['label', 'segment', 'label_raw', 'segment_order']
    
    for key, value in row.items():
        if key in skip_patterns:
            continue
        
        key_lower = key.lower()
        parsed = parse_number(value)
        
        if parsed is None:
            continue
        
        # Handle raw field names specifically
        if key == 'revenue_raw':
            revenue = parsed
        elif key == 'operating_income_raw':
            operating_income = parsed
        # Match revenue
        elif any(pattern in key_lower for pattern in revenue_patterns):
            revenue = parsed
        # Match operating income
        elif any(pattern in key_lower for pattern in op_income_patterns):
            operating_income = parsed
        # Store other metrics
        elif key.startswith('column_'):
            # Skip extracted column data from table parsing
            continue
        else:
            other_metrics[key] = parsed
    
    return {
        "revenue": revenue,
        "operating_income": operating_income,
        "other_metrics": other_metrics,
    }


# ============================================================================
# Grounding Payload Builder
# ============================================================================

def build_grounding_payload(
    company_name: str,
    filings: List[Dict[str, Any]],
    segment_tables: Dict[str, Dict[str, Any]],
    prior_canonical_segments: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Build a normalized, structured grounding payload for LLM segment reconciliation.
    
    Args:
        company_name: Name of the company (e.g., "Apple Inc.")
        filings: List of filing dicts with metadata (filename, period, form_type, etc.)
        segment_tables: Output from extract_segment_tables(), keyed by filename
        prior_canonical_segments: Optional list of canonical segments from previous run
        
    Returns:
        Grounding payload dict with:
        {
            "company_name": str,
            "filings": [
                {
                    "filing_id": str (e.g., "2022 10-K"),
                    "period_end": str (ISO date),
                    "segments": [
                        {
                            "label": str,
                            "revenue": float or None,
                            "operating_income": float or None,
                            "other_metrics": {
                                "segment_order": int,
                                ... other fields
                            }
                        }
                    ]
                }
            ],
            "prior_canonical_segments": [...] (if provided)
        }
    """
    structured_filings = []
    
    # Build a mapping from filename to filing metadata for quick lookup
    filing_by_name = {}
    for filing in filings:
        filing_by_name[filing.get("filename", "")] = filing
    
    # Process each filing's segment table
    for filename, table_data in segment_tables.items():
        filing_meta = filing_by_name.get(filename, {})
        
        # Build filing_id (e.g., "2022 10-K")
        period = filing_meta.get("period", "Unknown")
        form_type = filing_meta.get("form_type", "").upper()
        filing_id = f"{period} {form_type}".strip()
        if not form_type:
            filing_id = filename
        
        # Parse period_end (convert period string to ISO date if possible)
        period_end = _parse_period_to_iso(filing_meta.get("period", ""))
        
        # Extract and normalize segments
        segments = []
        segment_list = table_data.get("segments", [])
        raw_segments = table_data.get("raw_segments", [])
        
        # If we have raw_segments (detailed dicts), use those; otherwise reconstruct
        if raw_segments and isinstance(raw_segments[0], dict):
            # Use the detailed raw segment data
            for idx, raw_segment in enumerate(raw_segments):
                label = normalize_label(raw_segment.get("label_raw", ""))
                
                # Skip non-segment rows
                if not label or is_total_or_elimination(label):
                    continue
                
                # Extract metrics
                metrics = extract_numeric_fields(raw_segment)
                
                segment_obj = {
                    "label": label,
                    "revenue": metrics["revenue"],
                    "operating_income": metrics["operating_income"],
                    "other_metrics": {
                        **metrics["other_metrics"],
                        "segment_order": idx,
                    },
                }
                segments.append(segment_obj)
        else:
            # Fallback: reconstruct from simple lists
            values = table_data.get("values", [])
            for idx, segment_label in enumerate(segment_list):
                label = normalize_label(segment_label)
                
                # Skip non-segment rows
                if not label or is_total_or_elimination(label):
                    continue
                
                revenue = values[idx] if idx < len(values) else None
                
                segment_obj = {
                    "label": label,
                    "revenue": parse_number(revenue),
                    "operating_income": None,
                    "other_metrics": {
                        "segment_order": idx,
                    },
                }
                segments.append(segment_obj)
        
        # Add this filing to the payload
        filing_obj = {
            "filing_id": filing_id,
            "period_end": period_end,
            "segments": segments,
        }
        structured_filings.append(filing_obj)
    
    # Sort filings by period_end (oldest first)
    structured_filings.sort(key=lambda f: f["period_end"] or "0000-00-00")
    
    # Build final payload
    payload = {
        "company_name": company_name,
        "filings": structured_filings,
    }
    
    # Optionally include prior canonical segments for continuity
    if prior_canonical_segments:
        payload["prior_canonical_segments"] = prior_canonical_segments
    
    return payload


# ============================================================================
# Helper Functions
# ============================================================================

def _parse_period_to_iso(period_str: str) -> str:
    """
    Convert a period string (e.g., "December 31, 2022") to ISO date format.
    
    Falls back to "Unknown" if parsing fails.
    """
    if not period_str or period_str == "Unknown":
        return "Unknown"
    
    # Try common formats
    formats = [
        "%B %d, %Y",      # "December 31, 2022"
        "%b %d, %Y",      # "Dec 31, 2022"
        "%m/%d/%Y",       # "12/31/2022"
        "%d-%m-%Y",       # "31-12-2022"
        "%Y-%m-%d",       # "2022-12-31" (already ISO)
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(period_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    return period_str  # Return original if no format matches


def infer_company_name_from_filings(filings: List[Dict[str, Any]]) -> str:
    """
    Infer company name from filing metadata (company field if available).
    
    Falls back to generic "Unknown Company".
    """
    for filing in filings:
        if filing.get("company"):
            return filing["company"]
    
    return "Unknown Company"
