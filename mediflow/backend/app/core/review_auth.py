"""Agregado por Edil: identidad de MediFlow y permiso explícito de auditoría.

La API nunca autentica usando reviewer_id ni leyendo headers de identidad por
su cuenta. La sesión propia de MediFlow crea Principal dentro del servidor.
Se conserva el proveedor anterior de proxy como referencia inactiva; el
servidor de presentación ya no lo conecta a las peticiones.
"""
from dataclasses import dataclass
import os
import re
from urllib.parse import urlsplit

from fastapi import HTTPException, Request


def canonical_login(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@+:-]{0,319}", value):
        raise ValueError("El identificador de usuario no es válido.")
    return value.casefold()


@dataclass(frozen=True)
class Principal:
    login: str
    can_review: bool = False


@dataclass(frozen=True)
class PresentationAuthSettings:
    mode: str = "disabled"
    public_origin: str = ""
    reviewer_logins: frozenset[str] = frozenset()

    def __post_init__(self):
        if self.mode not in {"disabled", "tailscale"}:
            raise ValueError("MEDIFLOW_AUTH_MODE debe ser disabled o tailscale.")
        if self.mode == "tailscale":
            parsed = urlsplit(self.public_origin)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment or parsed.port not in {None, 443}):
                raise ValueError("MEDIFLOW_PUBLIC_ORIGIN debe ser un origen HTTPS sin ruta.")
            if self.public_origin != f"https://{parsed.netloc.lower()}":
                raise ValueError("MEDIFLOW_PUBLIC_ORIGIN debe estar normalizado y sin barra final.")
        for login in self.reviewer_logins:
            if canonical_login(login) != login:
                raise ValueError("Las identidades permitidas deben estar normalizadas.")

    @classmethod
    def from_environment(cls):
        return cls(
            mode=os.getenv("MEDIFLOW_AUTH_MODE", "disabled").strip().lower(),
            public_origin=os.getenv("MEDIFLOW_PUBLIC_ORIGIN", "").strip(),
            reviewer_logins=frozenset(canonical_login(part.strip())
                for part in os.getenv("MEDIFLOW_REVIEWER_LOGINS", "").split(",") if part.strip()),
        )


def principal_from_proxy(scope, settings: PresentationAuthSettings):
    """Referencia anterior, no utilizada por el servidor actual.

    Uvicorn debe usar proxy_headers=False para comprobar el peer TCP original.
    El administrador local y Tailscale son parte de esta frontera de confianza.
    Un Uvicorn directo no instala esta función y no puede aceptar esos headers.
    """
    if settings.mode != "tailscale":
        return None
    peer = scope.get("client") or ("", 0)
    if peer[0] not in {"127.0.0.1", "::1"}:
        return None
    headers = scope.get("headers", [])
    hosts = [v.decode("latin-1") for k, v in headers if k.lower() == b"host"]
    logins = [v.decode("latin-1") for k, v in headers if k.lower() == b"tailscale-user-login"]
    if hosts != [urlsplit(settings.public_origin).netloc] or len(logins) != 1:
        return None
    try:
        login = canonical_login(logins[0])
    except ValueError:
        return None
    return Principal(login=login, can_review=login in settings.reviewer_logins)


def require_auditor(request: Request) -> Principal:
    principal = getattr(request.state, "mediflow_principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="Debe iniciar sesión en MediFlow para registrar una revisión.")
    if not principal.can_review:
        raise HTTPException(status_code=403, detail="Esta cuenta no tiene permiso de auditor.")
    # Agregado por Edil: la sesión del navegador no sustituye comprobar el
    # origen de una escritura. CORS abierto tampoco sustituye esta validación.
    origin = getattr(request.state, "mediflow_public_origin", None)
    if not origin or request.headers.get("origin") != origin or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="La revisión debe enviarse desde el panel autorizado.")
    return principal
