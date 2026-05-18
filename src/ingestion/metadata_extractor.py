import re


FORM_PATTERN = re.compile(r"\b(10[- ]?K|10[- ]?Q|8[- ]?K|S-1|S-4|20-F|40-F)\b", re.I)
PERIOD_PATTERN = re.compile(
    r"for the (?:fiscal )?(year|quarter) ended\s+([A-Za-z0-9,\s]+)|Q([1-4])\s*(\d{4})", re.I
)


def extract_metadata(text):
    form_type = "Unknown"
    period = "Unknown"

    form_match = FORM_PATTERN.search(text)
    if form_match:
        form_type = form_match.group(1).upper().replace(" ", "-")

    period_match = PERIOD_PATTERN.search(text)
    if period_match:
        period = period_match.group(2) or f"Q{period_match.group(3)} {period_match.group(4)}"
        period = period.strip() if period else "Unknown"

    return {
        "form_type": form_type,
        "period": period,
    }
