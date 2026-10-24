"""Agregado por Edil: origen de la aplicación, separado del proveedor de red."""
from fastapi import HTTPException, Request

from .store import AuthSettings


def expected_origin(request: Request, settings: AuthSettings | None = None):
    settings = settings or AuthSettings.from_environment()
    if settings.public_origin:
        return settings.public_origin
    # Desarrollo HTTP únicamente en loopback. Un Host de Internet no se
    # convierte por sí solo en el origen autorizado de una aplicación.
    peer = request.client.host if request.client else ""
    if (request.url.scheme == "http" and request.url.hostname in {"127.0.0.1", "localhost", "::1"}
            and peer in {"127.0.0.1", "::1", "localhost", "testclient"}):
        return f"{request.url.scheme}://{request.url.netloc}"
    return None


def require_same_origin(request: Request):
    try:
        origin = expected_origin(request)
    except (ValueError, OSError):
        raise HTTPException(503, detail="El origen de MediFlow todavía no está configurado correctamente.") from None
    if origin is None:
        raise HTTPException(503, detail="El origen de MediFlow todavía no está configurado.")
    if request.headers.get("origin") != origin or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, detail="La operación debe enviarse desde MediFlow.")
    return origin
