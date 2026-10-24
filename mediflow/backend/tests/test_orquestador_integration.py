"""Agregado por Edil: reglas reales con documentos sintéticos, sin SDK ni nube."""

from copy import deepcopy

import pytest

from app.core import orquestador
from app.models.schemas import TriageResponse
from app.services.llm_errors import LLMResponseError
from app.services.servicio_orquestador import procesar_con_orquestador


def document(*, review=False, priority="Rutina", score=0.95):
    return {
        "status": "auditoria_humana" if review else "procesado",
        "documento_id": "DOC-SYNTHETIC-ORCHESTRATOR",
        "clasificacion": {
            "tipo_documento": "Receta Médica", "especialidad": "General",
            "nivel_prioridad": priority, "score_confianza_clasificacion": score,
        },
        "datos_extraidos": {
            "paciente": {"nombre": "Persona Ficticia", "edad": 30},
            "medico_solicitante": {"nombre": "Profesional Ficticio", "matricula": "TEST-000"},
            # Agregado por Edil: emisor explícito en este fixture sintético;
            # el código productivo nunca lo deduce del solicitante.
            "profesional_emisor": {"nombre": "Emisor Ficticio", "matricula": "TEST-EMISOR"},
            "estudio_realizado": "Evaluación sintética de prueba",
            "diagnostico_principal": None, "cie10_sugerido": None,
            "medicamentos_recetados": [{"medicamento": "Ejemplo ficticio", "dosis": "dosis ficticia"}],
        },
        "decision_enrutamiento": {
            "destino_principal": "Cola_Revision_Humana" if review else "Cola_Farmacia",
            "requiere_auditoria_humana": review,
            "justificacion_enrutamiento": "Motivo sintético previo.",
        },
        "notificacion_generada": None,
        "almacenamiento_oci": {
            "bucket": "recibidos", "ruta_objeto": "sintetico.txt", "status_backup": "exito",
        },
    }


def test_normal_uses_real_rules_without_modifying_input_or_adding_contract_fields():
    original = document()
    snapshot = deepcopy(original)
    result = procesar_con_orquestador(original, source_text="Documento sintético de control habitual.")
    assert original == snapshot
    assert result["status"] == "procesado"
    assert result["decision_enrutamiento"]["destino_principal"] == "Cola_Farmacia"
    assert set(result) == set(TriageResponse.model_fields)
    assert set(result["decision_enrutamiento"]) == {
        "destino_principal", "requiere_auditoria_humana", "justificacion_enrutamiento",
    }
    assert "source_text" not in result
    assert "texto_extraido" not in result


def test_prior_llm_review_and_reason_cannot_be_removed():
    result = procesar_con_orquestador(document(review=True), source_text="Control habitual sintético.")
    assert result["status"] == "auditoria_humana"
    assert result["decision_enrutamiento"]["requiere_auditoria_humana"] is True
    assert "Motivo sintético previo." in result["decision_enrutamiento"]["justificacion_enrutamiento"]


def test_prior_urgency_is_not_downgraded_when_no_rule_matches():
    result = procesar_con_orquestador(document(priority="Urgente"), source_text="Control habitual sintético.")
    assert result["clasificacion"]["nivel_prioridad"] == "Urgente"
    assert result["decision_enrutamiento"]["destino_principal"] == "Cola_Emergencia_Medica"


def test_new_urgency_and_low_confidence_keep_auditing_and_urgent_priority():
    result = procesar_con_orquestador(
        document(score=0.3), source_text="Caso sintético: dolor toracico opresivo actual.",
    )
    assert result["status"] == "auditoria_humana"
    assert result["clasificacion"]["nivel_prioridad"] == "Urgente"
    assert result["decision_enrutamiento"]["destino_principal"] == "Cola_Revision_Humana"
    assert result["decision_enrutamiento"]["requiere_auditoria_humana"] is True


def test_cie10_without_source_still_triggers_review_but_not_emergency_inference():
    original = document()
    original["datos_extraidos"]["cie10_sugerido"] = "I21"
    result = procesar_con_orquestador(original)
    assert result["status"] == "auditoria_humana"
    assert result["clasificacion"]["nivel_prioridad"] == "Rutina"


def test_diagnosis_is_evaluated_even_without_full_source_text():
    original = document()
    original["datos_extraidos"]["diagnostico_principal"] = "infarto agudo de miocardio"
    result = procesar_con_orquestador(original)
    assert result["status"] == "auditoria_humana"
    assert result["clasificacion"]["nivel_prioridad"] == "Urgente"


def test_missing_source_alone_is_not_an_automatic_review_signal():
    result = procesar_con_orquestador(document())
    assert result["status"] == "procesado"


def test_source_is_forwarded_separately_and_json_is_never_serialized(monkeypatch):
    original_evaluate = orquestador.evaluate_analysis
    observations = []

    def observe(payload, *, source_text=None):
        observations.append(source_text)
        assert "texto_extraido" not in payload
        return original_evaluate(payload, source_text=source_text)

    monkeypatch.setattr(orquestador, "evaluate_analysis", observe)
    procesar_con_orquestador(document(), source_text="Fuente sintética original.")
    procesar_con_orquestador(document())
    assert observations == ["Fuente sintética original.", None]


def test_illegible_dose_uses_real_laura_score_to_request_review():
    original = document()
    original["datos_extraidos"]["medicamentos_recetados"][0]["dosis"] = "ILLEGIBLE"
    result = procesar_con_orquestador(original, source_text="Receta de prueba.")
    assert result["status"] == "auditoria_humana"


@pytest.mark.parametrize("kind", ["", "   ", "DESCONOCIDO", " No identificado ", "no_identificado", "Pendiente de procesamiento"])
def test_unidentified_document_needs_review_even_with_three_other_complete_criteria(kind):
    original = document()
    original["clasificacion"]["tipo_documento"] = kind
    assert procesar_con_orquestador(original)["status"] == "auditoria_humana"


@pytest.mark.parametrize("score, expected", [(0.69, "auditoria_humana"), (0.70, "procesado"), (0.71, "procesado")])
def test_uses_shared_laura_threshold(score, expected):
    assert procesar_con_orquestador(document(score=score))["status"] == expected


@pytest.mark.parametrize("bad_value", [True, "0.95", -1.0, 1.1])
def test_input_contract_is_strict_and_error_does_not_include_data(bad_value):
    original = document()
    original["datos_extraidos"]["paciente"]["nombre"] = "DATO_SINTETICO_NO_DIVULGAR"
    original["clasificacion"]["score_confianza_clasificacion"] = bad_value
    with pytest.raises(LLMResponseError) as error:
        procesar_con_orquestador(original)
    assert "DATO_SINTETICO_NO_DIVULGAR" not in str(error.value)


def test_unanalyzed_receipt_is_not_promoted_to_processed():
    original = document()
    original["status"] = "recibido"
    with pytest.raises(LLMResponseError):
        procesar_con_orquestador(original)


def test_final_contract_is_validated_if_pipeline_returns_invalid_priority(monkeypatch):
    monkeypatch.setattr(orquestador.pipeline_v1_2, "invoke", lambda state: {
        "status": "procesado", "clasificacion": {"nivel_prioridad": "Inventada"},
        "decision_enrutamiento": state["documento"]["decision_enrutamiento"],
    })
    with pytest.raises(LLMResponseError):
        procesar_con_orquestador(document())


def test_catalog_failure_is_controlled_and_does_not_echo_original_error(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("DATO_SINTETICO_NO_DIVULGAR")

    monkeypatch.setattr(orquestador, "evaluate_analysis", fail)
    with pytest.raises(LLMResponseError) as error:
        procesar_con_orquestador(document())
    assert "DATO_SINTETICO_NO_DIVULGAR" not in str(error.value)
