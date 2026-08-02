"""Real document text extraction for resumes."""

from __future__ import annotations

import io

import fitz  # PyMuPDF
from docx import Document

from app.core.exceptions import ValidationAppError


class DocumentExtractionService:
    def extract(self, *, data: bytes, file_extension: str) -> str:
        ext = file_extension.lower().lstrip(".")
        if ext == "pdf":
            return self._extract_pdf(data)
        if ext == "docx":
            return self._extract_docx(data)
        if ext in {"txt", "md"}:
            return data.decode("utf-8", errors="ignore").strip()
        raise ValidationAppError(
            f"Unsupported file type for extraction: {ext}",
            details={"allowed": ["pdf", "docx", "txt", "md"]},
        )

    def _extract_pdf(self, data: bytes) -> str:
        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                parts = [page.get_text("text") for page in doc]
            text = "\n".join(parts).strip()
        except Exception as exc:  # noqa: BLE001
            raise ValidationAppError(
                "Unable to extract text from PDF",
                details={"error": str(exc)},
            ) from exc
        if not text:
            raise ValidationAppError("PDF contained no extractable text")
        return text

    def _extract_docx(self, data: bytes) -> str:
        try:
            document = Document(io.BytesIO(data))
            parts = [p.text for p in document.paragraphs if p.text and p.text.strip()]
            text = "\n".join(parts).strip()
        except Exception as exc:  # noqa: BLE001
            raise ValidationAppError(
                "Unable to extract text from DOCX",
                details={"error": str(exc)},
            ) from exc
        if not text:
            raise ValidationAppError("DOCX contained no extractable text")
        return text
