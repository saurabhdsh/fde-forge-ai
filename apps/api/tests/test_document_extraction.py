"""Document extraction unit tests."""

from app.services.document_extraction import DocumentExtractionService


def test_extract_txt() -> None:
    service = DocumentExtractionService()
    text = service.extract(data=b"Python engineer with FHIR experience", file_extension="txt")
    assert "Python" in text
    assert "FHIR" in text
