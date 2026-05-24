import io
import re
import pdfplumber

NUMERIC_PATTERN = re.compile(r"[-+]?[0-9]{1,3}(?:[,\d]*)(?:\.\d+)?")


def _parse_value(cell_text):
    if not cell_text:
        return None
    cleaned = cell_text.replace("$", "").replace("(", "-").replace(")", "")
    cleaned = cleaned.replace(",", "")
    match = NUMERIC_PATTERN.search(cleaned)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def extract_segment_tables(filings):
    findings = {}

    for filing in filings:
        segments = []
        values = []
        raw_segments = []  # Store raw segment dicts for grounding

        with pdfplumber.open(io.BytesIO(filing["raw_bytes"])) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    if not table:
                        continue

                    for row in table:
                        if not row or len(row) < 2:
                            continue

                        segment = row[0].strip() if row[0] else ""
                        if not segment or len(segment) < 3:
                            continue

                        numeric_value = None
                        for candidate in row[1:]:
                            value = _parse_value(candidate if candidate else "")
                            if value is not None:
                                numeric_value = value
                                break

                        if numeric_value is not None:
                            segments.append(segment)
                            values.append(numeric_value)
                            
                            # Store raw segment data for grounding
                            raw_segment = {
                                "label_raw": segment,
                                "revenue_raw": str(numeric_value),
                            }
                            # Store additional columns if available
                            for idx, cell in enumerate(row[1:], 1):
                                if cell and idx < len(row):
                                    raw_segment[f"column_{idx}"] = cell
                            raw_segments.append(raw_segment)

        if not segments:
            # fallback: find segment headers from raw text
            for line in filing["text"].splitlines():
                if re.search(r"segment|reporting unit|business segment|geographic", line, re.I):
                    tokens = [token.strip() for token in re.split(r"\s{2,}|\t", line) if token.strip()]
                    if len(tokens) >= 2:
                        value = _parse_value(tokens[-1])
                        if value is not None:
                            segments.append(tokens[0])
                            values.append(value)
                            raw_segments.append({
                                "label_raw": tokens[0],
                                "revenue_raw": str(value),
                            })

        findings[filing["filename"]] = {
            "segments": segments,
            "values": values,
            "raw_segments": raw_segments,
        }

    return findings
