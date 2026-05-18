import re

DEFINITION_PATTERN = re.compile(
    r"([A-Z][A-Za-z0-9 &/\-]{2,80})\s*(?:[:\u2013\u2014\-–—]|\(|—)\s*([A-Z][^\n\.]{10,200})",
    re.M,
)


def extract_definitions(filings):
    definitions = {}

    for filing in filings:
        matches = {}
        text = filing["text"]

        for header, definition in DEFINITION_PATTERN.findall(text):
            clean_header = header.strip()
            clean_definition = definition.strip().rstrip(".")
            if len(clean_header) > 1 and len(clean_definition) > 10:
                matches[clean_header] = clean_definition

        if not matches:
            for line in text.splitlines():
                if re.search(r"(segment|reporting unit|business segment|operating segment)", line, re.I):
                    parts = [part.strip() for part in re.split(r"[:\-–—]", line, 1) if part.strip()]
                    if len(parts) == 2:
                        matches[parts[0]] = parts[1]

        definitions[filing["filename"]] = matches

    return definitions
