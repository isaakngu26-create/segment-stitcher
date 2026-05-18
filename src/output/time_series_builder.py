import pandas as pd


def build_time_series(filings, tables, matches):
    rows = []

    for filing in filings:
        filename = filing["filename"]
        row = {
            "filing": filename,
            "period": filing.get("period", "Unknown"),
            "form_type": filing.get("form_type", "Unknown"),
        }

        table = tables.get(filename, {})
        for segment, value in zip(table.get("segments", []), table.get("values", [])):
            canonical = matches.get(segment, segment)
            row[canonical] = row.get(canonical, 0.0) + value

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    numeric_cols = [col for col in df.columns if col not in {"filing", "period", "form_type"}]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.fillna("")
