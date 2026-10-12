# Agregado por Edil: demuestra el flujo de Brando con transportes simulados;
# no representa una llamada real a Gemini ni prueba clínica de calidad.
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app
from app.models.schemas import TriageResponse
from app.services.gemini_client import GeminiClinicalClient, GeminiSettings
from app.services.llm_errors import (
    LLMConfigurationError, LLMAuthenticationError, LLMQuotaError, LLMTimeoutError,
    LLMNetworkError, LLMResponseError, LLMInputError,
)


def clinical_payload(review=False):
    return {
        "clasificacion": {"tipo_documento": "Receta médica", "especialidad": "General",
                          "nivel_prioridad": "Rutina", "score_confianza_clasificacion": 0.8},
        "datos_extraidos": {
            "paciente": {"nombre": None, "edad": None},
            "medico_solicitante": {"nombre": None, "matricula": None},
            "estudio_realizado": None, "diagnostico_principal": None, "cie10_sugerido": None,
            "medicamentos_recetados": [{"medicamento": "Medicamento ficticio", "dosis": "dosis de prueba"}],
        },
        "decision_enrutamiento": {
            "destino_principal": "Cola_Revision_Humana" if review else "Cola_Farmacia",
            "requiere_auditoria_humana": review,
            "justificacion_enrutamiento": "Caso sintético.",
        },
    }


@pytest.mark.parametrize("review,status", [(False,"procesado"),(True,"auditoria_humana")])
def test_full_http_oci_gemini_validation_flow(monkeypatch, review, status):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "model-under-test")
    events = []
    with patch("app.api.routes.OCIStorageManager") as storage_factory, \
         patch("app.services.gemini_client.genai.Client") as gemini_factory:
        storage = storage_factory.return_value
        storage.settings.bucket_recibidos = "recibidos"
        def upload(body, name):
            events.append("oci")
            assert body == b"Nota sintetica"
            return name
        storage.subir_a_recibidos.side_effect = upload
        def generate(**kwargs):
            events.append("gemini")
            return SimpleNamespace(text=json.dumps(clinical_payload(review)), candidates=None)
        gemini_factory.return_value.models.generate_content.side_effect = generate
        with TestClient(app) as http:
            response = http.post("/api/triage", data={"analyze":"true"},
                                 files={"file":("demo.txt", b"Nota sintetica")})
        assert response.status_code == 201
        result = TriageResponse.model_validate(response.json())
        assert result.status == status
        assert result.datos_extraidos.medicamentos_recetados[0].medicamento == "Medicamento ficticio"
        assert result.almacenamiento_oci.bucket == "recibidos"
        assert events == ["oci", "gemini"]
        gemini_factory.return_value.close.assert_called_once()
        storage.mover_archivo.assert_not_called()


@pytest.mark.parametrize("failure,code", [
    (LLMConfigurationError("private"),503), (LLMAuthenticationError("private"),502),
    (LLMQuotaError("private"),429), (LLMTimeoutError("private"),504),
    (LLMNetworkError("private"),503), (LLMResponseError("private"),502),
    (LLMInputError("private"),422),
])
def test_analysis_failures_keep_received_object_and_hide_details(failure, code):
    with patch("app.api.routes.OCIStorageManager") as factory, \
         patch("app.api.routes.analyze_received_document", side_effect=failure):
        factory.return_value.settings.bucket_recibidos = "recibidos"
        factory.return_value.subir_a_recibidos.side_effect = lambda body,name:name
        with TestClient(app) as http:
            response = http.post("/api/triage", data={"analyze":"true"},
                                 files={"file":("demo.txt",b"Nota sintetica")})
        assert response.status_code == code
        assert "private" not in response.text
        assert response.headers["X-Document-ID"].startswith("DOC-CLIN-")
        factory.return_value.object_storage.delete_object.assert_not_called()


def test_oci_failure_does_not_call_ia():
    with patch("app.api.routes.OCIStorageManager") as factory, \
         patch("app.api.routes.analyze_received_document") as analyze:
        factory.return_value.subir_a_recibidos.side_effect = RuntimeError("private")
        with TestClient(app) as http:
            response = http.post("/api/triage", data={"analyze":"true"},
                                 files={"file":("demo.txt",b"Nota sintetica")})
        assert response.status_code == 500
        analyze.assert_not_called()


@pytest.mark.parametrize("filename,data,mime", [
    ("demo.jpg", b"\xff\xd8\xffsynthetic", "image/jpeg"),
    ("demo.png", b"\x89PNG\r\n\x1a\nsynthetic", "image/png"),
])
def test_native_multimodal_path_is_prepared_without_ocr(filename,data,mime):
    transport=MagicMock()
    transport.models.generate_content.return_value=SimpleNamespace(
        text=json.dumps(clinical_payload()),candidates=None)
    service=GeminiClinicalClient(GeminiSettings("unit-test-key","model-under-test"),client=transport)
    service.extract_document(data,filename)
    parts=transport.models.generate_content.call_args.kwargs["contents"].parts
    assert parts[1].inline_data.mime_type == mime
    assert parts[1].inline_data.data == data


def test_pdf_without_text_uses_native_pdf_input_not_fake_ocr():
    writer=PdfWriter()
    writer.add_blank_page(width=100,height=100)
    output=BytesIO()
    writer.write(output)
    transport=MagicMock()
    transport.models.generate_content.return_value=SimpleNamespace(
        text=json.dumps(clinical_payload(True)),candidates=None)
    service=GeminiClinicalClient(GeminiSettings("unit-test-key","model-under-test"),client=transport)
    result=service.extract_document(output.getvalue(),"scan.pdf")
    assert result.decision_enrutamiento.requiere_auditoria_humana
    parts=transport.models.generate_content.call_args.kwargs["contents"].parts
    assert parts[1].inline_data.mime_type == "application/pdf"
