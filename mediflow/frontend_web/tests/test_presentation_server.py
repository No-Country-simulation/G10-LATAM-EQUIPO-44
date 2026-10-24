"""Agregado por Edil: enrutamiento de presentación, sin OCI/Gemini."""
import importlib.util
from pathlib import Path
import pytest

from starlette.testclient import TestClient

module_path = Path(__file__).resolve().parents[1] / "tool/presentation_server.py"
spec = importlib.util.spec_from_file_location("mediflow_presentation", module_path)
presentation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(presentation)
from app.auth.store import AuthSettings, SessionStore

AUTH = AuthSettings(public_origin="https://presentation.test")
DISABLED_AUTH = AuthSettings()


@pytest.fixture
def local_accounts(tmp_path, monkeypatch):
    # Agregado por Edil: cuentas ficticias solo dentro de la carpeta de pytest.
    monkeypatch.setenv("MEDIFLOW_AUTH_DB_FILE", str(tmp_path / "users.sqlite3"))
    monkeypatch.setenv("MEDIFLOW_PUBLIC_ORIGIN", "https://presentation.test")
    store = SessionStore(AuthSettings.from_environment())
    store.add_user("auditor", "Synthetic-password-only-2026", can_review=True)
    store.add_user("reader", "Synthetic-password-only-2026", can_review=False)
    return store


def login(client, username="auditor"):
    response = client.post("/api/auth/login", json={"username": username, "password": "Synthetic-password-only-2026"},
                           headers={"Origin": "https://presentation.test"})
    assert response.status_code == 200


def test_web_uses_same_https_origin_and_decisions_are_disabled_by_default():
    with TestClient(presentation.create_application(auth_settings=DISABLED_AUTH), base_url="https://presentation.test") as client:
        result = client.get("/web/auditoria/index.html")
    assert result.status_code == 200
    assert "window.MEDIFLOW_API_BASE_URL=window.location.origin" in result.text
    assert "window.MEDIFLOW_REVIEW_CONTRACT_APPROVED=false" in result.text
    assert result.headers["cache-control"] == "no-store"


def test_existing_api_and_assets_are_accessible_without_new_business_endpoints():
    with TestClient(presentation.create_application(auth_settings=DISABLED_AUTH)) as client:
        assert client.get("/").json()["app"] == "MediFlow Backend"
        assert "/api/reviews/pending" in client.get("/openapi.json").json()["paths"]
        assert client.get("/web/assets/js/documents-api.js").status_code == 200


def test_private_configuration_and_directory_traversal_are_not_served():
    with TestClient(presentation.create_application(auth_settings=DISABLED_AUTH)) as client:
        for path in ["/web/.env", "/web/../backend/.env", "/web/%2e%2e/backend/.env", "/web/.git/config"]:
            assert client.get(path).status_code == 404


def test_unapproved_reviews_are_blocked_before_reaching_backend_or_oci(monkeypatch):
    from app.api import routes
    monkeypatch.setattr(routes, "OCIStorageManager", lambda: (_ for _ in ()).throw(AssertionError("No OCI access expected")))
    with TestClient(presentation.create_application(auth_settings=DISABLED_AUTH)) as client:
        result = client.post("/api/documents/DOC-SYNTHETIC/review", json={})
    assert result.status_code == 403


def test_approved_mode_reaches_normal_backend_validation_without_storage(local_accounts):
    with TestClient(presentation.create_application(enable_approved_reviews=True, auth_settings=local_accounts.settings),
                    base_url="https://presentation.test", client=("127.0.0.1", 12345)) as client:
        login(client)
        result = client.post("/api/documents/DOC-SYNTHETIC/review", json={},
            headers={"Origin": "https://presentation.test"})
    assert result.status_code == 422


def test_approved_contract_without_identity_cannot_write(monkeypatch):
    from app.api import routes
    monkeypatch.setattr(routes, "OCIStorageManager", lambda: (_ for _ in ()).throw(AssertionError("No OCI")))
    with TestClient(presentation.create_application(enable_approved_reviews=True, auth_settings=AUTH)) as client:
        result = client.post("/api/documents/DOC-SYNTHETIC/review", json={})
    assert result.status_code == 401


def test_own_session_identity_is_injected_per_request_and_never_cached(local_accounts):
    with TestClient(presentation.create_application(enable_approved_reviews=True, auth_settings=local_accounts.settings),
                    base_url="https://presentation.test", client=("127.0.0.1", 12345)) as client:
        login(client)
        result = client.get("/web/auditoria/index.html")
        assert '"login": "auditor", "canReview": true' in result.text
        assert "window.MEDIFLOW_REVIEW_CONTRACT_APPROVED=true" in result.text
        assert result.headers["cache-control"] == "no-store"
        login(client, "reader")
        unauthorized = client.get("/web/auditoria/index.html")
        assert '"login": "reader", "canReview": false' in unauthorized.text
        assert client.post("/api/auth/logout", headers={"Origin": "https://presentation.test"}).status_code == 204
        anonymous = client.get("/web/auditoria/index.html")
        assert "window.MEDIFLOW_AUTHENTICATED_USER=null" in anonymous.text


def test_authenticated_session_review_persists_canonical_principal_and_keeps_six_fields(monkeypatch, local_accounts):
    from types import SimpleNamespace
    from app.api import routes
    from app.core.oci_client import ReviewRecord
    saved = []
    def save(data):
        saved.append(data)
        return ReviewRecord.from_mapping(data)
    manager = SimpleNamespace(
        recuperar_resultado_triage=lambda doc_id: {"status": "auditoria_humana", "decision_enrutamiento": {"requiere_auditoria_humana": True}},
        get_latest_review_status=lambda doc_id: "pendiente", save_review_record=save,
    )
    monkeypatch.setattr(routes, "OCIStorageManager", lambda: manager)
    with TestClient(presentation.create_application(enable_approved_reviews=True, auth_settings=local_accounts.settings),
                    base_url="https://presentation.test", client=("127.0.0.1", 12345)) as client:
        login(client, "AUDITOR")
        response = client.post("/api/documents/DOC-SYNTHETIC/review",
            json={"decision": "aprobado", "reviewer_id": "auditor", "observacion": None, "expected_review_status": "pendiente"},
            headers={"Tailscale-User-Login": "ignored-network-user", "Origin": "https://presentation.test"})
    assert response.status_code == 200
    assert response.json() == saved[0]
    assert saved[0]["reviewer_id"] == "auditor"
    assert len(saved[0]) == 6


def test_own_session_upload_carries_authenticated_uploader_to_persistence_and_get(monkeypatch, local_accounts):
    from copy import deepcopy
    from types import SimpleNamespace
    from app.api import routes
    saved = {}
    def save(data):
        saved[data["documento_id"]] = deepcopy(data)
    manager = SimpleNamespace(settings=SimpleNamespace(bucket_recibidos="recibidos"),
        subir_a_recibidos=lambda content, name: name, guardar_resultado_triage=save,
        recuperar_resultado_triage=lambda doc_id: deepcopy(saved.get(doc_id)))
    monkeypatch.setattr(routes, "OCIStorageManager", lambda: manager)
    with TestClient(presentation.create_application(enable_approved_reviews=True, auth_settings=local_accounts.settings),
                    base_url="https://presentation.test", client=("127.0.0.1", 12345)) as client:
        login(client, "reader")
        response = client.post("/api/triage", files={"file": ("synthetic.txt", b"synthetic only")},
            data={"cargado_por": "spoofed"})
        assert response.status_code == 201
        data = response.json()
        assert data["cargado_por"] == "reader"
        assert saved[data["documento_id"]]["cargado_por"] == data["cargado_por"]
        assert client.get("/api/documents/" + data["documento_id"]).json() == data


def test_tailscale_identity_headers_never_create_a_mediflow_session(monkeypatch):
    from app.api import routes
    monkeypatch.setattr(routes, "OCIStorageManager", lambda: (_ for _ in ()).throw(AssertionError("No OCI")))
    with TestClient(presentation.create_application(enable_approved_reviews=True, auth_settings=AUTH),
                    base_url="https://presentation.test", client=("127.0.0.1", 12345)) as client:
        headers = {"Tailscale-User-Login": "auditor@example.test", "Origin": "https://presentation.test"}
        html = client.get("/web/auditoria/index.html", headers=headers).text
        assert "window.MEDIFLOW_AUTHENTICATED_USER=null" in html
        assert client.post("/api/documents/DOC-SYNTHETIC/review", json={}, headers=headers).status_code == 401
