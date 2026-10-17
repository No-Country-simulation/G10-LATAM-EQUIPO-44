# Agregado por Edil: conecta la recepción de Drazen con Gemini y validación,
# reutilizando el cliente OCI de Eliana. No mueve ni elimina documentos.
"""Integración de Sprint 2: archivo en memoria -> IA -> contrato validado."""

from .gemini_client import GeminiClinicalClient
from pathlib import PurePosixPath
from .document_text import extract_document_text
from .llm_errors import OCRRequiredError, LLMConfigurationError
from .servicio_orquestador import procesar_con_orquestador
from app.models.schemas import TriageResponse
from data_ai.synthetic_demo_rules import rules_profile


def analyze_received_document(content: bytes, filename: str, document_id: str, storage: dict):
    """El archivo ya se guardó en recibidos; storage describe esa operación real."""
    source_text = None
    try:
        demo = rules_profile() == "synthetic_demo_v1"
    except ValueError:
        raise LLMConfigurationError("El perfil de reglas no está configurado correctamente.") from None
    with GeminiClinicalClient() as client:
        # Agregado por Edil: conservar la extracción Gemini y aplicar después
        # las entregas de Eliana/Nicolás/Laura, sin otro proveedor ni otra llamada.
        # Antes: return client.process_document(...)
        # Agregado por Edil: antes la imagen solo dejaba un diagnóstico resumido.
        # En demo se conserva transcripción interna de la misma generación.
        # El modo general conserva la llamada y comportamiento anteriores.
        if demo:
            extracted, source_text = client.process_document_with_source(
                content, filename, document_id=document_id, storage=storage
            )
        else:
            extracted = client.process_document(
                content, filename, document_id=document_id, storage=storage
            )
    suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
    if not demo and suffix in {".txt", ".pdf"}:
        try:
            source_text = extract_document_text(content, filename)
        except OCRRequiredError:
            # El PDF escaneado se analizó como media nativa. No inventar texto OCR.
            pass
    routed = procesar_con_orquestador(extracted.model_dump(), source_text=source_text)
    return TriageResponse.model_validate(routed, strict=True)
