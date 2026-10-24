"""Agregado por Edil: usuarios/sesiones sintéticos, sin OCI ni Gemini."""
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.auth import manage
from app.auth.routes import LoginRequest
from app.auth.store import (
    AuthSettings, SessionStore, InvalidCredentials, LoginRateLimited, COOKIE_NAME,
    hash_password, verify_password, normalize_username, DEFAULT_DB,
)

PASSWORD = "synthetic-password-only-for-tests"
ORIGIN = "https://mediflow-auth.test"


@pytest.fixture
def storage(tmp_path, monkeypatch):
    database = tmp_path / "private" / "auth.sqlite3"
    monkeypatch.setenv("MEDIFLOW_AUTH_DB_FILE", str(database))
    monkeypatch.setenv("MEDIFLOW_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.delenv("MEDIFLOW_SESSION_TTL_SECONDS", raising=False)
    return SessionStore()


def login(client, username="edil", password=PASSWORD, origin=ORIGIN):
    headers = {"Origin": origin} if origin is not None else {}
    return client.post("/api/auth/login", json={"username": username, "password": password}, headers=headers)


def test_password_hash_is_salted_and_not_recoverable_plaintext():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first.startswith("scrypt$32768$8$3$")
    assert first != second
    assert PASSWORD not in first
    assert verify_password(PASSWORD, first)
    assert not verify_password("wrong-password", first)
    assert not verify_password(PASSWORD, None)
    assert not verify_password(PASSWORD, "invalid-format")
    assert PASSWORD not in repr(LoginRequest(username="synthetic", password=PASSWORD))


@pytest.mark.parametrize("username", ["", "../edil", " user", "user ", "a/b", "x" * 129])
def test_invalid_username_is_rejected(username):
    with pytest.raises(ValueError):
        normalize_username(username)


def test_reading_anonymous_or_nonexistent_session_creates_no_database(tmp_path):
    database = tmp_path / "never-created" / "auth.sqlite3"
    store = SessionStore(AuthSettings(db_file=database))
    assert store.get_principal(None) is None
    assert store.get_principal("A" * 43) is None
    assert not database.exists()
    assert not database.parent.exists()


def test_auth_database_cannot_be_configured_under_public_web():
    with pytest.raises(ValueError):
        AuthSettings(db_file=DEFAULT_DB.parent.parent / "frontend_web/src/auth.sqlite3")


def test_sessions_are_random_hashed_and_survive_store_recreation(storage):
    principal = storage.add_user("Edil", PASSWORD, can_review=True)
    first, authenticated = storage.authenticate("EDIL", PASSWORD)
    second, _ = storage.authenticate("edil", PASSWORD)
    assert first != second
    assert principal == authenticated
    assert authenticated.login == "edil" and authenticated.can_review
    assert SessionStore(storage.settings).get_principal(first) == principal
    raw = storage.settings.db_file.read_bytes()
    assert PASSWORD.encode() not in raw
    assert first.encode() not in raw
    assert second.encode() not in raw
    storage.revoke(first)
    assert storage.get_principal(first) is None
    assert storage.get_principal(second) == principal


def test_session_expiry_disable_and_reset_revoke_access(tmp_path):
    now = [10000.0]
    store = SessionStore(AuthSettings(db_file=tmp_path / "auth.sqlite3", session_ttl_seconds=900), clock=lambda: now[0])
    store.add_user("edil", PASSWORD, can_review=True)
    token, _ = store.authenticate("edil", PASSWORD)
    now[0] += 901
    assert store.get_principal(token) is None
    token, _ = store.authenticate("edil", PASSWORD)
    store.reset_password("edil", PASSWORD + "-new")
    assert store.get_principal(token) is None
    with pytest.raises(InvalidCredentials):
        store.authenticate("edil", PASSWORD)
    token, _ = store.authenticate("edil", PASSWORD + "-new")
    store.disable_user("edil")
    assert store.get_principal(token) is None
    with pytest.raises(InvalidCredentials):
        store.authenticate("edil", PASSWORD + "-new")


def test_existing_users_are_not_overwritten(storage):
    storage.add_user("edil", PASSWORD)
    with pytest.raises(sqlite3.IntegrityError):
        storage.add_user("EDIL", PASSWORD + "-replacement", can_review=True)
    _, principal = storage.authenticate("edil", PASSWORD)
    assert not principal.can_review


def test_failed_login_limit_persists_with_fixed_clock_and_across_instances(tmp_path):
    now = [10000.0]
    settings = AuthSettings(db_file=tmp_path / "auth.sqlite3")
    store = SessionStore(settings, clock=lambda: now[0])
    store.add_user("edil", PASSWORD, can_review=True)
    for _ in range(5):
        with pytest.raises(InvalidCredentials):
            SessionStore(settings, clock=lambda: now[0]).authenticate("edil", "wrong", client_address="synthetic-peer")
    with pytest.raises(LoginRateLimited):
        store.authenticate("edil", PASSWORD, client_address="synthetic-peer")
    now[0] += 901
    assert store.authenticate("edil", PASSWORD, client_address="synthetic-peer")[1].can_review


def test_changing_usernames_cannot_bypass_peer_rate_limit(tmp_path):
    store = SessionStore(AuthSettings(db_file=tmp_path / "auth.sqlite3"), clock=lambda: 10000.0)
    for number in range(20):
        with pytest.raises(InvalidCredentials):
            store.authenticate(f"unknown-{number}", "wrong", client_address="synthetic-peer")
    with pytest.raises(LoginRateLimited):
        store.authenticate("unknown-21", "wrong", client_address="synthetic-peer")


def test_login_cookie_and_session_use_own_credentials_not_tailscale(storage):
    storage.add_user("edil", PASSWORD, can_review=True)
    with TestClient(app, base_url=ORIGIN) as client:
        anonymous = client.get("/api/auth/session", headers={"Tailscale-User-Login": "edil"})
        assert anonymous.json() == {"authenticated": False, "user": None}
        response = login(client)
        assert response.status_code == 200
        assert response.json() == {"authenticated": True, "user": {"login": "edil", "canReview": True}}
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
        assert "Path=/" in cookie and "Domain=" not in cookie and "Max-Age=28800" in cookie
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/auth/session").json() == response.json()
        # Un header inventado no cambia la cuenta asociada a la cookie.
        assert client.get("/api/auth/session", headers={"Tailscale-User-Login": "other"}).json() == response.json()
        logout = client.post("/api/auth/logout", headers={"Origin": ORIGIN})
        assert logout.status_code == 204
        assert client.get("/api/auth/session").json()["authenticated"] is False


def test_non_auditor_can_login_but_cannot_record_decisions(storage, monkeypatch):
    from app.api import routes
    storage.add_user("reader", PASSWORD)
    monkeypatch.setattr(routes, "OCIStorageManager", lambda: (_ for _ in ()).throw(AssertionError("No OCI")))
    with TestClient(app, base_url=ORIGIN) as client:
        assert login(client, username="reader").json()["user"]["canReview"] is False
        response = client.post("/api/documents/DOC-SYNTHETIC/review", headers={"Origin": ORIGIN},
            json={"decision": "aprobado", "reviewer_id": "reader", "observacion": None, "expected_review_status": "pendiente"})
        assert response.status_code == 403


@pytest.mark.parametrize("origin", [None, "null", "https://foreign.test"])
def test_login_and_logout_reject_foreign_or_missing_origins(storage, origin):
    with TestClient(app, base_url=ORIGIN) as client:
        assert login(client, origin=origin).status_code == 403
        headers = {"Origin": origin} if origin is not None else {}
        assert client.post("/api/auth/logout", headers=headers).status_code == 403
    assert not storage.settings.db_file.exists()


def test_validation_and_auth_errors_never_reflect_password_or_configuration(storage):
    storage.add_user("edil", PASSWORD, can_review=True)
    with TestClient(app, base_url=ORIGIN) as client:
        for payload in [
            {"username": "../invalid", "password": PASSWORD},
            {"username": "edil", "password": PASSWORD, "extra": PASSWORD},
            {"username": "edil", "password": {"secret": PASSWORD}},
        ]:
            response = client.post("/api/auth/login", headers={"Origin": ORIGIN}, json=payload)
            assert response.status_code == 422
            assert PASSWORD not in response.text
        assert login(client, password="incorrect").status_code == 401
        for _ in range(4):
            assert login(client, password="incorrect").status_code == 401
        limited = login(client)
        assert limited.status_code == 429 and limited.headers["retry-after"] == "900"
        assert PASSWORD not in limited.text


def test_request_body_is_bounded_and_invalid_config_is_sanitized(storage, monkeypatch):
    with TestClient(app, base_url=ORIGIN) as client:
        response = client.post("/api/auth/login", headers={"Origin": ORIGIN, "Content-Type": "application/json"}, content="x" * 17000)
        assert response.status_code == 413
        monkeypatch.setenv("MEDIFLOW_PUBLIC_ORIGIN", "https://secret:private@invalid.test")
        response = login(client)
        assert response.status_code == 503
        assert "private" not in response.text


def test_http_cookie_only_for_explicit_loopback_development(storage, monkeypatch):
    monkeypatch.delenv("MEDIFLOW_PUBLIC_ORIGIN")
    storage.add_user("edil", PASSWORD, can_review=True)
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = login(client, origin="http://127.0.0.1:8000")
        assert response.status_code == 200
        assert "Secure" not in response.headers["set-cookie"]
        assert client.get("/api/auth/session").json()["authenticated"] is True
    with TestClient(app, base_url="http://untrusted.test") as client:
        assert login(client, origin="http://untrusted.test").status_code == 503


def test_cli_creation_uses_hidden_prompt_and_no_password_argument(storage, monkeypatch, capsys):
    answers = iter([PASSWORD, PASSWORD])
    monkeypatch.setattr(manage.getpass, "getpass", lambda prompt: next(answers))
    monkeypatch.setattr("sys.argv", ["manage", "add-auditor", "edil"])
    manage.main()
    assert PASSWORD not in capsys.readouterr().out
    assert storage.authenticate("edil", PASSWORD)[1].can_review


def test_cli_mismatch_does_not_create_account(storage, monkeypatch):
    answers = iter([PASSWORD, PASSWORD + "-mismatch"])
    monkeypatch.setattr(manage.getpass, "getpass", lambda prompt: next(answers))
    monkeypatch.setattr("sys.argv", ["manage", "add-auditor", "edil"])
    with pytest.raises(SystemExit):
        manage.main()
    assert not storage.settings.db_file.exists()
