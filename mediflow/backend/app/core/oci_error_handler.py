"""Capa de manejo de errores sobre el cliente OCI de Eliana."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .oci_client import OCIStorageManager, OCISettings
from .oci_client import OCIConfigurationError as ClientConfigurationError

try:
    from oci.exceptions import ConfigFileNotFound, InvalidConfig, RequestException, ServiceError
except ImportError:
    class _UnavailableSDKError(Exception):
        """No se produce durante pruebas sin SDK."""
    ConfigFileNotFound = InvalidConfig = RequestException = ServiceError = _UnavailableSDKError


class OCIUploadError(Exception):
    """Excepción base para errores controlados durante una subida."""


class OCIConnectionError(OCIUploadError):
    """La conexión o la comunicación con OCI falló."""


class OCIConfigurationError(OCIUploadError):
    """La configuración o las credenciales de OCI no son válidas."""


class OCIInputError(OCIUploadError):
    """La ruta, el archivo o los datos de entrada no son válidos."""


def upload_document(
    file_path: str | Path,
    bucket_name: str,
    object_name: str,
    config_profile: str = "DEFAULT",
) -> None:
    """Sube un archivo mediante ``OCIStorageManager`` y traduce sus errores."""
    if not isinstance(file_path, (str, Path)):
        raise OCIInputError("La ruta del archivo debe ser texto o Path")
    if not isinstance(bucket_name, str) or not bucket_name.strip():
        raise OCIInputError("El nombre del bucket es obligatorio")
    if not isinstance(object_name, str) or not object_name.strip():
        raise OCIInputError("El nombre del objeto es obligatorio")

    try:
        settings = replace(OCISettings.from_environment(), config_profile=config_profile)
        manager = OCIStorageManager(settings=settings)
        manager.subir_archivo(str(file_path), bucket_name, object_name)
    except (ConnectionError, TimeoutError, RequestException) as error:
        raise OCIConnectionError(f"No fue posible conectar con OCI: {error}") from error
    except (ClientConfigurationError, ConfigFileNotFound, InvalidConfig, PermissionError) as error:
        raise OCIConfigurationError(
            f"La configuración o las credenciales de OCI son inválidas: {error}"
        ) from error
    except (FileNotFoundError, IsADirectoryError, ValueError, TypeError, OSError) as error:
        raise OCIInputError(f"El archivo o la entrada no son válidos: {error}") from error
    except ServiceError as error:
        if getattr(error, "status", None) in (401, 403):
            raise OCIConfigurationError(
                f"OCI rechazó las credenciales o los permisos: {error}"
            ) from error
        raise OCIConnectionError(f"OCI devolvió un error de servicio: {error}") from error
