import io
import pdfplumber


def load_pdfs(files):
    filings = []

    for uploaded_file in files:
        raw_bytes = uploaded_file.read()
        pages = []

        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")

        filings.append({
            "filename": uploaded_file.name,
            "raw_bytes": raw_bytes,
            "pages": pages,
            "text": "\n".join(pages),
        })

    return filings
