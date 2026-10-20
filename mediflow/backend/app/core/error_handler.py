"""Errores públicos para la persistencia de revisiones humanas en OCI."""

from __future__ import annotations

try:
    from requests.exceptions import ConnectTimeout, ReadTimeout, Timeout
except ImportError:
    class Timeout(Exception):
        """Fallback para entornos sin requests."""

    ConnectTimeout = ReadTimeout = Timeout

try:
    from urllib3.exceptions import (
        ConnectTimeoutError,
        ReadTimeoutError,
        TimeoutError as Urllib3TimeoutError,
    )
except ImportError:
    class Urllib3TimeoutError(Exception):
        """Fallback para entornos sin urllib3."""

    ConnectTimeoutError = ReadTimeoutError = Urllib3TimeoutError

try:
    from oci.exceptions import RequestException as OCIRequestException
except ImportError:
    class OCIRequestException(Exception):
        """Fallback para entornos sin el SDK de OCI."""


class ReviewValidationError(ValueError):
    """El registro de revisión no cumple el contrato acordado."""


class DuplicateReviewError(RuntimeError):
    """El documento ya tiene una decisión final."""


class ReviewNotFoundError(LookupError):
    """No existe el registro de revisión solicitado."""


class OCIPersistenceError(RuntimeError):
    """OCI no confirmó una operación de persistencia."""


class OCICredentialsError(OCIPersistenceError):
    """OCI rechazó las credenciales de autenticación."""


class OCIPermissionDeniedError(OCIPersistenceError):
    """OCI rechazó los permisos para la operación solicitada."""


class OCITimeoutError(OCIPersistenceError):
    """La operación contra OCI agotó su tiempo de espera."""


class OCIIncompleteResponseError(OCIPersistenceError):
    """OCI devolvió una respuesta sin los datos requeridos."""


def map_oci_error(
    error: BaseException, *, duplicate_on_precondition: bool = False
) -> OCIPersistenceError | DuplicateReviewError:
    """Traduce errores de OCI sin exponer detalles del SDK.

    Un estado 412 se traduce a ``DuplicateReviewError`` únicamente cuando
    proviene de la escritura condicional de ``_final.json``; ningún otro
    código debe reinterpretarse como duplicado.
    """
    if isinstance(
        error,
        (
            TimeoutError,
            Timeout,
            ConnectTimeout,
            ReadTimeout,
            Urllib3TimeoutError,
            ConnectTimeoutError,
            ReadTimeoutError,
        ),
    ):
        return OCITimeoutError("OCI no respondió dentro del tiempo esperado.")
    if isinstance(error, OCIRequestException) and _has_timeout_cause(error):
        return OCITimeoutError("OCI no respondió dentro del tiempo esperado.")

    status = getattr(error, "status", None)
    if status == 401:
        return OCICredentialsError("OCI rechazó las credenciales.")
    if status == 403:
        return OCIPermissionDeniedError("OCI rechazó los permisos.")
    if status == 429 or isinstance(status, int) and status >= 500:
        return OCIPersistenceError("OCI no pudo completar la operación.")
    if status == 412 and duplicate_on_precondition:
        return DuplicateReviewError("La revisión ya existe.")
    return OCIPersistenceError("OCI no pudo completar la operación.")


def _has_timeout_cause(error: BaseException) -> bool:
    current: BaseException | None = error
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        cause = getattr(current, "__cause__", None) or getattr(
            current, "__context__", None
        )
        if cause is None:
            return False
        if isinstance(
            cause,
            (
                TimeoutError,
                Timeout,
                ConnectTimeout,
                ReadTimeout,
                Urllib3TimeoutError,
                ConnectTimeoutError,
                ReadTimeoutError,
            ),
        ):
            return True
        current = cause
    return False
