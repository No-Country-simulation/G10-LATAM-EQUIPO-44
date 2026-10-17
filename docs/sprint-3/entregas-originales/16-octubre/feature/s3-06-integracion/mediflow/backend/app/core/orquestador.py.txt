"""Routing decision assembled from the team's urgency and confidence rules."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_AI_ROOT = PROJECT_ROOT / "data_ai"
for path in (str(PROJECT_ROOT), str(DATA_AI_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from data_ai.score_confianza import evaluar_confianza_con_dosis
from data_ai.urgency_json_adapter import evaluate_analysis


def _confidence_is_ambiguous(documento: dict[str, Any]) -> bool:
    clasificacion = documento.get("clasificacion") or {}
    datos = documento.get("datos_extraidos") or {}
    tipo = str(clasificacion.get("tipo_documento") or "").strip()
    score = clasificacion.get("score_confianza_clasificacion", 0.0)
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return True

    patient = datos.get("paciente") or {}
    doctor = datos.get("medico_solicitante") or {}
    criteria = [
        tipo not in {"", "No identificado", "Pendiente de procesamiento"},
        bool(patient.get("nombre")),
        bool(doctor.get("nombre")),
        bool(datos.get("diagnostico_principal") or datos.get("estudio_realizado")),
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
        umbral=0.70,
    )
    return bool(result["es_ambiguo"])


def _urgency_requires_review(documento: dict[str, Any]) -> tuple[bool, bool]:
    source_text = documento.get("texto_extraido")
    if not isinstance(source_text, str) or not source_text.strip():
        return False, False
    assessment = evaluate_analysis(documento, source_text=source_text)
    return (
        bool(assessment.get("review_recommended")),
        assessment.get("suggested_priority") == "Urgente",
    )


def nodo_orquestador(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documento = state["documento"]
    clasificacion = documento.get("clasificacion") or {}
    prioridad = clasificacion.get("nivel_prioridad", "Rutina")
    tipo_documento = str(clasificacion.get("tipo_documento") or "").strip()
    ambiguous = _confidence_is_ambiguous(documento)
    review_required, urgent_by_rules = _urgency_requires_review(documento)

    if ambiguous or review_required:
        reasons = []
        if ambiguous:
            reasons.append("confianza o datos insuficientes")
        if review_required:
            reasons.append("reglas clínicas")
        return {
            "decision_enrutamiento": {
                "status": "auditoria_humana",
                "prioridad": "Urgente" if urgent_by_rules else prioridad,
                "destino_principal": "Cola_Revision_Humana",
                "requiere_auditoria_humana": True,
                "justificacion_enrutamiento": (
                    "Derivado a auditoría humana por: " + " y ".join(reasons) + "."
                ),
            }
        }

    if urgent_by_rules or prioridad == "Urgente":
        destination = "Cola_Emergencia_Medica"
    elif tipo_documento == "Receta Médica":
        destination = "Cola_Farmacia"
    else:
        destination = "Cola_Historia_Clinica"

    return {
        "decision_enrutamiento": {
            "status": "procesado",
            "prioridad": "Urgente" if urgent_by_rules else prioridad,
            "destino_principal": destination,
            "requiere_auditoria_humana": False,
            "justificacion_enrutamiento": "Procesamiento automático exitoso.",
        }
    }


class _Pipeline:
    def invoke(self, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return nodo_orquestador(state)


pipeline_v1_2 = _Pipeline()
