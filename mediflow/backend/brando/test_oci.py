"""Prueba de integración autocontenida del simulador OCI.

Uso directo desde la raíz del repositorio:
    python mediflow/backend/brando/test_oci.py
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

try:
    from .oci_simulator import (
        OCIConfigurationError,
        OCIConnectionError,
        OCIInputError,
        OCIUploadAdapter,
        StubOCIClient,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from oci_simulator import (  # type: ignore[no-redef]
        OCIConfigurationError,
        OCIConnectionError,
        OCIInputError,
        OCIUploadAdapter,
        StubOCIClient,
    )


class OCIIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "documento.txt"
        self.file_path.write_text("archivo de prueba", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_subida_exitosa(self) -> None:
        client = StubOCIClient()
        result = OCIUploadAdapter(client, "namespace-demo").upload_file(
            self.file_path, "documentos", "documento.txt"
        )
        self.assertEqual(result["object"], "documento.txt")
        self.assertEqual(len(client.uploads), 1)

    def test_controla_error_de_red(self) -> None:
        adapter = OCIUploadAdapter(StubOCIClient("network"), "namespace-demo")
        with self.assertRaises(OCIConnectionError):
            adapter.upload_file(self.file_path, "documentos", "documento.txt")

    def test_controla_error_de_configuracion(self) -> None:
        adapter = OCIUploadAdapter(StubOCIClient("configuration"), "namespace-demo")
        with self.assertRaises(OCIConfigurationError):
            adapter.upload_file(self.file_path, "documentos", "documento.txt")

    def test_controla_archivo_invalido(self) -> None:
        adapter = OCIUploadAdapter(StubOCIClient(), "namespace-demo")
        with self.assertRaises(OCIInputError):
            adapter.upload_file(Path(self.temp_dir.name) / "ausente.txt", "documentos", "x.txt")

    def test_controla_entrada_invalida(self) -> None:
        adapter = OCIUploadAdapter(StubOCIClient(), "namespace-demo")
        with self.assertRaises(OCIInputError):
            adapter.upload_file(self.file_path, "", "documento.txt")


if __name__ == "__main__":
    print("Prueba autocontenida de subida a OCI con stub propio")
    result = unittest.main(verbosity=2, exit=False)
    print("Resultado general: OK" if result.result.wasSuccessful() else "Resultado general: FALLÓ")
    raise SystemExit(0 if result.result.wasSuccessful() else 1)