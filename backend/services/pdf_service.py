"""Extract text from PDF/TXT files, keeping page numbers."""
from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pdf(path):
    """Return a list of {"page": n, "text": "..."} for pages that contain text."""
    try:
        reader = PdfReader(path)
        pages = []
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append({"page": number, "text": text})
        return pages, len(reader.pages)
    except (PdfReadError, Exception) as exc:
        raise ValueError("The PDF could not be read. It may be corrupted or encrypted.") from exc


def extract_txt(path):
    """A TXT file is treated as a single page."""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="ignore").strip()
    return ([{"page": 1, "text": text}] if text else []), 1


def extract_document(path, extension):
    pages, total = extract_pdf(path) if extension == ".pdf" else extract_txt(path)
    if not pages:
        raise ValueError("No extractable text found. The file is empty or a scanned image PDF.")
    return pages, total
