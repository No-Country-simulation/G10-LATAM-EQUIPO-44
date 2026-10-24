"""Agregado por Edil: inicio/cierre de sesión propios de MediFlow."""
import json
import sqlite3

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
from starlette.concurrency import run_in_threadpool

from .origin import require_same_origin
from .store import (
    COOKIE_NAME, AuthSettings, SessionStore, InvalidCredentials, LoginRateLimited, normalize_username,
)

router = APIRouter(prefix="/api/auth", tags=["Usuarios MediFlow"])
MAX_LOGIN_BODY_BYTES = 16 * 1024


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=128)
    password: SecretStr = Field(repr=False)


def session_payload(principal):
    return {"authenticated": principal is not None,
            "user": {"login": principal.login, "canReview": principal.can_review} if principal else None}


async def parse_login(request: Request):
    # Agregado por Edil: no usar el manejador genérico de errores de body,
    # que puede reflejar en 422 el valor recibido de una contraseña.
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise HTTPException(415, detail="El inicio de sesión requiere JSON.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_LOGIN_BODY_BYTES:
            raise HTTPException(413, detail="La solicitud de inicio de sesión es demasiado grande.")
        body.extend(chunk)
    try:
        parsed = LoginRequest.model_validate(json.loads(body))
        normalize_username(parsed.username)
        if not 1 <= len(parsed.password.get_secret_value()) <= 1024:
            raise ValueError()
        return parsed
    except (ValueError, TypeError, ValidationError, UnicodeDecodeError):
        raise HTTPException(422, detail="Revisa el usuario y la contraseña enviados.") from None


@router.post("/login", summary="Iniciar sesión en MediFlow", openapi_extra={
    "requestBody": {"required": True, "content": {"application/json": {"schema": {
        "type": "object", "additionalProperties": False, "required": ["username", "password"],
        "properties": {"username": {"type": "string", "maxLength": 128},
                       "password": {"type": "string", "format": "password", "writeOnly": True, "maxLength": 1024}}
    }}}}
})
async def login(request: Request):
    origin = require_same_origin(request)
    parsed = await parse_login(request)
    try:
        settings = AuthSettings.from_environment()
        store = SessionStore(settings)
        token, principal = await run_in_threadpool(store.authenticate,
            parsed.username, parsed.password.get_secret_value(),
            client_address=request.client.host if request.client else "unknown")
        # Rotar la cookie al autenticar; no reutilizar una sesión enviada por
        # el cliente como identidad nueva.
        await run_in_threadpool(store.revoke, request.cookies.get(COOKIE_NAME))
    except InvalidCredentials:
        raise HTTPException(401, detail="Usuario o contraseña incorrectos.") from None
    except LoginRateLimited:
        raise HTTPException(429, detail="Demasiados intentos. Espera antes de volver a iniciar sesión.",
                            headers={"Retry-After": "900"}) from None
    except (sqlite3.Error, OSError, ValueError):
        raise HTTPException(503, detail="El inicio de sesión no está disponible.") from None
    response = JSONResponse(session_payload(principal), headers={"Cache-Control": "no-store"})
    response.set_cookie(COOKIE_NAME, token, max_age=settings.session_ttl_seconds,
                        httponly=True, secure=origin.startswith("https://"), samesite="strict", path="/")
    return response


@router.get("/session", summary="Consultar la sesión de MediFlow")
async def session(request: Request):
    if getattr(request.state, "mediflow_auth_unavailable", False):
        raise HTTPException(503, detail="La sesión no se pudo consultar.")
    principal = getattr(request.state, "mediflow_principal", None)
    return JSONResponse(session_payload(principal), headers={"Cache-Control": "no-store"})


@router.post("/logout", status_code=204, summary="Cerrar sesión en MediFlow")
async def logout(request: Request):
    origin = require_same_origin(request)
    try:
        await run_in_threadpool(SessionStore().revoke, request.cookies.get(COOKIE_NAME))
    except (sqlite3.Error, OSError, ValueError):
        raise HTTPException(503, detail="No se pudo cerrar la sesión. Intenta nuevamente.") from None
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True,
                           secure=origin.startswith("https://"), samesite="strict")
    return response
