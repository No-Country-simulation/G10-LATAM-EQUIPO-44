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
