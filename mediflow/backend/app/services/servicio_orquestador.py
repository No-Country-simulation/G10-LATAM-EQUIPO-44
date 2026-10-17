"""Adapter between the triage JSON and Eliana's routing decision."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.orquestador import pipeline_v1_2


def procesar_con_orquestador(documento: dict[str, Any]) -> dict[str, Any]:
    """Merge the routing decision into the existing triage document."""
    resultado = deepcopy(documento)
    decision = resultado.get("decision_enrutamiento") or {}
    decision_final = pipeline_v1_2.invoke({"documento": resultado})[
        "decision_enrutamiento"
    ]
    decision_final.setdefault(
        "justificacion_enrutamiento",
        decision.get("justificacion_enrutamiento", ""),
    )
    decision.update(decision_final)
    resultado["decision_enrutamiento"] = decision
    resultado["status"] = decision_final["status"]
    return resultado
