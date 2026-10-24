"""Agregado por Edil: identidad/permisos sin SDK ni credenciales reales."""
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request, Depends
from fastapi.testclient import TestClient

from app.main import app
from app.api import routes
from app.core.review_auth import (
    Principal, PresentationAuthSettings, canonical_login, principal_from_proxy, require_auditor,
)

ORIGIN = "https://presentation.test"
LOGIN = "auditor@example.test"


def settings(logins=(LOGIN,)):
    return PresentationAuthSettings("tailscale", ORIGIN, frozenset(logins))


def proxy_scope(headers=None, peer="127.0.0.1"):
    return {"client": (peer, 12345), "headers": headers if headers is not None else [
        (b"host", b"presentation.test"), (b"tailscale-user-login", LOGIN.encode())]}


def test_identity_is_canonical_and_authorization_is_explicit():
    assert canonical_login("Auditor@Example.Test") == LOGIN
    assert principal_from_proxy(proxy_scope(), settings()) == Principal(LOGIN, True)
    assert principal_from_proxy(proxy_scope(), settings(())) == Principal(LOGIN, False)
    assert principal_from_proxy(proxy_scope(), PresentationAuthSettings()) is None


@pytest.mark.parametrize("scope", [
    proxy_scope(peer="100.64.0.1"), proxy_scope(headers=[]),
    proxy_scope(headers=[(b"host", b"localhost"), (b"tailscale-user-login", LOGIN.encode())]),
    proxy_scope(headers=[(b"host", b"presentation.test"), (b"tailscale-user-login", b"invalid login")]),
    proxy_scope(headers=[(b"host", b"presentation.test"), (b"tailscale-user-login", LOGIN.encode()),
                         (b"tailscale-user-login", b"other@example.test")]),
])
def test_untrusted_peer_host_missing_duplicate_or_invalid_headers_do_not_authenticate(scope):
    assert principal_from_proxy(scope, settings()) is None


@pytest.mark.parametrize("origin", ["http://presentation.test", "https://user:secret@presentation.test", "https://presentation.test/path", "https://presentation.test/", "https://presentation.test?x=1"])
def test_invalid_public_origin_is_rejected(origin):
    with pytest.raises(ValueError):
        PresentationAuthSettings("tailscale", origin)


def test_settings_are_external_and_default_to_no_auditors(monkeypatch):
    monkeypatch.setenv("MEDIFLOW_AUTH_MODE", "tailscale")
    monkeypatch.setenv("MEDIFLOW_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.delenv("MEDIFLOW_REVIEWER_LOGINS", raising=False)
    assert PresentationAuthSettings.from_environment().reviewer_logins == frozenset()
    monkeypatch.setenv("MEDIFLOW_REVIEWER_LOGINS", " Auditor@Example.Test, second@example.test ")
    assert PresentationAuthSettings.from_environment().reviewer_logins == frozenset({LOGIN, "second@example.test"})


def payload(reviewer=LOGIN):
    return {"decision": "aprobado", "reviewer_id": reviewer, "observacion": None, "expected_review_status": "pendiente"}


def test_direct_backend_does_not_trust_identity_headers(monkeypatch):
    factory = MagicMock(side_effect=AssertionError("No OCI"))
    monkeypatch.setattr(routes, "OCIStorageManager", factory)
    with TestClient(app) as client:
        response = client.post("/api/documents/DOC-SYNTHETIC/review", json=payload(),
            headers={"Tailscale-User-Login": LOGIN, "Origin": ORIGIN})
    assert response.status_code == 401
    factory.assert_not_called()


@pytest.mark.parametrize("principal,origin,fetch_site,expected", [
    (None, ORIGIN, "same-origin", 401),
    (Principal(LOGIN, False), ORIGIN, "same-origin", 403),
    (Principal(LOGIN, True), "https://foreign.test", "cross-site", 403),
    (Principal(LOGIN, True), "null", "cross-site", 403),
    (Principal(LOGIN, True), None, "none", 403),
    (Principal(LOGIN, True), ORIGIN, "cross-site", 403),
])
def test_auth_rejections_precede_oci(monkeypatch, principal, origin, fetch_site, expected):
    isolated = FastAPI()
    @isolated.middleware("http")
    async def synthetic_proxy(request: Request, call_next):
        request.state.mediflow_principal = principal
        request.state.mediflow_public_origin = ORIGIN
        return await call_next(request)
    isolated.include_router(routes.router)
    factory = MagicMock(side_effect=AssertionError("No OCI"))
    monkeypatch.setattr(routes, "OCIStorageManager", factory)
    headers = {"Sec-Fetch-Site": fetch_site}
    if origin is not None:
        headers["Origin"] = origin
    with TestClient(isolated) as client:
        response = client.post("/api/documents/DOC-SYNTHETIC/review", json=payload(), headers=headers)
    assert response.status_code == expected
    factory.assert_not_called()


def test_forged_reviewer_is_rejected_before_storage(monkeypatch):
    factory = MagicMock(side_effect=AssertionError("No OCI"))
    monkeypatch.setattr(routes, "OCIStorageManager", factory)
    app.dependency_overrides[require_auditor] = lambda: Principal(LOGIN, True)
    try:
        with TestClient(app) as client:
            response = client.post("/api/documents/DOC-SYNTHETIC/review", json=payload("someone-else"))
        assert response.status_code == 403
        factory.assert_not_called()
    finally:
        app.dependency_overrides.pop(require_auditor, None)
