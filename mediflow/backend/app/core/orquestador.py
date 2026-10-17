"""Decide the final routing state for a document JSON."""

from __future__ import annotations

from typing import Any


def nodo_orquestador(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    documento = state["documento"]
    clasificacion = documento.get("clasificacion") or {}
    datos = documento.get("datos_extraidos") or {}
    prioridad = clasificacion.get("nivel_prioridad", "Rutina")
    tipo_documento = clasificacion.get("tipo_documento", "")

    audit_required = bool(
        documento.get("decision_enrutamiento", {}).get("requiere_auditoria_humana")
        or clasificacion.get("requiere_auditoria_humana")
        or tipo_documento == "Pendiente de procesamiento"
    )
    if audit_required:
        return {
            "decision_enrutamiento": {
                "status": "auditoria_humana",
                "prioridad": prioridad,
                "destino_principal": "Cola_Revision_Humana",
                "requiere_auditoria_humana": True,
                "justificacion_enrutamiento": "Documento pendiente de revisión humana.",
            }
        }

    if prioridad == "Urgente":
        destino = "Cola_Emergencia_Medica"
    elif tipo_documento == "Receta Médica":
        destino = "Cola_Farmacia"
    else:
        destino = "Cola_Historia_Clinica"

    return {
        "decision_enrutamiento": {
            "status": "procesado",
            "prioridad": prioridad,
            "destino_principal": destino,
            "requiere_auditoria_humana": False,
            "justificacion_enrutamiento": "Procesamiento automático exitoso.",
        }
    }


class _Pipeline:
    def invoke(self, state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return nodo_orquestador(state)


pipeline_v1_2 = _Pipeline()
