"""Cliente reutilizable de Oracle Cloud Infrastructure Object Storage.

La configuración se toma de variables de entorno. Las credenciales y las
claves privadas nunca se almacenan en el repositorio.
"""

from __future__ import annotations

import json
import re
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

    # Agregado por Edil: reutilizar la copia verificada de Brando sin cambiar el
    # método mover_archivo histórico ni sus parámetros de espera. El flujo
    # automático conserva siempre el original en recibidos; aquí no se borra.
    def copiar_archivo(
        self, nombre_archivo: str, bucket_origen: str, bucket_destino: str
    ) -> Any:
        from .oci_transfer import OCIObjectMover

        object_name = _required_name(nombre_archivo, "objeto")
        source_bucket = _required_name(bucket_origen, "bucket origen")
        destination_bucket = _required_name(bucket_destino, "bucket destino")
        region = self.config.get("region") or self.settings.region
        if not region:
            raise OCIConfigurationError("Falta la región OCI para copiar el documento.")
        return OCIObjectMover(
            self.object_storage, self.namespace, region
        ).copy(object_name, source_bucket, destination_bucket)

    # Métodos agregados por Drazen para Sprint 3 (S3-04A): persistencia, recuperación y verificación
    def obtener_objeto_bytes(self, nombre_bucket: str, nombre_objeto: str) -> bytes:
        """Obtiene el contenido binario de un objeto en memoria sin guardar en disco."""
        response = self.object_storage.get_object(
            namespace_name=self.namespace,
            bucket_name=_required_name(nombre_bucket, "bucket"),
            object_name=_required_name(nombre_objeto, "objeto"),
        )
        data = getattr(response, "data", None)
        if data is None:
            return b""
        if hasattr(data, "content") and isinstance(data.content, (bytes, bytearray)):
            return bytes(data.content)
        if hasattr(data, "raw") and hasattr(data.raw, "read"):
            return data.raw.read()
        if hasattr(data, "text"):
            return data.text.encode("utf-8")
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        return bytes(data)

    def guardar_json(
        self, datos: dict | str, nombre_bucket: str, nombre_objeto: str
    ) -> str:
        """Serializa y sube un diccionario o texto JSON a un bucket de OCI."""
        if isinstance(datos, dict):
            contenido_bytes = json.dumps(datos, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
        elif isinstance(datos, str):
            if not isinstance(json.loads(datos), dict):
                raise ValueError("El resultado JSON debe ser un objeto.")
            contenido_bytes = datos.encode("utf-8")
        else:
            raise ValueError("Los datos deben ser un diccionario o una cadena JSON.")
        return self.subir_archivo_desde_memoria(contenido_bytes, nombre_bucket, nombre_objeto)

    def recuperar_json(self, nombre_bucket: str, nombre_objeto: str) -> dict:
        """Descarga y deserializa un objeto JSON almacenado en OCI."""
        contenido = self.obtener_objeto_bytes(nombre_bucket, nombre_objeto)
        payload = json.loads(contenido.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("El JSON almacenado no es un objeto.")
        return payload

    def listar_objetos(
        self, nombre_bucket: str, prefix: str | None = None, limit: int | None = None
    ) -> list[str]:
        """Lista los nombres de los objetos presentes en un bucket."""
        if limit is not None and (type(limit) is not int or limit < 1):
            raise ValueError("El límite debe ser un entero positivo.")
        kwargs: dict[str, Any] = {
            "namespace_name": self.namespace,
            "bucket_name": _required_name(nombre_bucket, "bucket"),
        }
        if prefix:
            kwargs["prefix"] = prefix
        if limit:
            kwargs["limit"] = limit
        # Agregado por Edil: list_objects devuelve una página; continuar con next_start_with.
        nombres: list[str] = []
        tokens: set[str] = set()
        while True:
            if limit is not None:
                kwargs["limit"] = min(limit - len(nombres), 1000)
            response = self.object_storage.list_objects(**kwargs)
            data = getattr(response, "data", None)
            nombres.extend(item.name for item in (getattr(data, "objects", []) or []))
            if limit is not None and len(nombres) >= limit:
                return nombres[:limit]
            next_start = getattr(data, "next_start_with", None)
            if not isinstance(next_start, str) or not next_start:
                return nombres
            if next_start in tokens:
                raise RuntimeError("OCI repitió un marcador de paginación.")
            tokens.add(next_start)
            kwargs["start"] = next_start


    def verificar_conexion_buckets(self) -> dict[str, bool]:
        """Verifica la conectividad y acceso a los buckets de recibidos, procesados y auditoría."""
        resultados: dict[str, bool] = {}
        for nombre_bucket in [
            self.settings.bucket_recibidos,
            self.settings.bucket_procesados,
            self.settings.bucket_auditoria,
        ]:
            try:
                self.object_storage.get_bucket(
                    namespace_name=self.namespace,
                    bucket_name=nombre_bucket,
                )
                resultados[nombre_bucket] = True
            except Exception:
                resultados[nombre_bucket] = False
        return resultados

    def determinar_bucket_por_estado(self, status: str) -> str:
        """Determina el bucket correspondiente según el estado del documento."""
        # Agregado por Edil: no guardar estados desconocidos silenciosamente en recibidos.
        if status not in {"recibido", "procesado", "auditoria_humana"}:
            raise ValueError("Estado de documento no permitido.")
        if status == "auditoria_humana":
            return self.settings.bucket_auditoria
        elif status == "procesado":
            return self.settings.bucket_procesados
        return self.settings.bucket_recibidos

    def guardar_resultado_triage(self, triage_data: dict | Any) -> str:
        """Guarda el JSON del resultado de triaje en el bucket correspondiente a su estado."""
        if hasattr(triage_data, "model_dump"):
            payload = triage_data.model_dump()
        elif isinstance(triage_data, dict):
            payload = dict(triage_data)
        else:
            raise ValueError("triage_data debe ser un dict o modelo Pydantic.")

        doc_id = _validate_document_id(payload.get("documento_id"))

        estado = payload.get("status", "recibido")
        bucket = self.determinar_bucket_por_estado(estado)
        objeto_json = f"{doc_id}.json"

        return self.guardar_json(payload, bucket, objeto_json)

    def recuperar_resultado_triage(self, documento_id: str) -> dict | None:
        """Busca y recupera el JSON de un documento por su ID en los tres buckets."""
        objeto_json = f"{_validate_document_id(documento_id)}.json"
        # Priorizamos procesados y auditoria_humana sobre recibidos
        buckets_a_buscar = [
            self.settings.bucket_procesados,
            self.settings.bucket_auditoria,
            self.settings.bucket_recibidos,
        ]
        for bucket in buckets_a_buscar:
            try:
                return self.recuperar_json(bucket, objeto_json)
            except Exception as error:
                # Agregado por Edil: únicamente un 404 del SDK permite buscar en otro bucket.
                # Permisos, red y JSON inválido deben llegar al endpoint como error.
                if not _oci_not_found(error):
                    raise
        return None

    def listar_resultados_triage(
        self, status: str | None = None, limit: int | None = None,
        prioridad: str | None = None,
    ) -> list[dict]:
        """Lista y recupera los documentos JSON almacenados en los buckets."""
        # Agregado por Edil: selección anterior conservada. Consultar solo recibidos
        # incluía versiones antiguas de documentos que ya habían terminado.
        # if status:
        # buckets = [self.determinar_bucket_por_estado(status)]
        # else:
        # buckets = [
        # self.settings.bucket_procesados,
        # self.settings.bucket_auditoria,
        # self.settings.bucket_recibidos,
        # ]
        if status is not None and status not in {"recibido", "procesado", "auditoria_humana"}:
            raise ValueError("Estado no permitido.")
        buckets = [self.settings.bucket_procesados, self.settings.bucket_auditoria, self.settings.bucket_recibidos]

        if prioridad is not None and prioridad not in {"Rutina", "Urgente"}:
            raise ValueError("Prioridad no permitida.")
        if limit is not None and (type(limit) is not int or limit < 1):
            raise ValueError("El límite debe ser positivo.")
        vistos: set[str] = set()
        documentos: list[dict] = []
        for bucket in buckets:
            # Agregado por Edil: un fallo de lectura no equivale a una lista vacía.
            nombres = self.listar_objetos(bucket)
            for nombre in nombres:
                if nombre.endswith(".json"):
                    doc_id_candidato = nombre[:-5]
                    if doc_id_candidato in vistos:
                        continue
                    try:
                        doc = self.recuperar_json(bucket, nombre)
                        if isinstance(doc, dict) and "documento_id" in doc:
                            # Código anterior: filtrar estado antes de deduplicar.
                            # if status and doc.get("status") != status: continue
                            doc_id = doc["documento_id"]
                            if doc_id in vistos:
                                continue
                            vistos.add(doc_id)
                            # Agregado por Edil: filtrar la versión actual, no una recepción antigua.
                            if status and doc.get("status") != status:
                                continue
                            # Agregado por Edil: deduplicar primero y filtrar antes del límite.
                            # No usar una versión antigua de recibidos si la actual no coincide.
                            if prioridad and doc.get("clasificacion", {}).get("nivel_prioridad") != prioridad:
                                continue
                            documentos.append(doc)
                            if limit and len(documentos) >= limit:
                                return documentos
                    except Exception:
                        # No ocultar permisos, errores de red ni documentos corruptos.
                        raise
        return documentos


def _required_name(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"El nombre de {label} es obligatorio.")
    return value.strip()


# Agregado por Edil: nombres seguros para JSON derivados de IDs, sin rutas arbitrarias.
def _validate_document_id(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is None:
        raise ValueError("Identificador de documento inválido.")
    return value


def _oci_not_found(error: Exception) -> bool:
    # OCI puede devolver NotAuthorizedOrNotFound; 404 por sí solo no prueba permiso.
    return oci is not None and isinstance(error, oci.exceptions.ServiceError) and error.status == 404
