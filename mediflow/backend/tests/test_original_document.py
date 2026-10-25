"""Agregado por Edil: original OCI privado, sin servicios externos."""
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.review_auth import Principal


@pytest.fixture
def original():
    doc_id = "DOC-CLIN-ABC123"
    payload = {
        "documento_id": doc_id, "status": "recibido", "cargado_por": "edil",
        "clasificacion": {"tipo_documento": "Pendiente de procesamiento", "nivel_prioridad": "Rutina", "score_confianza_clasificacion": 0},
        "datos_extraidos": {"paciente": {}, "medico_solicitante": {}},
        "decision_enrutamiento": {"destino_principal": "Cola_Procesamiento_Inicial", "requiere_auditoria_humana": False, "justificacion_enrutamiento": "Sintético"},
        "almacenamiento_oci": {"bucket": "recibidos", "ruta_objeto": doc_id + ".jpg", "status_backup": "exito"},
    }
    manager = MagicMock()
    manager.settings.bucket_recibidos = "recibidos"
    manager.settings.bucket_procesados = "procesados"
    manager.settings.bucket_auditoria = "auditoria_humana"
    manager.namespace = "test-only"
    manager.recuperar_resultado_triage.return_value = payload
    manager.object_storage.get_object.return_value.data.raw = io.BytesIO(b"synthetic-original")
    # Cookie ficticia: la middleware consulta el sustituto solo si hay cookie.
    with patch("app.api.routes.OCIStorageManager", return_value=manager), patch(
        "app.auth.middleware.get_principal_from_session", return_value=Principal("edil", False)
    ) as identity:
        yield payload, manager, identity


@pytest.mark.parametrize("extension,mime", [("jpg", "image/jpeg"), ("png", "image/png"), ("pdf", "application/pdf"), ("txt", "text/plain")])
@pytest.mark.parametrize("bucket", ["recibidos", "procesados", "auditoria_humana"])
def test_original_reads_stored_bytes_only(original, extension, mime, bucket):
    payload, manager, _ = original
    payload["almacenamiento_oci"].update(bucket=bucket, ruta_objeto="DOC-CLIN-ABC123." + extension)
    with TestClient(app, cookies={"mediflow_session": "synthetic-token-not-real"}) as client:
        response = client.get("/api/documents/DOC-CLIN-ABC123/original")
    assert response.status_code == 200
    assert response.content == b"synthetic-original"
    assert response.headers["content-type"].startswith(mime)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "inline" in response.headers["content-disposition"]
    manager.object_storage.get_object.assert_called_once_with(namespace_name="test-only", bucket_name=bucket, object_name="DOC-CLIN-ABC123." + extension)


@pytest.mark.parametrize("principal,code", [(None, 401), (Principal("other", False), 403)])
def test_no_anonymous_or_other_user_original(original, principal, code):
    _, manager, identity = original
    identity.return_value = principal
    with TestClient(app, cookies={"mediflow_session": "synthetic-token-not-real"}) as client:
        response = client.get("/api/documents/DOC-CLIN-ABC123/original")
    assert response.status_code == code
    manager.object_storage.get_object.assert_not_called()


def test_auditor_reads_anonymous_upload(original):
    payload, _, identity = original
    payload["cargado_por"] = None
    identity.return_value = Principal("auditor", True)
    with TestClient(app, cookies={"mediflow_session": "synthetic-token-not-real"}) as client:
        assert client.get("/api/documents/DOC-CLIN-ABC123/original").status_code == 200


@pytest.mark.parametrize("location", [
    {"bucket": "private-unrelated", "ruta_objeto": "DOC-CLIN-ABC123.jpg"},
    {"bucket": "recibidos", "ruta_objeto": "other-document.jpg"},
    {"bucket": "recibidos", "ruta_objeto": "DOC-CLIN-ABC123.html"},
    {"bucket": "recibidos", "ruta_objeto": "../DOC-CLIN-ABC123.jpg"},
])
def test_untrusted_reference_does_not_access_another_original(original, location):
    payload, manager, _ = original
    payload["almacenamiento_oci"].update(location)
    with TestClient(app, cookies={"mediflow_session": "synthetic-token-not-real"}) as client:
        assert client.get("/api/documents/DOC-CLIN-ABC123/original").status_code == 502
    manager.object_storage.get_object.assert_not_called()


def test_missing_original_and_storage_error_do_not_leak(original):
    _, manager, _ = original
    manager.object_storage.get_object.side_effect = RuntimeError("SECRET")
    with TestClient(app, cookies={"mediflow_session": "synthetic-token-not-real"}) as client:
        response = client.get("/api/documents/DOC-CLIN-ABC123/original")
    assert response.status_code == 502
    assert "SECRET" not in response.text


def test_original_missing_metadata_is_404(original):
    _, manager, _ = original
    manager.recuperar_resultado_triage.return_value = None
    with TestClient(app, cookies={"mediflow_session": "synthetic-token-not-real"}) as client:
        assert client.get("/api/documents/DOC-CLIN-ABC123/original").status_code == 404
    manager.object_storage.get_object.assert_not_called()


@pytest.mark.parametrize("origin", ["http://127.0.0.1:8080", "https://desktop-edilanti.tailf48a22.ts.net:10000"])
def test_frontend_origin_preflight_preserves_credentials(origin):
    with TestClient(app) as client:
        response = client.options("/api/triage", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"
