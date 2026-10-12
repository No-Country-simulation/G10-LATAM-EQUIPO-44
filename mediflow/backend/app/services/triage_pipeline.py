# Agregado por Edil: conecta la recepción de Drazen con Gemini y validación,
# reutilizando el cliente OCI de Eliana. No mueve ni elimina documentos.
"""Integración de Sprint 2: archivo en memoria -> IA -> contrato validado."""

from .gemini_client import GeminiClinicalClient


def analyze_received_document(content: bytes, filename: str, document_id: str, storage: dict):
    """El archivo ya se guardó en recibidos; storage describe esa operación real."""
    with GeminiClinicalClient() as client:
        return client.process_document(
            content, filename, document_id=document_id, storage=storage
        )
