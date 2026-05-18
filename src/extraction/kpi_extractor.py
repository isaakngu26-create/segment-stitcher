import re

KPI_PATTERN = re.compile(r"\b(EBITDA|Revenue|Operating Income|Gross Profit|Net Income|Segment Margin)\b", re.I)


def extract_kpis(text):
    kpis = []
    for match in KPI_PATTERN.finditer(text):
        kpis.append(match.group(1))
    return list(dict.fromkeys(kpis))


def extract_kpi_tables(filings):
    results = {}
    for filing in filings:
        results[filing["filename"]] = extract_kpis(filing["text"])
    return results
