"""Pruebas locales del cliente OCI; no contactan servicios de Oracle."""

from __future__ import annotations

import unittest
import tempfile
import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from requests.exceptions import ReadTimeout

from app.core.error_handler import (
    DuplicateReviewError,
    OCIIncompleteResponseError,
    OCICredentialsError,
    OCIPermissionDeniedError,
    OCIPersistenceError,
    OCITimeoutError,
    ReviewNotFoundError,
    ReviewValidationError,
)
from app.core.oci_client import OCISettings, OCIStorageManager


class FakeObjectStorage:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


class SDKError(Exception):
    def __init__(self, status: int):
        self.status = status


class OCISettingsTest(unittest.TestCase):
    def test_local_profile_is_resolved_by_sdk_without_environment_secrets(self):
        settings = OCISettings.from_environment({"OCI_CONFIG_PROFILE": "SPRINT1"})
        with patch("app.core.oci_client.oci") as sdk:
            settings.connection_config()
            sdk.config.from_file.assert_called_once_with(profile_name="SPRINT1")

    def test_reads_bucket_names_from_environment(self) -> None:
        settings = OCISettings.from_environment(
            {
                "OCI_NAMESPACE": "namespace-demo",
                "OCI_BUCKET_RECIBIDOS": "recibidos-demo",
                "OCI_BUCKET_PROCESADOS": "procesados-demo",
                "OCI_BUCKET_AUDITORIA": "auditoria-demo",
            }
        )

        self.assertEqual(settings.namespace, "namespace-demo")
        self.assertEqual(settings.bucket_recibidos, "recibidos-demo")
        self.assertEqual(settings.bucket_procesados, "procesados-demo")
        self.assertEqual(settings.bucket_auditoria, "auditoria-demo")

    def test_uses_safe_default_bucket_names(self) -> None:
        settings = OCISettings.from_environment({})

        self.assertEqual(settings.bucket_recibidos, "recibidos")
        self.assertEqual(settings.bucket_procesados, "procesados")
        self.assertEqual(settings.bucket_auditoria, "auditoria_humana")


class OCIStorageManagerTest(unittest.TestCase):
    def test_download_preserves_object_content(self):
        storage = MagicMock()
        storage.get_object.return_value.data.raw.stream.return_value = [b"parte1", b"parte2"]
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        with tempfile.TemporaryDirectory() as folder:
            destination = manager.descargar_archivo(
                "recibidos", "test.txt", Path(folder) / "download.txt"
            )
            self.assertEqual(destination.read_bytes(), b"parte1parte2")
        storage.get_object.assert_called_once_with(
            namespace_name="demo", bucket_name="recibidos",
            object_name="test.txt",
        )

    def test_uploads_bytes_to_received_bucket(self) -> None:
        storage = FakeObjectStorage()
        settings = OCISettings.from_environment(
            {"OCI_NAMESPACE": "namespace-demo", "OCI_BUCKET_RECIBIDOS": "recibidos"}
        )
        manager = OCIStorageManager(settings, object_storage_client=storage)

        result = manager.subir_a_recibidos(b"contenido de prueba", "documento.txt")

        self.assertEqual(result, "documento.txt")
        self.assertEqual(
            storage.calls,
            [
                {
                    "namespace_name": "namespace-demo",
                    "bucket_name": "recibidos",
                    "object_name": "documento.txt",
                    "put_object_body": b"contenido de prueba",
                }
            ],
        )

    # Agregado por Edil: prueba faltante de subida local del módulo de Eliana,
    # sin acceder a OCI y sin atribuir esta corrección a su entrega original.
    def test_uploads_local_file_preserving_bytes(self):
        storage = MagicMock()
        uploaded = []
        storage.put_object.side_effect = lambda **kwargs: uploaded.append(
            (kwargs["bucket_name"], kwargs["object_name"], kwargs["put_object_body"].read())
        )
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "demo.txt"
            source.write_bytes(b"documento sintetico")
            result = manager.subir_archivo(source, "recibidos", "demo.txt")
            self.assertEqual(source.read_bytes(), b"documento sintetico")
        self.assertEqual(result, "demo.txt")
        self.assertEqual(uploaded, [("recibidos", "demo.txt", b"documento sintetico")])

    # Pruebas agregadas por Drazen para Sprint 3 (S3-04A): persistencia, recuperación y verificación
    def test_guardar_y_recuperar_json_en_memoria(self):
        storage = MagicMock()
        payload = {"documento_id": "DOC-TEST-001", "status": "procesado"}
        storage.get_object.return_value.data.content = b'{"documento_id": "DOC-TEST-001", "status": "procesado"}'

        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )

        saved_name = manager.guardar_json(payload, "procesados", "DOC-TEST-001.json")
        self.assertEqual(saved_name, "DOC-TEST-001.json")
        storage.put_object.assert_called_once()
        self.assertEqual(storage.put_object.call_args.kwargs["bucket_name"], "procesados")
        self.assertEqual(storage.put_object.call_args.kwargs["object_name"], "DOC-TEST-001.json")

        recuperado = manager.recuperar_json("procesados", "DOC-TEST-001.json")
        self.assertEqual(recuperado, payload)

    def test_verificar_conexion_buckets(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({
                "OCI_NAMESPACE": "demo",
                "OCI_BUCKET_RECIBIDOS": "recibidos",
                "OCI_BUCKET_PROCESADOS": "procesados",
                "OCI_BUCKET_AUDITORIA": "auditoria_humana",
            }),
            object_storage_client=storage,
        )
        # Todos accesibles
        estado = manager.verificar_conexion_buckets()
        self.assertEqual(estado, {"recibidos": True, "procesados": True, "auditoria_humana": True})

        # Si uno falla
        def mock_get_bucket(namespace_name, bucket_name):
            if bucket_name == "auditoria_humana":
                raise RuntimeError("Access denied")
            return MagicMock()
        storage.get_bucket.side_effect = mock_get_bucket
        estado_con_error = manager.verificar_conexion_buckets()
        self.assertEqual(estado_con_error, {"recibidos": True, "procesados": True, "auditoria_humana": False})

    def test_guardar_resultado_triage_enruta_bucket_correcto(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        # Procesado -> procesados
        manager.guardar_resultado_triage({"documento_id": "DOC-1", "status": "procesado"})
        self.assertEqual(storage.put_object.call_args.kwargs["bucket_name"], "procesados")
        self.assertEqual(storage.put_object.call_args.kwargs["object_name"], "DOC-1.json")

        # Auditoria -> auditoria_humana
        manager.guardar_resultado_triage({"documento_id": "DOC-2", "status": "auditoria_humana"})
        self.assertEqual(storage.put_object.call_args.kwargs["bucket_name"], "auditoria_humana")
        self.assertEqual(storage.put_object.call_args.kwargs["object_name"], "DOC-2.json")

        # Recibido -> recibidos
        manager.guardar_resultado_triage({"documento_id": "DOC-3", "status": "recibido"})
        self.assertEqual(storage.put_object.call_args.kwargs["bucket_name"], "recibidos")
        self.assertEqual(storage.put_object.call_args.kwargs["object_name"], "DOC-3.json")

    def test_recuperar_resultado_triage(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        # Si no existe en procesados ni auditoria, lo encuentra en recibidos
        def mock_get_object(namespace_name, bucket_name, object_name):
            if bucket_name == "recibidos" and object_name == "DOC-RECIBIDO.json":
                mock_res = MagicMock()
                mock_res.data.content = b'{"documento_id": "DOC-RECIBIDO", "status": "recibido"}'
                return mock_res
            # Agregado por Edil: simular el 404 real del SDK, no un error genérico de red.
            from oci.exceptions import ServiceError
            raise ServiceError(404, "ObjectNotFound", {}, "Objeto de prueba ausente")

        storage.get_object.side_effect = mock_get_object
        doc = manager.recuperar_resultado_triage("DOC-RECIBIDO")
        self.assertIsNotNone(doc)
        self.assertEqual(doc["documento_id"], "DOC-RECIBIDO")

        # Documento que no existe en ningún bucket
        doc_inexistente = manager.recuperar_resultado_triage("DOC-INEXISTENTE")
        self.assertIsNone(doc_inexistente)

    def test_save_review_record_writes_and_verifies_identical_bytes(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        record = {
            "documento_id": "DOC-REVIEW",
            "review_id": "REV-001",
            "review_status": "aprobado",
            "reviewer_id": "auditor-1",
            "observacion": None,
            "reviewed_at": "2026-10-20T15:30:00Z",
        }
        content = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
        content_md5 = base64.b64encode(hashlib.md5(content).digest()).decode("ascii")
        storage.put_object.side_effect = [
            SimpleNamespace(headers={"opc-content-md5": content_md5}),
            SimpleNamespace(headers={}),
        ]
        storage.get_object.side_effect = lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(content=content)
        )

        result = manager.save_review_record(record)

        self.assertEqual(result.to_dict(), record)
        self.assertEqual(storage.put_object.call_count, 2)
        final_call, mirror_call = storage.put_object.call_args_list
        self.assertEqual(final_call.kwargs["object_name"], "reviews/DOC-REVIEW/_final.json")
        self.assertEqual(mirror_call.kwargs["object_name"], "reviews/DOC-REVIEW/REV-001.json")
        self.assertEqual(final_call.kwargs["put_object_body"], content)
        self.assertEqual(mirror_call.kwargs["put_object_body"], content)
        self.assertEqual(final_call.kwargs["content_md5"], content_md5)
        self.assertEqual(mirror_call.kwargs["content_md5"], content_md5)
        self.assertEqual(final_call.kwargs["if_none_match"], "*")
        self.assertNotIn("if_none_match", mirror_call.kwargs)

    def test_save_review_record_412_does_not_write_mirror(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.put_object.side_effect = SDKError(412)

        with self.assertRaises(DuplicateReviewError):
            manager.save_review_record(self._valid_review())

        storage.put_object.assert_called_once()

    def test_save_review_record_maps_sdk_errors(self):
        for error, expected in (
            (SDKError(401), OCICredentialsError),
            (SDKError(403), OCIPermissionDeniedError),
            (ReadTimeout("timeout"), OCITimeoutError),
            (SDKError(503), OCIPersistenceError),
        ):
            storage = MagicMock()
            manager = OCIStorageManager(
                OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
                object_storage_client=storage,
            )
            storage.put_object.side_effect = error

            with self.subTest(expected=expected):
                with self.assertRaises(expected):
                    manager.save_review_record(self._valid_review())

    def test_save_review_record_rejects_incomplete_final_response(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.put_object.return_value = SimpleNamespace(headers={})

        with self.assertRaises(OCIIncompleteResponseError):
            manager.save_review_record(self._valid_review())

        storage.get_object.assert_not_called()

    def test_save_review_record_rejects_wrong_md5(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.put_object.return_value = SimpleNamespace(
            headers={"opc-content-md5": "wrong-md5"}
        )

        with self.assertRaises(OCIIncompleteResponseError):
            manager.save_review_record(self._valid_review())

        storage.get_object.assert_not_called()

    def test_save_review_record_rejects_mismatched_final_bytes(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        content = json.dumps(
            self._valid_review(), sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
        content_md5 = base64.b64encode(hashlib.md5(content).digest()).decode("ascii")
        storage.put_object.return_value = SimpleNamespace(
            headers={"opc-content-md5": content_md5}
        )
        storage.get_object.return_value = SimpleNamespace(
            data=SimpleNamespace(content=b"different")
        )

        with self.assertRaises(OCIIncompleteResponseError):
            manager.save_review_record(self._valid_review())

        storage.put_object.assert_called_once()

    def test_save_review_record_keeps_final_when_mirror_fails(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        content = json.dumps(
            self._valid_review(), sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
        content_md5 = base64.b64encode(hashlib.md5(content).digest()).decode("ascii")
        storage.put_object.side_effect = [
            SimpleNamespace(headers={"opc-content-md5": content_md5}),
            SDKError(503),
        ]
        storage.get_object.return_value = SimpleNamespace(
            data=SimpleNamespace(content=content)
        )

        with self.assertRaises(OCIPersistenceError):
            manager.save_review_record(self._valid_review())

        self.assertEqual(storage.put_object.call_count, 2)
        storage.delete_object.assert_not_called()
        self.assertEqual(
            storage.put_object.call_args_list[0].kwargs["object_name"],
            "reviews/DOC-REVIEW/_final.json",
        )

    def test_save_review_record_never_writes_outside_reviews(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )

        with self.assertRaises(ReviewValidationError):
            manager.save_review_record({**self._valid_review(), "documento_id": "../escape"})

        storage.put_object.assert_not_called()

    def test_save_review_record_does_not_modify_urgent_triage_object(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        content = json.dumps(
            self._valid_review(), sort_keys=True, ensure_ascii=False
        ).encode("utf-8")
        content_md5 = base64.b64encode(hashlib.md5(content).digest()).decode("ascii")
        storage.put_object.side_effect = [
            SimpleNamespace(headers={"opc-content-md5": content_md5}),
            SimpleNamespace(headers={}),
        ]
        storage.get_object.side_effect = lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(content=content)
        )
        urgent_key = "DOC-URGENTE.json"

        manager.save_review_record(self._valid_review())

        written_keys = [
            call.kwargs["object_name"] for call in storage.put_object.call_args_list
        ]
        self.assertNotIn(urgent_key, written_keys)
        storage.delete_object.assert_not_called()

    @staticmethod
    def _valid_review():
        return {
            "documento_id": "DOC-REVIEW",
            "review_id": "REV-001",
            "review_status": "aprobado",
            "reviewer_id": "auditor-1",
            "observacion": None,
            "reviewed_at": "2026-10-20T15:30:00Z",
        }

    def test_get_review_record_reads_and_validates_record(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        record = self._valid_review()
        storage.get_object.return_value = SimpleNamespace(
            data=SimpleNamespace(content=json.dumps(record).encode())
        )

        result = manager.get_review_record("DOC-REVIEW", "REV-001")

        self.assertEqual(result.to_dict(), record)
        self.assertEqual(
            storage.get_object.call_args.kwargs["object_name"],
            "reviews/DOC-REVIEW/REV-001.json",
        )

    def test_get_review_record_maps_404_to_not_found(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.get_object.side_effect = SDKError(404)

        with self.assertRaises(ReviewNotFoundError):
            manager.get_review_record("DOC-REVIEW", "REV-001")

    def test_list_reviews_for_document_orders_reviews_and_uses_final_fallback(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        older = {**self._valid_review(), "review_id": "REV-001",
                 "reviewed_at": "2026-10-20T10:00:00Z"}
        newer = {**self._valid_review(), "review_id": "REV-002",
                 "reviewed_at": "2026-10-20T12:00:00Z"}
        final_content = json.dumps(newer).encode()
        storage.list_objects.return_value = SimpleNamespace(
            data=SimpleNamespace(
                objects=[
                    SimpleNamespace(name="reviews/DOC-REVIEW/REV-002.json"),
                    SimpleNamespace(name="reviews/DOC-REVIEW/_final.json"),
                    SimpleNamespace(name="reviews/DOC-REVIEW/REV-001.json"),
                ],
                next_start_with=None,
            )
        )
        contents = {
            "reviews/DOC-REVIEW/_final.json": final_content,
            "reviews/DOC-REVIEW/REV-001.json": json.dumps(older).encode(),
            "reviews/DOC-REVIEW/REV-002.json": final_content,
        }
        storage.get_object.side_effect = lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(content=contents[kwargs["object_name"]])
        )

        result = manager.list_reviews_for_document("DOC-REVIEW")

        self.assertEqual([item.review_id for item in result], ["REV-001", "REV-002"])
        self.assertIn(
            "reviews/DOC-REVIEW/_final.json",
            [call.kwargs["object_name"] for call in storage.get_object.call_args_list],
        )

    def test_list_reviews_for_document_does_not_duplicate_final_and_mirror(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        record = self._valid_review()
        storage.list_objects.return_value = SimpleNamespace(
            data=SimpleNamespace(
                objects=[
                    SimpleNamespace(name="reviews/DOC-REVIEW/_final.json"),
                    SimpleNamespace(name="reviews/DOC-REVIEW/REV-001.json"),
                ],
                next_start_with=None,
            )
        )
        storage.get_object.return_value = SimpleNamespace(
            data=SimpleNamespace(content=json.dumps(record).encode())
        )

        result = manager.list_reviews_for_document("DOC-REVIEW")

        self.assertEqual([item.to_dict() for item in result], [record])
        self.assertEqual(storage.get_object.call_count, 2)

    def test_list_reviews_for_document_returns_final_when_only_final_is_listed(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        record = self._valid_review()
        storage.list_objects.return_value = SimpleNamespace(
            data=SimpleNamespace(
                objects=[
                    SimpleNamespace(name="reviews/DOC-REVIEW/_final.json"),
                ],
                next_start_with=None,
            )
        )
        storage.get_object.return_value = SimpleNamespace(
            data=SimpleNamespace(content=json.dumps(record).encode())
        )

        result = manager.list_reviews_for_document("DOC-REVIEW")

        self.assertEqual([item.to_dict() for item in result], [record])

    def test_list_reviews_for_document_returns_empty_without_final_or_mirrors(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.get_object.side_effect = SDKError(404)

        self.assertEqual(manager.list_reviews_for_document("DOC-REVIEW"), [])
        storage.list_objects.assert_not_called()

    def test_list_reviews_for_document_uses_final_when_mirror_is_missing(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        record = self._valid_review()
        storage.list_objects.return_value = SimpleNamespace(
            data=SimpleNamespace(
                objects=[SimpleNamespace(name="reviews/DOC-REVIEW/REV-001.json")],
                next_start_with=None,
            )
        )
        storage.get_object.side_effect = [
            SimpleNamespace(data=SimpleNamespace(content=json.dumps(record).encode())),
            SDKError(404),
        ]

        result = manager.list_reviews_for_document("DOC-REVIEW")

        self.assertEqual(result[0].to_dict(), record)
        self.assertEqual(storage.get_object.call_count, 2)

    def test_list_reviews_for_document_follows_pagination(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        record = self._valid_review()
        storage.list_objects.side_effect = [
            SimpleNamespace(
                data=SimpleNamespace(
                    objects=[SimpleNamespace(name="reviews/DOC-REVIEW/REV-001.json")],
                    next_start_with="NEXT",
                )
            ),
            SimpleNamespace(
                data=SimpleNamespace(
                    objects=[SimpleNamespace(name="reviews/DOC-REVIEW/REV-002.json")],
                    next_start_with=None,
                )
            ),
        ]
        second = {**record, "review_id": "REV-002"}
        contents = {
            "reviews/DOC-REVIEW/_final.json": json.dumps(record).encode(),
            "reviews/DOC-REVIEW/REV-001.json": json.dumps(record).encode(),
            "reviews/DOC-REVIEW/REV-002.json": json.dumps(second).encode(),
        }
        storage.get_object.side_effect = lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(content=contents[kwargs["object_name"]])
        )

        result = manager.list_reviews_for_document("DOC-REVIEW")

        self.assertEqual(len(result), 2)
        self.assertEqual(storage.list_objects.call_args_list[1].kwargs["start"], "NEXT")

    def test_get_latest_review_status_returns_three_states(self):
        for status in ("aprobado", "rechazado"):
            storage = MagicMock()
            manager = OCIStorageManager(
                OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
                object_storage_client=storage,
            )
            record = {
                **self._valid_review(),
                "review_status": status,
                "observacion": "Revisado" if status == "rechazado" else None,
            }
            storage.head_object.return_value = SimpleNamespace()
            storage.get_object.return_value = SimpleNamespace(
                data=SimpleNamespace(content=json.dumps(record).encode())
            )
            self.assertEqual(manager.get_latest_review_status("DOC-REVIEW"), status)

        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.head_object.side_effect = SDKError(404)
        self.assertEqual(manager.get_latest_review_status("DOC-REVIEW"), "pendiente")

    def test_get_latest_review_status_rejects_invalid_final_json(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.head_object.return_value = SimpleNamespace()
        storage.get_object.return_value = SimpleNamespace(
            data=SimpleNamespace(content=b'{"status": "auditoria_humana"}')
        )

        with self.assertRaises(ReviewValidationError):
            manager.get_latest_review_status("DOC-REVIEW")

    def test_list_pending_reviews_excludes_decided_and_preserves_triage_json(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        pending = {
            "documento_id": "DOC-PENDING",
            "status": "auditoria_humana",
            "clasificacion": {"nivel_prioridad": "Urgente"},
            "extra": ["preserve", {"nested": True}],
        }
        decided = {**pending, "documento_id": "DOC-DECIDED"}
        manager.listar_resultados_triage = MagicMock(return_value=[pending, decided])
        storage.head_object.side_effect = [SDKError(404), SimpleNamespace()]

        result = manager.list_pending_reviews()

        self.assertEqual(result, [pending])
        self.assertIs(result[0], pending)
        self.assertEqual(
            storage.head_object.call_args_list[0].kwargs["object_name"],
            "reviews/DOC-PENDING/_final.json",
        )

    def test_list_pending_reviews_maps_head_forbidden_and_timeout(self):
        document = {"documento_id": "DOC-PENDING", "status": "auditoria_humana"}
        for error, expected in (
            (SDKError(403), OCIPermissionDeniedError),
            (ReadTimeout("timeout"), OCITimeoutError),
        ):
            storage = MagicMock()
            manager = OCIStorageManager(
                OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
                object_storage_client=storage,
            )
            manager.listar_resultados_triage = MagicMock(return_value=[document])
            storage.head_object.side_effect = error

            with self.subTest(expected=expected):
                with self.assertRaises(expected):
                    manager.list_pending_reviews()

    def test_review_reads_map_403_and_timeout(self):
        for error, expected in (
            (SDKError(403), OCIPermissionDeniedError),
            (ReadTimeout("timeout"), OCITimeoutError),
        ):
            storage = MagicMock()
            manager = OCIStorageManager(
                OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
                object_storage_client=storage,
            )
            storage.get_object.side_effect = error
            with self.subTest(expected=expected):
                with self.assertRaises(expected):
                    manager.get_review_record("DOC-REVIEW", "REV-001")

    def test_list_reviews_for_document_reads_multiple_pages(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        first = self._valid_review()
        second = {**self._valid_review(), "review_id": "REV-002"}
        storage.list_objects.side_effect = [
            SimpleNamespace(
                data=SimpleNamespace(
                    objects=[SimpleNamespace(name="reviews/DOC-REVIEW/REV-001.json")],
                    next_start_with="NEXT",
                )
            ),
            SimpleNamespace(
                data=SimpleNamespace(
                    objects=[SimpleNamespace(name="reviews/DOC-REVIEW/REV-002.json")],
                    next_start_with=None,
                )
            ),
        ]
        contents = {
            "reviews/DOC-REVIEW/_final.json": json.dumps(first).encode(),
            "reviews/DOC-REVIEW/REV-001.json": json.dumps(first).encode(),
            "reviews/DOC-REVIEW/REV-002.json": json.dumps(second).encode(),
        }
        storage.get_object.side_effect = lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(content=contents[kwargs["object_name"]])
        )

        result = manager.list_reviews_for_document("DOC-REVIEW")

        self.assertEqual({item.review_id for item in result}, {"REV-001", "REV-002"})
        self.assertEqual(storage.list_objects.call_args_list[1].kwargs["start"], "NEXT")

    def test_listar_resultados_triage(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )

        def mock_list(namespace_name, bucket_name, **kwargs):
            mock_res = MagicMock()
            if bucket_name == "procesados":
                mock_res.data.objects = [MagicMock(name="DOC-1.json"), MagicMock(name="DOC-1.pdf")]
                mock_res.data.objects[0].name = "DOC-1.json"
                mock_res.data.objects[1].name = "DOC-1.pdf"
            elif bucket_name == "auditoria_humana":
                mock_res.data.objects = [MagicMock(name="DOC-2.json")]
                mock_res.data.objects[0].name = "DOC-2.json"
            else:
                mock_res.data.objects = []
            return mock_res

        def mock_get(namespace_name, bucket_name, object_name):
            mock_res = MagicMock()
            if object_name == "DOC-1.json":
                mock_res.data.content = b'{"documento_id": "DOC-1", "status": "procesado"}'
            elif object_name == "DOC-2.json":
                mock_res.data.content = b'{"documento_id": "DOC-2", "status": "auditoria_humana"}'
            return mock_res

        storage.list_objects.side_effect = mock_list
        storage.get_object.side_effect = mock_get

        docs = manager.listar_resultados_triage()
        self.assertEqual(len(docs), 2)
        ids = [d["documento_id"] for d in docs]
        self.assertIn("DOC-1", ids)
        self.assertIn("DOC-2", ids)

    def test_listar_resultados_triage_preserves_root_json_results(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.list_objects.return_value = SimpleNamespace(
            data=SimpleNamespace(
                objects=[
                    SimpleNamespace(name="DOC-1.json"),
                    SimpleNamespace(name="DOC-1.pdf"),
                    SimpleNamespace(name="DOC-2.json"),
                ],
                next_start_with=None,
            )
        )
        documents = {
            "DOC-1.json": {"documento_id": "DOC-1", "status": "procesado"},
            "DOC-2.json": {"documento_id": "DOC-2", "status": "procesado"},
        }
        storage.get_object.side_effect = lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(
                content=json.dumps(documents[kwargs["object_name"]]).encode()
            )
        )

        assert manager.listar_resultados_triage() == [
            documents["DOC-1.json"],
            documents["DOC-2.json"],
        ]
        assert [call.kwargs["object_name"] for call in storage.get_object.call_args_list] == [
            "DOC-1.json",
            "DOC-2.json",
        ]

    def test_listar_resultados_triage_ignores_review_objects_before_reading(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.list_objects.side_effect = [
            SimpleNamespace(
                data=SimpleNamespace(
                    objects=[
                        SimpleNamespace(name="DOC-1.json"),
                        SimpleNamespace(name="reviews/REV-1/_final.json"),
                    ],
                    next_start_with=None,
                )
            ),
            SimpleNamespace(
                data=SimpleNamespace(
                    objects=[
                        SimpleNamespace(name="DOC-1.json"),
                        SimpleNamespace(name="reviews/REV-1.json"),
                        SimpleNamespace(name="DOC-2.json"),
                    ],
                    next_start_with=None,
                )
            ),
            SimpleNamespace(
                data=SimpleNamespace(objects=[], next_start_with=None)
            ),
            SimpleNamespace(
                data=SimpleNamespace(objects=[], next_start_with=None)
            ),
        ]
        documents = {
            "DOC-1.json": {"documento_id": "DOC-1", "status": "procesado"},
            "DOC-2.json": {
                "documento_id": "DOC-2",
                "status": "auditoria_humana",
            },
        }
        storage.get_object.side_effect = lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(
                content=json.dumps(documents[kwargs["object_name"]]).encode()
            )
        )

        result = manager.listar_resultados_triage(status="auditoria_humana")

        assert result == [documents["DOC-2.json"]]
        assert [call.kwargs["object_name"] for call in storage.get_object.call_args_list] == [
            "DOC-1.json",
            "DOC-2.json",
        ]

    def test_listar_resultados_triage_preserves_pagination(self):
        storage = MagicMock()
        manager = OCIStorageManager(
            OCISettings.from_environment({"OCI_NAMESPACE": "demo"}),
            object_storage_client=storage,
        )
        storage.list_objects.side_effect = [
            SimpleNamespace(
                data=SimpleNamespace(
                    objects=[
                        SimpleNamespace(name="DOC-1.json"),
                        SimpleNamespace(name="reviews/REV-1/_final.json"),
                    ],
                    next_start_with="NEXT",
                )
            ),
            SimpleNamespace(
                data=SimpleNamespace(
                    objects=[SimpleNamespace(name="DOC-2.json")],
                    next_start_with=None,
                )
            ),
            SimpleNamespace(
                data=SimpleNamespace(objects=[], next_start_with=None)
            ),
            SimpleNamespace(
                data=SimpleNamespace(objects=[], next_start_with=None)
            ),
        ]
        documents = {
            "DOC-1.json": {"documento_id": "DOC-1", "status": "procesado"},
            "DOC-2.json": {"documento_id": "DOC-2", "status": "procesado"},
        }
        storage.get_object.side_effect = lambda **kwargs: SimpleNamespace(
            data=SimpleNamespace(
                content=json.dumps(documents[kwargs["object_name"]]).encode()
            )
        )

        assert manager.listar_resultados_triage() == [
            documents["DOC-1.json"],
            documents["DOC-2.json"],
        ]
        assert storage.list_objects.call_args_list[1].kwargs["start"] == "NEXT"
        assert [call.kwargs["object_name"] for call in storage.get_object.call_args_list] == [
            "DOC-1.json",
            "DOC-2.json",
        ]
