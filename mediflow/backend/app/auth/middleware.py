"""Agregado por Edil: sesión propia para API, también usando Uvicorn directo."""
import sqlite3

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool

from .origin import expected_origin
from .store import COOKIE_NAME, get_principal_from_session


class LocalSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # No leer nombres de usuario ni headers de identidad del proxy.
        request.state.mediflow_principal = None
        request.state.mediflow_auth_unavailable = False
        try:
            request.state.mediflow_public_origin = expected_origin(request)
            token = request.cookies.get(COOKIE_NAME)
            if token:
                request.state.mediflow_principal = await run_in_threadpool(get_principal_from_session, token)
        except (sqlite3.Error, OSError, ValueError):
            request.state.mediflow_public_origin = None
            request.state.mediflow_auth_unavailable = True
        return await call_next(request)
