"""Routing decision assembled from the team's urgency and confidence rules."""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_AI_ROOT = PROJECT_ROOT / "data_ai"
for path in (str(PROJECT_ROOT), str(DATA_AI_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from data_ai.score_confianza import UMBRAL_CONFIANZA_MVP, evaluar_confianza_con_dosis
from data_ai.urgency_json_adapter import evaluate_analysis


def _normalized_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return " ".join(normalized.replace("_", " ").split())


def _known_document_type(value: Any) -> bool:
    return _normalized_text(value) not in {
        "", "desconocido", "no identificado", "noidentificado", "pendiente de procesamiento",
    }


def _confidence_is_ambiguous(documento: dict[str, Any]) -> bool:
    clasificacion = documento.get("clasificacion") or {}
    datos = documento.get("datos_extraidos") or {}
    tipo_conocido = _known_document_type(clasificacion.get("tipo_documento"))
    score = clasificacion.get("score_confianza_clasificacion", 0.0)
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return True

    patient = datos.get("paciente") or {}
    doctor = datos.get("medico_solicitante") or {}
    # Agregado por Edil: conservar los cuatro criterios generales del MVP de
    # Brando. No sustituyen una tabla de campos críticos por tipo documental ni
    # una calibración clínica; los textos vacíos no cuentan como datos presentes.
    criteria = [
        tipo_conocido,
        bool(_normalized_text(patient.get("nombre"))),
        bool(_normalized_text(doctor.get("nombre"))),
        bool(_normalized_text(datos.get("diagnostico_principal"))
             or _normalized_text(datos.get("estudio_realizado"))),
    ]
    doses = [
        item.get("dosis")
        for item in (datos.get("medicamentos_recetados") or [])
        if isinstance(item, dict)
    ]
    result = evaluar_confianza_con_dosis(
        score_clasificacion=float(score),
        criterios_cumplidos=criteria,
        dosis_medicamentos=doses,
        # Agregado por Edil: una sola fuente para el umbral acordado por Laura.
        umbral=UMBRAL_CONFIANZA_MVP,
    )
    # Agregado por Edil: tres criterios de cuatro dan 0.75 y podrían aprobar un
    # tipo desconocido. Esa identificación incompleta necesita revisión humana.
    return not tipo_conocido or bool(result["es_ambiguo"])


def _urgency_requires_review(
    documento: dict[str, Any], *, source_text: str | None = None,
) -> tuple[bool, bool]:
    # Agregado por Edil: antes se omitía el detector si faltaba texto y se perdían
    # las señales de diagnóstico/CIE-10. Ahora se evalúan también esos campos.
    # source_text debe venir del archivo real, nunca de serializar el JSON LLM.
    # Sin texto la cobertura es limitada: no equivale a OCR ni a ausencia de riesgo.
    assessment = evaluate_analysis(documento, source_text=source_text)
    return (
        # La cobertura limitada por sí sola no fuerza auditoría. Sí la fuerzan
        # las coincidencias clínicas del detector y las otras reglas del MVP.
        bool(assessment.get("requires_human_review")),
        assessment.get("suggested_priority") == "Urgente",
    )


def nodo_orquestador(state: dict[str, Any]) -> dict[str, Any]:
    documento = state["documento"]
    clasificacion = documento.get("clasificacion") or {}
    prioridad = clasificacion.get("nivel_prioridad", "Rutina")
    tipo_documento = _normalized_text(clasificacion.get("tipo_documento"))
    ambiguous = _confidence_is_ambiguous(documento)
    review_required, urgent_by_rules = _urgency_requires_review(
        documento, source_text=state.get("source_text"),
    )
    original_decision = documento.get("decision_enrutamiento") or {}
    # Agregado por Edil: sumar reglas nunca debe quitar una revisión ya solicitada
    # por la extracción. También se conserva un estado o destino previo de revisión.
    original_review = (
        original_decision.get("requiere_auditoria_humana", False)
        or documento.get("status") == "auditoria_humana"
        or original_decision.get("destino_principal") == "Cola_Revision_Humana"
    )
    # Agregado por Edil: urgencia y auditoría son dimensiones independientes.
    # El detector puede elevar prioridad, pero nunca rebaja una Urgente previa.
    prioridad_final = "Urgente" if urgent_by_rules or prioridad == "Urgente" else "Rutina"

    if original_review or ambiguous or review_required:
        reasons = []
        if original_review:
            reasons.append(original_decision.get("justificacion_enrutamiento", "").strip()
                           or "revisión humana solicitada por la extracción")
        if ambiguous:
            reasons.append("confianza o datos insuficientes")
        if review_required:
            reasons.append("reglas clínicas")
        return {
            "status": "auditoria_humana",
            "clasificacion": {"nivel_prioridad": prioridad_final},
            "decision_enrutamiento": {
                "destino_principal": "Cola_Revision_Humana",
                "requiere_auditoria_humana": True,
                "justificacion_enrutamiento": (
                    "Derivado a auditoría humana por: " + " y ".join(reasons) + "."
                ),
            }
        }

    if urgent_by_rules or prioridad == "Urgente":
        destination = "Cola_Emergencia_Medica"
    elif tipo_documento == "receta medica":
        destination = "Cola_Farmacia"
    else:
        destination = "Cola_Historia_Clinica"

    return {
        "status": "procesado",
        "clasificacion": {"nivel_prioridad": prioridad_final},
        "decision_enrutamiento": {
            "destino_principal": destination,
            "requiere_auditoria_humana": False,
            "justificacion_enrutamiento": (
                original_decision.get("justificacion_enrutamiento")
                or "Procesamiento técnico completado según las reglas del MVP."
            ),
        }
    }


class _Pipeline:
    # Agregado por Edil: se conserva el adaptador Python de Brando con invoke.
    # No se afirma ejecutar LangGraph sin declarar e instalar esa dependencia.
    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        return nodo_orquestador(state)


pipeline_v1_2 = _Pipeline()
