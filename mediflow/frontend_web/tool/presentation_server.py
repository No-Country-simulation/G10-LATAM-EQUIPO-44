"""Agregado por Edil: web y API bajo un origen para la presentación privada.

No activa Tailscale. Solo escucha en loopback.
Sirve exclusivamente frontend_web/src; .env y fuentes privadas no se publican.
"""
from pathlib import Path
import argparse
import json
import re
import sqlite3
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "backend"))

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.requests import HTTPConnection
from starlette.concurrency import run_in_threadpool
from app.main import app as backend
from app.core.review_auth import Principal


def create_application(*, enable_approved_reviews=False, auth_settings=None, session_resolver=None):
    from app.auth.store import AuthSettings, SessionStore
    settings = auth_settings if auth_settings is not None else AuthSettings.from_environment()
    resolve_session = session_resolver if session_resolver is not None else SessionStore(settings).get_principal
    class PresentationFiles(StaticFiles):
        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            if path.endswith(".html") and response.status_code == 200:
                html = Path(response.path).read_text(encoding="utf-8")
                # HTTPS del navegador se conserva al pasar por Tailscale Serve.
                # No usar localhost desde el teléfono ni incrustar secretos.
                enabled = "true" if enable_approved_reviews else "false"
                principal = scope.get("state", {}).get("mediflow_principal")
                identity = {"login": principal.login, "canReview": principal.can_review} if principal else None
                # Agregado por Edil: identidad para mostrar, nunca un token ni
                # una identidad elegida por el navegador. Backend valida de nuevo.
                identity_json = json.dumps(identity, ensure_ascii=True).replace("<", "\\u003c").replace("&", "\\u0026")
                config = ("<script>window.MEDIFLOW_API_BASE_URL=window.location.origin;"
                          f"window.MEDIFLOW_REVIEW_CONTRACT_APPROVED={enabled};"
                          f"window.MEDIFLOW_AUTHENTICATED_USER={identity_json};</script>")
                return HTMLResponse(html.replace("</head>", config + "</head>"),
                                    headers={"Cache-Control": "no-store"})
            return response

    application = Starlette(routes=[
        Mount("/web", app=PresentationFiles(directory=PROJECT / "frontend_web/src", html=True)),
        Mount("/", app=backend),
    ])

    class ReviewApprovalGate:
        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                # Agregado por Edil: Tailscale solo transporta el tráfico.
                # Antes: principal_from_proxy(scope, settings).
                # HTML usa la sesión de MediFlow; la API tiene su middleware
                # propio para funcionar también sin este servidor de presentación.
                scope = dict(scope)
                scope["state"] = dict(scope.get("state", {}))
                if scope.get("path", "").startswith("/web/"):
                    token = HTTPConnection(scope).cookies.get("mediflow_session")
                    try:
                        principal = await run_in_threadpool(resolve_session, token)
                    except (sqlite3.Error, OSError, ValueError):
                        # La pantalla de acceso sigue disponible si la base de
                        # sesiones falla; nunca se inventa una identidad.
                        principal = None
                    scope["state"]["mediflow_principal"] = principal if isinstance(principal, Principal) else None
                    scope["state"]["mediflow_public_origin"] = settings.public_origin
            # Agregado por Edil: no basta ocultar botones. Bloquear también
            # la escritura por Swagger/HTTP en este despliegue hasta aprobar
            # el contrato, sin reescribir la API de Drazen ni su persistencia.
            if (not enable_approved_reviews and scope["type"] == "http"
                    and scope.get("method") == "POST"
                    and re.fullmatch(r"/api/documents/[^/]+/review/?", scope.get("path", ""))):
                response = JSONResponse({"detail": "Las decisiones de revisión no están habilitadas para esta presentación."}, status_code=403)
                await response(scope, receive, send)
                return
            await application(scope, receive, send)

    return ReviewApprovalGate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--enable-approved-reviews", action="store_true",
                        help="Usar solo después de la aprobación del contrato por el equipo.")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1 y 65535.")
    import uvicorn
    uvicorn.run(create_application(enable_approved_reviews=args.enable_approved_reviews),
                host="127.0.0.1", port=args.port, access_log=False,
                proxy_headers=False)


if __name__ == "__main__":
    main()
