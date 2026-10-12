# Agregado por Edil: completa el módulo LLM pendiente; conserva las entregas previas.
"""PDF y TXT sintéticos en memoria. No OCI, OCR ni Gemini real."""

from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from app.services.document_text import extract_document_text
from app.services.llm_errors import DocumentExtractionError, LLMInputError, OCRRequiredError


def pdf_bytes(*, text=False, encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    if text:
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({
                NameObject("/F1"): DictionaryObject({
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                })
            })
        })
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 200 Td (Documento sintetico para prueba.) Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("unit-test-only")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_txt_utf8_bom_and_whitespace():
    assert extract_document_text(b"\xef\xbb\xbf  Nota ficticia.  ", "test.TXT") == "Nota ficticia."


def test_pdf_with_text():
    assert "Documento sintetico" in extract_document_text(pdf_bytes(text=True), "test.pdf")


def test_scanned_or_blank_pdf_requires_ocr():
    with pytest.raises(OCRRequiredError):
        extract_document_text(pdf_bytes(), "scan.pdf")


def test_encrypted_pdf_is_controlled():
    with pytest.raises(DocumentExtractionError):
        extract_document_text(pdf_bytes(encrypted=True), "test.pdf")


@pytest.mark.parametrize("data,name", [
    (b"", "empty.txt"), (b" \n ", "empty.txt"),
    (b"\xff", "invalid.txt"), (b"not-a-pdf", "invalid.pdf"),
    (b"image", "test.jpg"), (b"image", "test.png"), (b"binary", "test.exe"),
])
def test_invalid_inputs_are_controlled(data, name):
    with pytest.raises(LLMInputError):
        extract_document_text(data, name)


def test_file_too_large():
    with pytest.raises(DocumentExtractionError):
        extract_document_text(b"x" * (10 * 1024 * 1024 + 1), "large.txt")

def test_txt_text_limit_is_enforced():
    with pytest.raises(LLMInputError):
        extract_document_text(b"x" * 80_001, "large.txt")


def test_pdf_page_limit_is_enforced():
    writer = PdfWriter()
    for _ in range(101):
        writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(DocumentExtractionError):
        extract_document_text(output.getvalue(), "too-many-pages.pdf")


def test_embedded_nul_is_not_treated_as_text():
    with pytest.raises(LLMInputError):
        extract_document_text(b"synthetic\x00binary", "binary.txt")
