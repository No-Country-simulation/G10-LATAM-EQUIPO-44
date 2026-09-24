"""Adaptador y stub autocontenido para simular subidas a OCI."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

class OCIUploadError(Exception):
    """Excepción base de la operación de subida."""


class OCIConnectionError(OCIUploadError):
    """Error de red o de conectividad con OCI."""


class OCIConfigurationError(OCIUploadError):
    """Configuración o credenciales inválidas."""


class OCIInputError(OCIUploadError):
    """Archivo, ruta o dato de destino inválido."""


class OCIUploadAdapter:
    """Valida la entrada y traduce errores del cliente OCI a errores propios."""

    def __init__(self, client: object, namespace: str):
        try:
            if not hasattr(client, "put_object"):
                raise ValueError("el cliente no expone put_object")
            if not isinstance(namespace, str) or not namespace.strip():
                raise ValueError("el namespace es obligatorio")
            self.client = client
            self.namespace = namespace
        except (TypeError, ValueError) as error:
            raise OCIConfigurationError(f"Configuración OCI inválida: {error}") from error

    def upload_file(self, file_path: str | Path, bucket: str, object_name: str) -> dict[str, str]:
        """Sube un archivo local y devuelve su ubicación en OCI."""
        try:
            path = Path(file_path)
            if not path.is_file():
                raise FileNotFoundError(f"no existe el archivo '{file_path}'")
            if not isinstance(bucket, str) or not bucket.strip():
                raise ValueError("el bucket es obligatorio")
            if not isinstance(object_name, str) or not object_name.strip():
                raise ValueError("el nombre del objeto es obligatorio")
        except (TypeError, ValueError, OSError) as error:
            raise OCIInputError(f"Entrada de subida inválida: {error}") from error

        try:
            with path.open("rb") as file_handle:
                self.client.put_object(
                    namespace_name=self.namespace,
                    bucket_name=bucket,
                    object_name=object_name,
                    put_object_body=file_handle,
                )
        except (ConnectionError, TimeoutError) as error:
            raise OCIConnectionError(f"Problema de conectividad con OCI: {error}") from error
        except PermissionError as error:
            raise OCIConfigurationError(
                f"OCI rechazó la configuración o las credenciales: {error}"
            ) from error
        except OSError as error:
            raise OCIInputError(f"No se pudo leer el archivo: {error}") from error

        return {"namespace": self.namespace, "bucket": bucket, "object": object_name}


class StubOCIClient:
    """Cliente mínimo propio que simula ``put_object`` sin conectarse a OCI."""

    def __init__(self, failure: str | None = None):
        if failure not in (None, "network", "configuration"):
            raise ValueError("fallo simulado no soportado")
        self.failure = failure
        self.uploads: list[dict[str, str]] = []

    def put_object(
        self,
        *,
        namespace_name: str,
        bucket_name: str,
        object_name: str,
        put_object_body: BinaryIO,
    ) -> None:
        if self.failure == "network":
            raise ConnectionError("conexión simulada no disponible")
        if self.failure == "configuration":
            raise PermissionError("credenciales simuladas inválidas")
        self.uploads.append(
            {"namespace": namespace_name, "bucket": bucket_name, "object": object_name}
        )