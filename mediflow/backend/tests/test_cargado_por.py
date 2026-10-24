"""Agregado por Edil: autor de carga verificado, sin llamadas OCI ni Gemini."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api import routes
from app.models.schemas import TriageResponse
from app.core.review_auth import Principal
from app.services.llm_errors import LLMTimeoutError


@pytest.fixture
def storage(monkeypatch):
    documents = {}

    def save(document):
        documents[document["documento_id"]] = deepcopy(document)

    manager = SimpleNamespace(
        settings=SimpleNamespace(bucket_recibidos="recibidos"),
        subir_a_recibidos=lambda content, name: name,
        guardar_resultado_triage=save,
        recuperar_resultado_triage=lambda identifier: deepcopy(documents.get(identifier)),
        determinar_bucket_por_estado=lambda state: state,
        copiar_archivo=lambda *args: None,
    )
    monkeypatch.setattr(routes, "OCIStorageManager", lambda: manager)
    return documents


def client_for(login=None):
    application = FastAPI()
    application.include_router(routes.router)
    if login is not None:
        @application.middleware("http")
        async def synthetic_identity(request, call_next):
            # Solo el fixture establece este principal. Nunca se lee del cliente.
            request.state.mediflow_principal = Principal(login=login)
            return await call_next(request)
    return TestClient(application)


def processed_result(document_id, storage):
    example = Path(__file__).parents[1] / "app/core/contrato.json"
    data = json.loads(example.read_text(encoding="utf-8"))
    data.update(documento_id=document_id, cargado_por="autor-inventado-por-llm")
    data["almacenamiento_oci"] = storage
    return TriageResponse.model_validate(data)


def test_authenticated_uploader_is_persisted_and_recovered(storage):
    with client_for("uploader-synthetic@example.invalid") as client:
        response = client.post("/api/triage", files={"file": ("synthetic.txt", b"synthetic")},
                               data={"cargado_por": "identidad-suplantada"})
        assert response.status_code == 201
        data = response.json()
        identifier = data["documento_id"]
        assert data["cargado_por"] == "uploader-synthetic@example.invalid"
        assert storage[identifier]["cargado_por"] == data["cargado_por"]
        assert client.get(f"/api/documents/{identifier}").json()["cargado_por"] == data["cargado_por"]


def test_anonymous_upload_cannot_claim_an_identity(storage):
    with client_for() as client:
        response = client.post("/api/triage", files={"file": ("synthetic.txt", b"synthetic")},
                               data={"cargado_por": "identidad-suplantada"},
                               headers={"Tailscale-User-Login": "untrusted@example.invalid"})
    assert response.status_code == 201
    assert response.json()["cargado_por"] is None
    assert storage[response.json()["documento_id"]]["cargado_por"] is None


def test_analysis_cannot_replace_the_authenticated_uploader(storage, monkeypatch):
    def analyze(content, filename, identifier, location):
        return processed_result(identifier, location)

    monkeypatch.setattr(routes, "analyze_received_document", analyze)
    with client_for("uploader-synthetic@example.invalid") as client:
        response = client.post("/api/triage", files={"file": ("synthetic.txt", b"synthetic")},
                               data={"analyze": "true"})
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "procesado"
    assert data["clasificacion"]["nivel_prioridad"] == "Urgente"
    assert data["cargado_por"] == "uploader-synthetic@example.invalid"
    assert storage[data["documento_id"]]["cargado_por"] == data["cargado_por"]


def test_analysis_failure_keeps_original_uploader_in_recoverable_receipt(storage, monkeypatch):
    def fail(*args):
        raise LLMTimeoutError("synthetic timeout")

    monkeypatch.setattr(routes, "analyze_received_document", fail)
    with client_for("uploader-synthetic@example.invalid") as client:
        response = client.post("/api/triage", files={"file": ("synthetic.txt", b"synthetic")},
                               data={"analyze": "true"})
        assert response.status_code == 504
        identifier = response.headers["X-Document-ID"]
        receipt = client.get(f"/api/documents/{identifier}").json()
    assert receipt["status"] == "recibido"
    assert receipt["cargado_por"] == "uploader-synthetic@example.invalid"


def test_historical_json_without_uploader_can_still_be_read(storage):
    data = processed_result("DOC-HISTORICAL", {
        "bucket": "procesados", "ruta_objeto": "DOC-HISTORICAL.txt", "status_backup": "exito",
    }).model_dump()
    del data["cargado_por"]
    storage[data["documento_id"]] = deepcopy(data)
    with client_for() as client:
        response = client.get("/api/documents/DOC-HISTORICAL")
    assert response.status_code == 200
    assert response.json()["cargado_por"] is None
    assert "cargado_por" not in storage["DOC-HISTORICAL"]
