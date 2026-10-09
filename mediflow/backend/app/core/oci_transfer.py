"""Safe object transfers between OCI Object Storage buckets.

The transfer is deliberately independent from the document orchestration
pipeline.  It copies an object, verifies the destination content, and only
then deletes the source object.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Callable

import oci


class ObjectTransferError(RuntimeError):
    """Base error for a transfer that did not complete safely."""


class SourceObjectNotFoundError(ObjectTransferError):
    """The source object does not exist."""


class DestinationObjectExistsError(ObjectTransferError):
    """The destination already contains an object with the requested key."""


class TransferVerificationError(ObjectTransferError):
    """The copied object could not be verified."""


@dataclass(frozen=True)
class TransferResult:
    """Outcome returned after a successful copy-and-delete operation."""

    object_name: str
    source_bucket: str
    destination_bucket: str
    source_size: int
    destination_size: int
    sha256: str


class OCIObjectMover:
    """Move one OCI object without deleting an unverified source."""

    def __init__(
        self,
        object_storage: Any,
        namespace: str,
        region: str,
        *,
        sleep: Callable[[float], None] = time.sleep,
        poll_interval: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self.object_storage = object_storage
        self.namespace = namespace
        self.region = region
        self.sleep = sleep
        self.poll_interval = poll_interval
        self.timeout = timeout

    def move(
        self,
        object_name: str,
        source_bucket: str,
        destination_bucket: str,
    ) -> TransferResult:
        """Copy, verify, and delete ``object_name``.

        ``destination_object_if_none_match_e_tag="*"`` protects the copy
        against an object appearing at the destination between the preflight
        check and the copy request.
        """
        source_head = self._head_source(source_bucket, object_name)
        self._ensure_destination_is_empty(destination_bucket, object_name)

        details = oci.object_storage.models.CopyObjectDetails(
            source_object_name=object_name,
            destination_region=self.region,
            destination_namespace=self.namespace,
            destination_bucket=destination_bucket,
            destination_object_name=object_name,
            destination_object_if_none_match_e_tag="*",
        )
        try:
            response = self.object_storage.copy_object(
                namespace_name=self.namespace,
                bucket_name=source_bucket,
                copy_object_details=details,
            )
        except Exception as error:
            if self._is_conflict(error):
                raise DestinationObjectExistsError(
                    f"El destino ya contiene '{destination_bucket}/{object_name}'."
                ) from error
            raise ObjectTransferError(f"No se pudo copiar '{object_name}'.") from error

        self._wait_for_copy(response, destination_bucket, object_name)
        destination_head = self._head_destination(destination_bucket, object_name)
        source_hash = self._content_sha256(source_bucket, object_name)
        destination_hash = self._content_sha256(destination_bucket, object_name)
        if source_hash != destination_hash:
            raise TransferVerificationError(
                f"La verificación SHA-256 falló para '{object_name}'."
            )

        source_size = self._header_int(source_head, "content-length")
        destination_size = self._header_int(destination_head, "content-length")
        if source_size != destination_size:
            raise TransferVerificationError(
                f"El tamaño copiado no coincide para '{object_name}'."
            )

        try:
            self.object_storage.delete_object(
                namespace_name=self.namespace,
                bucket_name=source_bucket,
                object_name=object_name,
            )
        except Exception as error:
            raise ObjectTransferError(
                f"La copia fue verificada, pero no se eliminó el origen '{object_name}'."
            ) from error

        return TransferResult(
            object_name=object_name,
            source_bucket=source_bucket,
            destination_bucket=destination_bucket,
            source_size=source_size,
            destination_size=destination_size,
            sha256=source_hash,
        )

    def _head_source(self, bucket: str, object_name: str) -> Any:
        try:
            return self.object_storage.head_object(
                namespace_name=self.namespace,
                bucket_name=bucket,
                object_name=object_name,
            )
        except Exception as error:
            if self._is_not_found(error):
                raise SourceObjectNotFoundError(
                    f"No existe el origen '{bucket}/{object_name}'."
                ) from error
            raise ObjectTransferError(
                f"No se pudo consultar el origen '{bucket}/{object_name}'."
            ) from error

    def _ensure_destination_is_empty(self, bucket: str, object_name: str) -> None:
        try:
            self.object_storage.head_object(
                namespace_name=self.namespace,
                bucket_name=bucket,
                object_name=object_name,
            )
        except Exception as error:
            if self._is_not_found(error):
                return
            raise ObjectTransferError(
                f"No se pudo consultar el destino '{bucket}/{object_name}'."
            ) from error
        raise DestinationObjectExistsError(
            f"El destino ya contiene '{bucket}/{object_name}'."
        )

    def _head_destination(self, bucket: str, object_name: str) -> Any:
        try:
            return self.object_storage.head_object(
                namespace_name=self.namespace,
                bucket_name=bucket,
                object_name=object_name,
            )
        except Exception as error:
            raise TransferVerificationError(
                f"No se encontró el destino verificado '{bucket}/{object_name}'."
            ) from error

    def _wait_for_copy(self, response: Any, bucket: str, object_name: str) -> None:
        headers = getattr(response, "headers", {}) or {}
        work_request_id = headers.get("opc-work-request-id")
        deadline = time.monotonic() + self.timeout

        if work_request_id and hasattr(self.object_storage, "get_work_request"):
            while True:
                work_request = self.object_storage.get_work_request(work_request_id).data
                status = str(getattr(work_request, "status", "")).lower()
                if status in {"completed", "succeeded"}:
                    break
                if status in {"failed", "canceled", "cancelled"}:
                    raise ObjectTransferError(
                        f"La copia de '{object_name}' terminó con estado '{status}'."
                    )
                if time.monotonic() >= deadline:
                    raise ObjectTransferError(
                        f"La copia de '{object_name}' superó el tiempo de espera."
                    )
                self.sleep(self.poll_interval)

        while True:
            try:
                self.object_storage.head_object(
                    namespace_name=self.namespace,
                    bucket_name=bucket,
                    object_name=object_name,
                )
                return
            except Exception as error:
                if not self._is_not_found(error):
                    raise TransferVerificationError(
                        f"No se pudo confirmar la copia de '{object_name}'."
                    ) from error
                if time.monotonic() >= deadline:
                    raise TransferVerificationError(
                        f"No apareció el destino de '{object_name}' a tiempo."
                    )
                self.sleep(self.poll_interval)

    def _content_sha256(self, bucket: str, object_name: str) -> str:
        try:
            response = self.object_storage.get_object(
                namespace_name=self.namespace,
                bucket_name=bucket,
                object_name=object_name,
            )
            stream = getattr(getattr(response, "data", None), "raw", None)
            if stream is not None and hasattr(stream, "stream"):
                chunks = stream.stream(1024 * 1024, decode_content=False)
            else:
                chunks = [getattr(response, "data", b"")]
            digest = hashlib.sha256()
            for chunk in chunks:
                digest.update(chunk)
            return digest.hexdigest()
        except Exception as error:
            raise TransferVerificationError(
                f"No se pudo leer el contenido de '{bucket}/{object_name}'."
            ) from error

    @staticmethod
    def _header_int(response: Any, name: str) -> int:
        headers = getattr(response, "headers", {}) or {}
        value = headers.get(name) or headers.get(name.title())
        if value is None:
            raise TransferVerificationError(f"Falta el metadato '{name}'.")
        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise TransferVerificationError(
                f"El metadato '{name}' no es numérico."
            ) from error

    @staticmethod
    def _is_not_found(error: Exception) -> bool:
        return getattr(error, "status", None) == 404

    @staticmethod
    def _is_conflict(error: Exception) -> bool:
        return getattr(error, "status", None) in {409, 412}
