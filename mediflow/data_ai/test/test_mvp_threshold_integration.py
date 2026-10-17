"""Agregado por Edil: umbral MVP al consumir el contrato existente, sin servicios."""

from copy import deepcopy

import pytest

from app.models.schemas import TriageResponse
from mediflow.data_ai.score_confianza import (
    evaluar_confianza,
    evaluar_confianza_con_dosis,
)


@pytest.mark.parametrize("score,ambiguous", [(0.699, True), (0.70, False)])
def test_public_evaluation_helpers_share_mvp_default(score, ambiguous):
    # Agregado por Edil: los consumidores omiten el umbral; ambos caminos deben
    # aplicar 0.70 sin convertir una frontera exacta en ambiguedad.
    plain = evaluar_confianza(score, [True, True], False)
    with_doses = evaluar_confianza_con_dosis(score, [True, True], ["dosis de prueba"])
    assert plain["es_ambiguo"] is ambiguous
    assert with_doses == plain


def test_illegible_dose_requires_review_even_with_zero_threshold():
    # Agregado por Edil: una dosis ilegible conserva la revision obligatoria
    # al pasar por el adaptador de dosis, incluso al configurar umbral cero.
    result = evaluar_confianza_con_dosis(0.95, [True], ["ILLEGIBLE"], umbral=0.0)
    assert result["score_operativo"] == 0.0
    assert result["es_ambiguo"] is True


@pytest.mark.parametrize("field", ["score_clasificacion", "umbral"])
@pytest.mark.parametrize("invalid,error", [(True, TypeError), (float("nan"), ValueError), (float("inf"), ValueError)])
def test_critical_dose_does_not_bypass_numeric_validation(field, invalid, error):
    # Agregado por Edil: una alerta no debe ocultar una entrada invalida ni
    # permitir booleanos o valores no finitos procedentes de otro modulo.
    arguments = {
        "score_clasificacion": 0.95,
        "criterios_cumplidos": [True],
        "dosis_medicamentos": ["ILLEGIBLE"],
        "umbral": 0.70,
    }
    arguments[field] = invalid
    with pytest.raises(error):
        evaluar_confianza_con_dosis(**arguments)


def test_confidence_reads_existing_fields_without_expanding_document_contract():
    # Agregado por Edil: el calculo operativo permanece separado del JSON
    # publicado hasta acordar su persistencia; no inventamos campos de API.
    document = TriageResponse.model_validate({
        "status": "auditoria_humana",
        "documento_id": "DOC-SYNTHETIC-CONFIDENCE",
        "clasificacion": {
            "tipo_documento": "Receta Médica",
            "especialidad": "General",
            "nivel_prioridad": "Urgente",
            "score_confianza_clasificacion": 0.95,
        },
        "datos_extraidos": {
            "paciente": {"nombre": None, "edad": None},
            "medico_solicitante": {"nombre": None, "matricula": None},
            "estudio_realizado": None,
            "diagnostico_principal": None,
            "cie10_sugerido": None,
            "medicamentos_recetados": [{"medicamento": "Prueba sintetica", "dosis": "ILLEGIBLE"}],
        },
        "decision_enrutamiento": {
            "destino_principal": "Cola_Revision_Humana",
            "requiere_auditoria_humana": True,
            "justificacion_enrutamiento": "Caso sintetico de prueba.",
        },
        "almacenamiento_oci": {
            "bucket": "auditoria_humana",
            "ruta_objeto": "DOC-SYNTHETIC-CONFIDENCE.json",
            "status_backup": "exito",
        },
    }).model_dump(mode="json")
    before = deepcopy(document)
    result = evaluar_confianza_con_dosis(
        score_clasificacion=document["clasificacion"]["score_confianza_clasificacion"],
        criterios_cumplidos=[True],  # Criterio sintetico, no una politica por tipo.
        dosis_medicamentos=[item["dosis"] for item in document["datos_extraidos"]["medicamentos_recetados"]],
    )
    assert result["es_ambiguo"] is True
    assert document == before
    assert document["clasificacion"]["nivel_prioridad"] == "Urgente"
    assert "score_operativo" not in document
    assert "es_ambiguo" not in document
