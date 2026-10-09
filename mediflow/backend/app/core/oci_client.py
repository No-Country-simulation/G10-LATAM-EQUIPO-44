"""Cliente reutilizable de Oracle Cloud Infrastructure Object Storage.

La configuración se toma de variables de entorno. Las credenciales y las
claves privadas nunca se almacenan en el repositorio.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    import oci
except ImportError:  # Permite probar la configuración sin instalar el SDK.
    oci = None  # type: ignore[assignment]


class OCIConfigurationError(RuntimeError):
    """La configuración necesaria para conectar con OCI no es válida."""


def _value(environment: Mapping[str, str], name: str, default: str = "") -> str:
    return environment.get(name, default).strip()


@dataclass(frozen=True)
class OCISettings:
    """Configuración no secreta y referencias a secretos de OCI."""

    config_file: str | None
    config_profile: str
    user_ocid: str | None
    fingerprint: str | None
    key_file: str | None
    tenancy_ocid: str | None
    region: str | None
    namespace: str | None
    bucket_recibidos: str = "recibidos"
    bucket_procesados: str = "procesados"
    bucket_auditoria: str = "auditoria_humana"

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> "OCISettings":
        environment = os.environ if environment is None else environment
        config_file = _value(environment, "OCI_CONFIG_FILE") or None
        return cls(
            bucket_recibidos=_value(environment, "OCI_BUCKET_RECIBIDOS", "recibidos"),
            bucket_procesados=_value(environment, "OCI_BUCKET_PROCESADOS", "procesados"),
            bucket_auditoria=_value(environment, "OCI_BUCKET_AUDITORIA", "auditoria_humana"),
            config_file=config_file,
            config_profile=_value(environment, "OCI_CONFIG_PROFILE", "DEFAULT"),
            user_ocid=_value(environment, "OCI_USER_OCID") or None,
            fingerprint=_value(environment, "OCI_FINGERPRINT") or None,
            key_file=_value(environment, "OCI_KEY_FILE") or None,
            tenancy_ocid=_value(environment, "OCI_TENANCY_OCID") or None,
            region=_value(environment, "OCI_REGION") or None,
            namespace=_value(environment, "OCI_NAMESPACE") or None,
        )

    def connection_config(self) -> dict[str, str]:
        """Devuelve una configuración compatible con el SDK de OCI."""
        sdk = _require_oci()
        explicit = {
            "user": self.user_ocid,
            "fingerprint": self.fingerprint,
            "key_file": str(Path(self.key_file).expanduser()) if self.key_file else None,
            "tenancy": self.tenancy_ocid,
            "region": self.region,
        }
        provided = [value is not None for value in explicit.values()]
        if any(provided):
            if not all(provided):
                missing = ", ".join(key for key, value in explicit.items() if value is None)
                raise OCIConfigurationError(
                    f"Faltan variables OCI para autenticación: {missing}."
                )
            config = {key: value for key, value in explicit.items() if value is not None}
            sdk.config.validate_config(config)
            return config
        if self.config_file:
            return sdk.config.from_file(
                file_location=str(Path(self.config_file).expanduser()),
                profile_name=self.config_profile,
            )
        return sdk.config.from_file(profile_name=self.config_profile)


def _require_oci() -> Any:
    if oci is None:
        raise OCIConfigurationError(
            "El paquete 'oci' no está instalado. Ejecuta pip install -r requirements.txt."
        )
    return oci


class OCIStorageManager:
    """Opera Object Storage usando los buckets definidos por ``OCISettings``."""

    def __init__(
        self,
        settings: OCISettings | None = None,
        *,
        object_storage_client: Any | None = None,
    ) -> None:
        self.settings = settings or OCISettings.from_environment()
        self.config = self.settings.connection_config() if object_storage_client is None else {}
        sdk = _require_oci() if object_storage_client is None else None
        self.object_storage = object_storage_client or sdk.object_storage.ObjectStorageClient(
            self.config
        )
        self.namespace = self.settings.namespace or self.object_storage.get_namespace().data

    def subir_archivo_desde_memoria(
        self, contenido_bytes: bytes, nombre_bucket: str, nombre_destino: str
    ) -> str:
        """Sube bytes a un bucket y devuelve el nombre del objeto creado."""
        self.object_storage.put_object(
            namespace_name=self.namespace,
            bucket_name=_required_name(nombre_bucket, "bucket"),
            object_name=_required_name(nombre_destino, "objeto"),
            put_object_body=contenido_bytes,
        )
        return nombre_destino

    def subir_a_recibidos(self, contenido_bytes: bytes, nombre_destino: str) -> str:
        """Guarda un documento en el bucket independiente de recibidos."""
        object_name = _required_name(nombre_destino, "objeto")
        return self.subir_archivo_desde_memoria(
            contenido_bytes, self.settings.bucket_recibidos, object_name
        )

    def subir_archivo(
        self, ruta_local: str | Path, nombre_bucket: str, nombre_destino: str
    ) -> str:
        """Sube un archivo local al bucket indicado."""
        path = Path(ruta_local)
        if not path.is_file():
            raise FileNotFoundError(f"El archivo local '{path}' no fue encontrado.")
        with path.open("rb") as file_handle:
            self.object_storage.put_object(
                namespace_name=self.namespace,
                bucket_name=_required_name(nombre_bucket, "bucket"),
                object_name=_required_name(nombre_destino, "objeto"),
                put_object_body=file_handle,
            )
        return nombre_destino

    def descargar_archivo(
        self, nombre_bucket: str, nombre_archivo: str, ruta_descarga: str | Path
    ) -> Path:
        """Descarga un objeto y devuelve la ruta local creada."""
        response = self.object_storage.get_object(
            namespace_name=self.namespace,
            bucket_name=_required_name(nombre_bucket, "bucket"),
            object_name=_required_name(nombre_archivo, "objeto"),
        )
        destination = Path(ruta_descarga)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            for chunk in response.data.raw.stream(1024 * 1024, decode_content=False):
                output.write(chunk)
        return destination

    def mover_archivo(
        self,
        nombre_archivo: str,
        bucket_origen: str,
        bucket_destino: str,
        *,
        wait_seconds: float = 1.5,
        max_attempts: int = 10,
    ) -> None:
        """Copia el objeto y elimina el origen solo al verificar el destino."""
        sdk = _require_oci()
        object_name = _required_name(nombre_archivo, "objeto")
        destination_bucket = _required_name(bucket_destino, "bucket destino")
        copy_details = sdk.object_storage.models.CopyObjectDetails(
            source_object_name=object_name,
            destination_region=self.config["region"],
            destination_namespace=self.namespace,
            destination_bucket=destination_bucket,
            destination_object_name=object_name,
        )
        self.object_storage.copy_object(
            self.namespace, _required_name(bucket_origen, "bucket origen"), copy_details
        )
        for _ in range(max_attempts):
            names = {
                item.name
                for item in self.object_storage.list_objects(
                    self.namespace, destination_bucket
                ).data.objects
            }
            if object_name in names:
                self.object_storage.delete_object(self.namespace, bucket_origen, object_name)
                return
            time.sleep(wait_seconds)
        raise TimeoutError(f"OCI no confirmó la copia de '{object_name}'.")


def _required_name(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"El nombre de {label} es obligatorio.")
    return value.strip()
