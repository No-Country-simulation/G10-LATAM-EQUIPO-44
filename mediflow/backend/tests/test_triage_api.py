"""Prueba la API multipart con almacenamiento simulado; nunca contacta OCI."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import TriageResponse


@pytest.fixture
def storage():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.settings.bucket_recibidos = "recibidos"
        manager.subir_a_recibidos.side_effect = lambda body, name: name
        factory.return_value = manager
        yield factory, manager


@pytest.mark.parametrize("filename", ["test.pdf", "test.jpg", "test.jpeg", "test.png", "test.txt"])
def test_upload_reaches_storage_and_returns_contract(storage, filename):
    factory, manager = storage
    with TestClient(app) as client:
        response = client.post("/api/triage", files={"file": (filename, b"documento de prueba")})
    assert response.status_code == 201
    result = TriageResponse.model_validate(response.json())
    assert result.status == "recibido"
    assert result.almacenamiento_oci.bucket == "recibidos"
    assert "/" not in result.almacenamiento_oci.ruta_objeto
    assert result.documento_id in result.almacenamiento_oci.ruta_objeto
    assert manager.subir_a_recibidos.call_args.args[0] == b"documento de prueba"
    factory.assert_called_once()


@pytest.mark.parametrize("filename,body,code", [
    ("bad.exe", b"contenido", 415),
    ("empty.txt", b"", 400),
    ("large.txt", b"x" * (10 * 1024 * 1024 + 1), 413),
], ids=["extension-invalida", "archivo-vacio", "archivo-demasiado-grande"])
def test_invalid_files_do_not_access_storage(storage, filename, body, code):
    with TestClient(app) as client:
        response = client.post("/api/triage", files={"file": (filename, body)})
    assert response.status_code == code
    storage[0].assert_not_called()


def test_storage_failure_is_not_reported_as_success_or_leaked(storage):
    storage[1].subir_a_recibidos.side_effect = RuntimeError("detalle privado de OCI")
    with TestClient(app) as client:
        response = client.post("/api/triage", files={"file": ("test.txt", b"test")})
    assert response.status_code == 500
    assert "detalle privado" not in response.text


def test_registered_routes_and_health(storage):
    with TestClient(app) as client:
        assert client.get("/").json()["status"] == "ok"
        assert "/api/triage" in client.get("/openapi.json").json()["paths"]
        assert client.post("/api/triage").status_code == 422
    storage[0].assert_not_called()


def test_official_contract_example_validates():
    document = Path(__file__).parents[1] / "app/core/contrato.json"
    TriageResponse.model_validate(json.loads(document.read_text(encoding="utf-8")))
