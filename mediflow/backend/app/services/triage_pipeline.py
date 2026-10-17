# Agregado por Edil: conecta la recepción de Drazen con Gemini y validación,
# reutilizando el cliente OCI de Eliana. No mueve ni elimina documentos.
"""Integración de Sprint 2: archivo en memoria -> IA -> contrato validado."""

from .gemini_client import GeminiClinicalClient
from pathlib import PurePosixPath
from .document_text import extract_document_text
from .llm_errors import OCRRequiredError
from .servicio_orquestador import procesar_con_orquestador
from app.models.schemas import TriageResponse


def analyze_received_document(content: bytes, filename: str, document_id: str, storage: dict):
    """El archivo ya se guardó en recibidos; storage describe esa operación real."""
    with GeminiClinicalClient() as client:
        # Agregado por Edil: conservar la extracción Gemini y aplicar después
        # las entregas de Eliana/Nicolás/Laura, sin otro proveedor ni otra llamada.
        # Antes: return client.process_document(...)
        extracted = client.process_document(
            content, filename, document_id=document_id, storage=storage
        )
    source_text = None
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if suffix in {".txt", ".pdf"}:
        try:
            source_text = extract_document_text(content, filename)
        except OCRRequiredError:
            # El PDF escaneado se analizó como media nativa. No inventar texto OCR.
            pass
    routed = procesar_con_orquestador(extracted.model_dump(), source_text=source_text)
    return TriageResponse.model_validate(routed, strict=True)
