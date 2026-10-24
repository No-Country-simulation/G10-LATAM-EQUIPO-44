"""Cliente reutilizable de Oracle Cloud Infrastructure Object Storage.

La configuración se toma de variables de entorno. Las credenciales y las
claves privadas nunca se almacenan en el repositorio.
"""

from __future__ import annotations

import json
import base64
import hashlib
import re
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .error_handler import (
    OCIIncompleteResponseError,
    ReviewNotFoundError,
    ReviewValidationError,
    map_oci_error,
)

try:
    import oci
except ImportError:  # Permite probar la configuración sin instalar el SDK.
    oci = None  # type: ignore[assignment]


class OCIConfigurationError(RuntimeError):
    """La configuración necesaria para conectar con OCI no es válida."""


_REVIEW_FIELDS = frozenset(
    {
        "documento_id",
        "review_id",
        "review_status",
        "reviewer_id",
        "observacion",
        "reviewed_at",
    }
)
_REVIEW_ID_PATTERN = re.compile(r"REV-[A-Za-z0-9_-]{1,64}\Z")


@dataclass(frozen=True)
class ReviewRecord:
    """Registro exacto de una decisión final de auditoría humana."""

    documento_id: str
    review_id: str
    review_status: str
    reviewer_id: str
    observacion: str | None
    reviewed_at: str

    @classmethod
    def from_mapping(cls, record: Mapping[str, Any]) -> "ReviewRecord":
        """Valida y construye el registro sin aceptar campos de la solicitud HTTP."""
        if not isinstance(record, Mapping):
            raise ReviewValidationError("El registro de revisión debe ser un objeto.")
        extra_fields = set(record) - _REVIEW_FIELDS
        if extra_fields:
            raise ReviewValidationError("El registro contiene campos no permitidos.")
        if set(record) != _REVIEW_FIELDS:
            raise ReviewValidationError("El registro debe contener exactamente seis campos.")

        documento_id = record["documento_id"]
        if not isinstance(documento_id, str) or re.fullmatch(
            r"[A-Za-z0-9_-]{1,128}", documento_id
        ) is None:
            raise ReviewValidationError("El identificador de documento no es válido.")

        review_id = record["review_id"]
        if not isinstance(review_id, str) or (
            _REVIEW_ID_PATTERN.fullmatch(review_id) is None
            and not _is_uuid4(review_id)
        ):
            raise ReviewValidationError("El identificador de revisión no es válido.")

        review_status = record["review_status"]
        if review_status not in {"aprobado", "rechazado"}:
            raise ReviewValidationError("El estado de revisión no es válido.")

        reviewer_id = record["reviewer_id"]
        if not isinstance(reviewer_id, str) or not reviewer_id.strip():
            raise ReviewValidationError("El identificador del auditor es obligatorio.")

        observacion = record["observacion"]
        if observacion is not None and not isinstance(observacion, str):
            raise ReviewValidationError("La observación debe ser texto o null.")
        if review_status == "rechazado" and (
            observacion is None or not observacion.strip()
        ):
            raise ReviewValidationError(
                "Una revisión rechazada requiere una observación."
            )

        reviewed_at = record["reviewed_at"]
        if not _is_utc_z_datetime(reviewed_at):
            raise ReviewValidationError("La fecha de revisión no es un UTC ISO 8601 válido.")

        return cls(
            documento_id=documento_id,
            review_id=review_id,
            review_status=review_status,
            reviewer_id=reviewer_id,
            observacion=observacion,
            reviewed_at=reviewed_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Devuelve únicamente los seis campos persistibles del registro."""
        return {
            "documento_id": self.documento_id,
            "review_id": self.review_id,
            "review_status": self.review_status,
            "reviewer_id": self.reviewer_id,
            "observacion": self.observacion,
            "reviewed_at": self.reviewed_at,
        }


def _is_uuid4(value: str) -> bool:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return parsed.version == 4


def _is_utc_z_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0


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

    def save_review_record(self, record: Mapping[str, Any]) -> ReviewRecord:
        """Persiste una revisión final y su espejo verificando los bytes escritos."""
        review = ReviewRecord.from_mapping(record)
        final_key = f"reviews/{review.documento_id}/_final.json"
        mirror_key = f"reviews/{review.documento_id}/{review.review_id}.json"
        expected_prefix = f"reviews/{review.documento_id}/"
        if not final_key.startswith(expected_prefix) or not mirror_key.startswith(
            expected_prefix
        ):
            raise ReviewValidationError(
                "Las claves de revisión deben permanecer bajo reviews/."
            )

        content = json.dumps(
            review.to_dict(), sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
        content_md5 = base64.b64encode(hashlib.md5(content).digest()).decode("ascii")
        bucket = self.settings.bucket_auditoria

        try:
            final_response = self.object_storage.put_object(
                namespace_name=self.namespace,
                bucket_name=bucket,
                object_name=final_key,
                put_object_body=content,
                if_none_match="*",
                content_md5=content_md5,
            )
        except Exception as error:
            raise map_oci_error(error, duplicate_on_precondition=True) from None

        response_md5 = _response_header(final_response, "opc-content-md5")
        if response_md5 is None or response_md5 != content_md5:
            raise OCIIncompleteResponseError("OCI no confirmó la revisión final.")
        try:
            final_bytes = self.obtener_objeto_bytes(bucket, final_key)
        except Exception as error:
            raise map_oci_error(error) from None
        if final_bytes != content:
            raise OCIIncompleteResponseError("OCI no confirmó la revisión final.")

        try:
            self.object_storage.put_object(
                namespace_name=self.namespace,
                bucket_name=bucket,
                object_name=mirror_key,
                put_object_body=content,
                content_md5=content_md5,
            )
        except Exception as error:
            raise map_oci_error(error) from None
        try:
            mirror_bytes = self.obtener_objeto_bytes(bucket, mirror_key)
        except Exception as error:
            raise map_oci_error(error) from None
        if mirror_bytes != content:
            raise OCIIncompleteResponseError("OCI no confirmó el espejo de la revisión.")
        return review

    def get_review_record(self, documento_id: str, review_id: str) -> ReviewRecord:
        """Recupera una revisión por documento e identificador."""
        document_id = _validate_document_id(documento_id)
        validated_review_id = _validate_review_id(review_id)
        object_name = f"reviews/{document_id}/{validated_review_id}.json"
        try:
            content = self.obtener_objeto_bytes(self.settings.bucket_auditoria, object_name)
        except Exception as error:
            if _has_status(error, 404):
                raise ReviewNotFoundError("La revisión no existe.") from None
            raise map_oci_error(error) from None
        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise OCIIncompleteResponseError("OCI devolvió una revisión inválida.") from None
        try:
            return ReviewRecord.from_mapping(payload)
        except ReviewValidationError:
            raise

    def list_reviews_for_document(self, documento_id: str) -> list[ReviewRecord]:
        """Lista las revisiones de un documento ordenadas por fecha de revisión."""
        document_id = _validate_document_id(documento_id)
        prefix = f"reviews/{document_id}/"
        final_key = f"{prefix}_final.json"
        try:
            final_content = self.obtener_objeto_bytes(
                self.settings.bucket_auditoria, final_key
            )
        except Exception as error:
            if _has_status(error, 404):
                return []
            raise map_oci_error(error) from None
        try:
            final_payload = json.loads(final_content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise OCIIncompleteResponseError(
                "OCI devolvió una revisión inválida."
            ) from None
        final_record = ReviewRecord.from_mapping(final_payload)
        records_by_review_id = {final_record.review_id: final_record}
        try:
            names = self.listar_objetos(self.settings.bucket_auditoria, prefix=prefix)
        except Exception as error:
            raise map_oci_error(error) from None
        for object_name in names:
            if object_name == final_key or not object_name.endswith(".json"):
                continue
            try:
                content = self.obtener_objeto_bytes(
                    self.settings.bucket_auditoria, object_name
                )
            except Exception as error:
                if _has_status(error, 404):
                    continue
                raise map_oci_error(error) from None
            try:
                payload = json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise OCIIncompleteResponseError(
                    "OCI devolvió una revisión inválida."
                ) from None
            record = ReviewRecord.from_mapping(payload)
            records_by_review_id.setdefault(record.review_id, record)
        return sorted(
            records_by_review_id.values(),
            key=lambda item: _parse_review_timestamp(item.reviewed_at),
        )

    def get_latest_review_status(
        self, documento_id: str
    ) -> str:
        """Devuelve el estado de la decisión final o ``pendiente``."""
        document_id = _validate_document_id(documento_id)
        final_key = f"reviews/{document_id}/_final.json"
        try:
            self.object_storage.head_object(
                namespace_name=self.namespace,
                bucket_name=self.settings.bucket_auditoria,
                object_name=final_key,
            )
        except Exception as error:
            if _has_status(error, 404):
                return "pendiente"
            raise map_oci_error(error) from None
        try:
            content = self.obtener_objeto_bytes(self.settings.bucket_auditoria, final_key)
        except Exception as error:
            raise map_oci_error(error) from None
        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise OCIIncompleteResponseError("OCI devolvió una revisión inválida.") from None
        return ReviewRecord.from_mapping(payload).review_status

    def list_pending_reviews(self) -> list[dict]:
        """Lista triajes de auditoría que aún no tienen revisión final."""
        pending: list[dict] = []
        try:
            documents = self.listar_resultados_triage(status="auditoria_humana")
        except Exception as error:
            raise map_oci_error(error) from None
        for document in documents:
            document_id = _validate_document_id(document.get("documento_id"))
            final_key = f"reviews/{document_id}/_final.json"
            try:
                self.object_storage.head_object(
                    namespace_name=self.namespace,
                    bucket_name=self.settings.bucket_auditoria,
                    object_name=final_key,
                )
            except Exception as error:
                if _has_status(error, 404):
                    pending.append(document)
                    continue
                raise map_oci_error(error) from None
        return pending

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
                if "/" not in nombre and nombre.endswith(".json"):
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


def _response_header(response: Any, header_name: str) -> str | None:
    headers = getattr(response, "headers", None)
    if not isinstance(headers, Mapping):
        return None
    expected = header_name.lower()
    for name, value in headers.items():
        if isinstance(name, str) and name.lower() == expected:
            return value if isinstance(value, str) else None
    return None


def _has_status(error: BaseException, status: int) -> bool:
    return getattr(error, "status", None) == status


def _validate_review_id(value: Any) -> str:
    if not isinstance(value, str) or (
        _REVIEW_ID_PATTERN.fullmatch(value) is None and not _is_uuid4(value)
    ):
        raise ReviewValidationError("El identificador de revisión no es válido.")
    return value


def _parse_review_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value[:-1] + "+00:00")


# Agregado por Edil: nombres seguros para JSON derivados de IDs, sin rutas arbitrarias.
def _validate_document_id(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is None:
        raise ValueError("Identificador de documento inválido.")
    return value


def _oci_not_found(error: Exception) -> bool:
    # OCI puede devolver NotAuthorizedOrNotFound; 404 por sí solo no prueba permiso.
    return oci is not None and isinstance(error, oci.exceptions.ServiceError) and error.status == 404
