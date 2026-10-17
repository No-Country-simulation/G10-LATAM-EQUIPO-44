"""Pruebas locales del cliente OCI; no contactan servicios de Oracle."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core.oci_client import OCISettings, OCIStorageManager


class FakeObjectStorage:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def put_object(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


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
