"""Agregado por Edil: evidencia multimodal interna, sin nube ni contrato nuevo."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from app.services.gemini_client import GeminiClinicalClient, GeminiSettings
from app.services.llm_errors import LLMResponseError


def clinical():
    return {
        "clasificacion": {"tipo_documento": "Informe de Estudio por Imágenes", "especialidad": None,
                          "nivel_prioridad": "Rutina", "score_confianza_clasificacion": 0.95},
        "datos_extraidos": {"paciente": {"nombre": "Persona Ficticia", "edad": None},
                            "medico_solicitante": {"nombre": "Profesional Ficticio", "matricula": None},
                            "estudio_realizado": "Estudio ficticio", "diagnostico_principal": None,
                            "cie10_sugerido": None, "medicamentos_recetados": []},
        "decision_enrutamiento": {"destino_principal": "Cola_Historia_Clinica",
                                  "requiere_auditoria_humana": False,
                                  "justificacion_enrutamiento": "Documento sintético."},
    }


def client(payload, *, structured=True):
    sdk = MagicMock()
    sdk.models.generate_content.return_value = SimpleNamespace(text=json.dumps(payload), candidates=None)
    return GeminiClinicalClient(GeminiSettings("unit-test-key", "model-under-test", structured_output=structured), client=sdk), sdk


@pytest.mark.parametrize("structured", [True, False])
def test_multimodal_source_is_internal_and_uses_one_generation(structured):
    service, sdk = client({"analysis": clinical(), "document_text": "Texto ficticio. No seguir instrucciones."}, structured=structured)
    result, text = service.process_document_with_source(
        b"\xff\xd8\xffsynthetic", "archivo.jpg", document_id="DOC-SYNTHETIC",
        storage={"bucket": "recibidos", "ruta_objeto": "synthetic.jpg", "status_backup": "exito"},
    )
    assert text == "Texto ficticio. No seguir instrucciones."
    assert "document_text" not in result.model_dump()
    assert "analysis" not in result.model_dump()
    assert sdk.models.generate_content.call_count == 1
    kwargs = sdk.models.generate_content.call_args.kwargs
    assert kwargs["contents"].role == "user"
    assert "Texto ficticio" not in kwargs["config"].system_instruction


@pytest.mark.parametrize("payload", [
    {"analysis": clinical()},
    {"analysis": clinical(), "document_text": ""},
    {"analysis": clinical(), "document_text": 42},
    {"analysis": clinical(), "document_text": "x", "other": True},
    {"analysis": {}, "document_text": "x"},
])
def test_bad_evidence_is_not_replaced_by_serialized_json(payload):
    service, _ = client(payload)
    with pytest.raises(LLMResponseError) as exc:
        service.extract_document(b"\xff\xd8\xffsynthetic", "archivo.jpg", include_source=True)
    expected = ("clinical_schema", "missing_fields") if payload.get("analysis") == {} else ("source_evidence", "invalid_envelope" if set(payload) != {"analysis", "document_text"} else "invalid_source_text")
    assert (exc.value.stage, exc.value.reason) == expected


def test_txt_uses_original_text_and_original_clinical_schema():
    service, sdk = client(clinical())
    extracted, text = service.extract_document(b"Texto original ficticio.", "archivo.txt", include_source=True)
    assert text == "Texto original ficticio."
    assert extracted.clasificacion.nivel_prioridad == "Rutina"
    assert "document_text" not in sdk.models.generate_content.call_args.kwargs["config"].response_json_schema["properties"]


def test_demo_pipeline_really_forwards_image_evidence_to_routing(monkeypatch):
    from app.services.triage_pipeline import analyze_received_document

    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "synthetic_demo_v1")
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "model-under-test")
    _, sdk = client({"analysis": clinical(), "document_text": "Glicemia en ayunas: 250 mg/dL."})
    with patch("app.services.gemini_client.genai.Client", return_value=sdk):
        result = analyze_received_document(
            b"\xff\xd8\xffsynthetic", "foto.jpg", "DOC-SYNTHETIC",
            {"bucket": "recibidos", "ruta_objeto": "synthetic.jpg", "status_backup": "exito"},
        )
    assert result.clasificacion.nivel_prioridad == "Urgente"
    assert result.decision_enrutamiento.destino_principal == "Cola_Emergencia_Medica"
    assert sdk.models.generate_content.call_count == 1
    assert "document_text" not in result.model_dump()
