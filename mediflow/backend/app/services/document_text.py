# Agregado por Edil: completa el módulo LLM pendiente; conserva las entregas previas.
"""Extracción básica local, independiente de Gemini y de Object Storage."""

from io import BytesIO
from pathlib import PurePosixPath

from pypdf import PdfReader

from .llm_errors import DocumentExtractionError, LLMInputError, OCRRequiredError

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 80_000
MAX_PDF_PAGES = 100


def validate_document_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise LLMInputError("El documento está vacío.")
    if len(text) > MAX_TEXT_CHARS:
        raise LLMInputError("El documento supera el límite de texto permitido.")
    if "\x00" in text:
        raise LLMInputError("El contenido no es texto válido.")
    return text.strip()


def extract_document_text(content: bytes, filename: str) -> str:
    """Lee TXT UTF-8 o PDF con texto. No hace OCR ni accede a rutas del usuario."""
    if not isinstance(content, bytes) or not content:
        raise DocumentExtractionError("El documento está vacío.")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise DocumentExtractionError("El documento supera el límite de 10 MiB.")
    if not isinstance(filename, str):
        raise DocumentExtractionError("El formato del documento no es válido.")
    extension = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if extension == ".txt":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise DocumentExtractionError("El TXT debe estar codificado en UTF-8.") from None
    elif extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise DocumentExtractionError("El archivo no es un PDF válido.")
        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise DocumentExtractionError("No se admiten PDF cifrados.")
            if len(reader.pages) > MAX_PDF_PAGES:
                raise DocumentExtractionError("El PDF supera el límite de páginas.")
            parts = []
            total = 0
            for page in reader.pages:
                part = page.extract_text() or ""
                total += len(part) + 1
                if total > MAX_TEXT_CHARS:
                    raise DocumentExtractionError("El PDF supera el límite de texto.")
                parts.append(part)
            text = "\n".join(parts)
        except DocumentExtractionError:
            raise
        except Exception:
            raise DocumentExtractionError("No se pudo extraer el texto del PDF.") from None
        if not text.strip():
            raise OCRRequiredError("El PDF no contiene texto extraíble; requiere OCR.")
    else:
        raise DocumentExtractionError(
            "Este módulo admite TXT y PDF con texto. Imágenes requieren OCR."
        )
    return validate_document_text(text)
