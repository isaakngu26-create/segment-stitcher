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

        findings[filing["filename"]] = {
            "segments": segments,
            "values": values,
        }

    return findings
