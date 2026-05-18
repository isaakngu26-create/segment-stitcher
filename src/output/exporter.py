
def get_csv_bytes(df):
    if df is None or df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")
