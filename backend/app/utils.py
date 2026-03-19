"""Shared helper functions — extracted from main.py without modification."""

import io
import logging

import docx
import fitz  # PyMuPDF
from fastapi import UploadFile

logger = logging.getLogger(__name__)

ALLOWED_MIME_PREFIXES = ("audio/", "video/webm")
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


async def extract_text_from_upload(upload_file: UploadFile) -> str:
    """Helper purely to abstract PyMuPDF/docx/text extraction."""
    await upload_file.seek(0)
    file_bytes = await upload_file.read()
    if len(file_bytes) == 0:
        return ""

    content_type = upload_file.content_type or ""
    filename = upload_file.filename.lower() if upload_file.filename else ""
    text = ""

    if content_type == "application/pdf" or filename.endswith(".pdf"):
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text()
        except Exception as exc:
            logger.error(f"Erreur d'extraction d'un PDF: {exc}")
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.endswith(".docx"):
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as exc:
            logger.error(f"Erreur d'extraction d'un fichier DOCX: {exc}")
    else:
        try:
            text = file_bytes.decode("utf-8")
        except Exception:
            text = ""
    return text.strip()


def make_offer_snippet(job_offer: str, max_len: int = 200) -> str:
    """Create a short snippet from a job offer for display in lists."""
    snippet = job_offer.strip().replace("\n", " ")[:max_len]
    if len(job_offer.strip()) > max_len:
        snippet += "…"
    return snippet


def make_interview_title(job_offer: str) -> str:
    """Generate a title for an interview report from the job offer text."""
    first_line = job_offer.strip().split("\n")[0].strip()[:100]
    if first_line:
        return f"Entretien — {first_line}"
    return "Entretien"
