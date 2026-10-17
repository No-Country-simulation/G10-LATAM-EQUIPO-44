"""Agregado por Edil: integración de módulos reales con OCI/Gemini simulados."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import TriageResponse


class MemoryStorage:
    def __init__(self, events, *, fail_copy=False):
        self.settings = SimpleNamespace(bucket_recibidos="recibidos")
        self.events, self.fail_copy = events, fail_copy
        self.files, self.results = {}, {}

    def subir_a_recibidos(self, data, name):
        self.events.append("original")
        self.files["recibidos", name] = data
        return name

    def determinar_bucket_por_estado(self, status):
        return {"recibido": "recibidos", "procesado": "procesados", "auditoria_humana": "auditoria_humana"}[status]

    def guardar_resultado_triage(self, payload):
        result = TriageResponse.model_validate(payload, strict=True)
        self.events.append(result.status)
        self.results[self.determinar_bucket_por_estado(result.status), result.documento_id] = copy.deepcopy(payload)

    def copiar_archivo(self, name, source, target):
        self.events.append("copia")
        if self.fail_copy:
            raise RuntimeError("detalle-privado-del-sdk")
        self.files[target, name] = self.files[source, name]

    def recuperar_resultado_triage(self, document_id):
        for bucket in ("procesados", "auditoria_humana", "recibidos"):
            if (bucket, document_id) in self.results:
                return copy.deepcopy(self.results[bucket, document_id])


def clinical(*, review=False, priority="Rutina", score=0.9):
    return {
        "clasificacion": {"tipo_documento": "Receta médica", "especialidad": None,
                          "nivel_prioridad": priority, "score_confianza_clasificacion": score},
        "datos_extraidos": {"paciente": {"nombre": "Persona Ficticia", "edad": None},
                            "medico_solicitante": {"nombre": "Profesional Ficticio", "matricula": None},
                            "estudio_realizado": None, "diagnostico_principal": None, "cie10_sugerido": None,
                            "medicamentos_recetados": [{"medicamento": "Dato de prueba", "dosis": None}]},
        "decision_enrutamiento": {"destino_principal": "Cola_Revision_Humana" if review else "Cola_Farmacia",
                                  "requiere_auditoria_humana": review, "justificacion_enrutamiento": "Caso sintético."},
    }


@pytest.mark.parametrize("review,priority,score,expected", [
    (False, "Rutina", 0.9, "procesado"),
    (True, "Urgente", 0.9, "auditoria_humana"),
    (False, "Urgente", 0.69, "auditoria_humana"),
])
def test_post_routes_scores_copies_persists_and_gets_same_result(monkeypatch, review, priority, score, expected):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "model-under-test")
    events = []
    storage = MemoryStorage(events)
    with patch("app.api.routes.OCIStorageManager", return_value=storage), patch("app.services.gemini_client.genai.Client") as provider:
        def generate(**kwargs):
            events.append("gemini")
            return SimpleNamespace(text=json.dumps(clinical(review=review, priority=priority, score=score)), candidates=None)
        provider.return_value.models.generate_content.side_effect = generate
        with TestClient(app) as client:
            response = client.post("/api/triage", data={"analyze": "true"}, files={"file": ("demo.txt", b"Control ficticio para prueba del software.")})
            assert response.status_code == 201, response.text
            result = response.json()
            recovered = client.get("/api/documents/" + result["documento_id"])
    target = "procesados" if expected == "procesado" else "auditoria_humana"
    assert result["status"] == expected
    assert result["clasificacion"]["nivel_prioridad"] == priority
    assert result["almacenamiento_oci"]["bucket"] == target
    assert set(result["decision_enrutamiento"]) == {"destino_principal", "requiere_auditoria_humana", "justificacion_enrutamiento"}
    assert recovered.status_code == 200 and recovered.json() == result
    name = result["almacenamiento_oci"]["ruta_objeto"]
    assert storage.files["recibidos", name] == storage.files[target, name]
    assert events == ["original", "recibido", "gemini", "copia", expected]
    provider.return_value.models.generate_content.assert_called_once()


def test_no_consent_never_calls_ai_or_copy():
    events = []
    storage = MemoryStorage(events)
    with patch("app.api.routes.OCIStorageManager", return_value=storage), patch("app.api.routes.analyze_received_document") as ai:
        with TestClient(app) as client:
            result = client.post("/api/triage", files={"file": ("demo.txt", b"Documento ficticio.")})
    assert result.status_code == 201 and result.json()["status"] == "recibido"
    assert events == ["original", "recibido"]
    ai.assert_not_called()


def test_copy_failure_preserves_received_record_and_safe_id(monkeypatch, caplog):
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "model-under-test")
    events = []
    storage = MemoryStorage(events, fail_copy=True)
    with patch("app.api.routes.OCIStorageManager", return_value=storage), patch("app.services.gemini_client.genai.Client") as provider:
        provider.return_value.models.generate_content.return_value = SimpleNamespace(text=json.dumps(clinical()), candidates=None)
        with TestClient(app) as client:
            response = client.post("/api/triage", data={"analyze": "true"}, files={"file": ("demo.txt", b"Documento ficticio.")})
            assert response.status_code == 503
            document_id = response.headers["X-Document-ID"]
            recovered = client.get("/api/documents/" + document_id)
    assert recovered.status_code == 200 and recovered.json()["status"] == "recibido"
    assert len(storage.files) == 1
    assert "detalle-privado" not in response.text + caplog.text
    assert events == ["original", "recibido", "copia"]
