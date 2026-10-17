"""Apply the routing decision without replacing the triage JSON contract."""

from __future__ import annotations

from typing import Any

from app.core.orquestador import pipeline_v1_2
from app.models.schemas import TriageResponse
from app.services.llm_errors import LLMResponseError


def procesar_con_orquestador(
    documento: dict[str, Any], *, source_text: str | None = None,
) -> dict[str, Any]:
    """Apply team rules to an analyzed document using the current JSON contract."""
    try:
        # Agregado por Edil: validar antes y después, sin mutar el objeto recibido.
        # Antes se actualizaba el dict sin comprobar el contrato y se copiaban
        # status/prioridad dentro de decision_enrutamiento, donde no son campos.
        if not isinstance(documento, dict):
            raise TypeError()
        if source_text is not None and not isinstance(source_text, str):
            raise TypeError()
        parsed = TriageResponse.model_validate(documento, strict=True)
        # Una recepción no demuestra que exista análisis; este servicio no crea
        # resultados clínicos ni sustituye una extracción que todavía falta.
        if parsed.status == "recibido":
            raise ValueError()
        resultado = parsed.model_dump()
        actual_source = source_text if source_text and source_text.strip() else None
        evaluation = pipeline_v1_2.invoke({
            "documento": resultado,
            # Contexto interno: no se incorpora al JSON ni se persiste en logs.
            "source_text": actual_source,
        })
        resultado["decision_enrutamiento"].update(evaluation["decision_enrutamiento"])
        resultado["status"] = evaluation["status"]
        resultado["clasificacion"]["nivel_prioridad"] = evaluation["clasificacion"]["nivel_prioridad"]
        return TriageResponse.model_validate(resultado, strict=True).model_dump()
    except Exception:
        # Agregado por Edil: errores de esquema, catálogo o reglas se traducen al
        # error controlado del backend, sin adjuntar documentos ni excepciones.
        raise LLMResponseError("No se pudo validar el resultado de la orquestación.") from None
