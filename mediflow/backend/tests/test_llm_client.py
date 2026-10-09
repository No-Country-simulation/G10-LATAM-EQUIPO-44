import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.llm_client import CohereClient
from app.core.config import settings
from app.main import app


class FakeCohereResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def extraction_payload():
    return {
        "clasificacion": {
            "tipo_documento": "Informe de laboratorio",
            "especialidad": "Laboratorio",
            "nivel_prioridad": "Urgente",
            "score_confianza_clasificacion": 0.91,
        },
        "datos_extraidos": {
            "paciente": {"nombre": "Ana Perez", "edad": 43},
            "medico_solicitante": {"nombre": "Dr. Ruiz", "matricula": "M-1"},
            "estudio_realizado": "Hemograma",
            "diagnostico_principal": "Anemia",
            "cie10_sugerido": "D64.9",
        },
    }


def test_cohere_client_parses_json_response():
    client = CohereClient(api_key="test-key", model="test-model")
    response_body = {
        "message": {"content": [{"type": "text", "text": json.dumps(extraction_payload())}]}
    }
    with patch("app.core.llm_client.requests.post", return_value=FakeCohereResponse(response_body)) as request:
        result = client.extract_text(b"Paciente: Ana Perez", "informe.txt")

    assert result == extraction_payload()
    assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert request.call_args.kwargs["json"]["response_format"] == {"type": "json_object"}


def test_triage_uses_cohere_result_and_validates_contract(monkeypatch):
    storage_factory = MagicMock()
    storage = storage_factory.return_value
    storage.settings.bucket_name = "recibidos"
    storage.subir_a_recibidos.return_value = "pruebas/DOC-1.txt"
    client = MagicMock()
    client.extract_document.return_value = extraction_payload()

    monkeypatch.setattr(settings, "LLM_PROVIDER", "cohere")
    monkeypatch.setattr(settings, "COHERE_API_KEY", "test-key")
    with patch("app.api.routes.OCIStorageManager", storage_factory), patch(
        "app.api.routes.CohereClient.from_settings", return_value=client
    ):
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/triage", files={"file": ("informe.txt", b"Paciente: Ana Perez")}
            )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "procesado"
    assert body["datos_extraidos"]["paciente"]["nombre"] == "Ana Perez"
    assert body["almacenamiento_oci"]["bucket"] == "recibidos"
    client.extract_document.assert_called_once()
