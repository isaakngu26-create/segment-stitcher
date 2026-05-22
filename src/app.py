import pandas as pd
import streamlit as st
from ingestion.pdf_loader import load_pdfs
from ingestion.metadata_extractor import extract_metadata
from extraction.table_extractor import extract_segment_tables
from extraction.definition_extractor import extract_definitions
from reconciliation import reconcile_segments
from reconciliation.change_detector import detect_changes
from output.time_series_builder import build_time_series
from output.exporter import get_csv_bytes

st.set_page_config(page_title="SegmentStitcher", layout="wide")

st.title("SegmentStitcher")
st.markdown("Automatically extract segment reporting and reconcile segment definitions across filings.")

uploaded_files = st.file_uploader("Upload SEC filings (PDF)", accept_multiple_files=True, type=["pdf"])

if uploaded_files:
    filings = load_pdfs(uploaded_files)

    for filing in filings:
        metadata = extract_metadata(filing["text"])
        filing.update(metadata)

    segment_tables = extract_segment_tables(filings)
    definitions = extract_definitions(filings)
    matches, reconciliation = reconcile_segments(segment_tables, definitions)
    changes = detect_changes(filings, definitions)
    time_series = build_time_series(filings, segment_tables, matches)

    st.subheader("Extracted filings")
    st.write(pd.DataFrame([{
        "filename": filing["filename"],
        "period": filing.get("period", "Unknown"),
        "form_type": filing.get("form_type", "Unknown")
    } for filing in filings]))

    st.subheader("Segment definitions detected")
    for filename, defs in definitions.items():
        st.markdown(f"**{filename}**")
        st.write(defs)

    st.subheader("Reconciliation reasoning")
    st.write(reconciliation.get("summary", ""))
    if reconciliation.get("mapping"):
        st.table(pd.DataFrame(reconciliation["mapping"]))
    if reconciliation.get("renames"):
        st.markdown("**Detected renames and aliases**")
        st.table(pd.DataFrame(reconciliation["renames"]))

    st.subheader("Detected segment definition changes")
    if changes:
        st.json(changes)
    else:
        st.info("No material definition changes detected across the uploaded filings.")

    st.subheader("Reconciled time-series")
    st.dataframe(time_series)

    csv_bytes = get_csv_bytes(time_series)
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name="segment_stitcher_output.csv",
        mime="text/csv"
    )
else:
    st.info("Upload one or more SEC filing PDFs to begin.")
