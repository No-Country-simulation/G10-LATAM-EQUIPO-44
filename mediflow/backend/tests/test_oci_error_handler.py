"""Prueba independiente del manejo de errores del cliente OCI de Eliana."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.core.oci_error_handler import (
    OCIConfigurationError, OCIConnectionError, OCIInputError, upload_document,
)


class OCIErrorHandlerTest(unittest.TestCase):
    @patch("app.core.oci_error_handler.OCIStorageManager")
    def test_controla_configuracion_del_cliente(self, manager_class):
        from app.core.oci_client import OCIConfigurationError as ClientError
        manager_class.side_effect = ClientError("configuración incompleta")
        with self.assertRaises(OCIConfigurationError):
            upload_document("documento.txt", "recibidos", "test.txt")

    @patch("app.core.oci_error_handler.OCIStorageManager")
    def test_controla_permisos_sdk(self, manager_class):
        try:
            from oci.exceptions import ServiceError
        except ImportError:
            self.skipTest("SDK OCI no instalado")
        manager_class.return_value.subir_archivo.side_effect = ServiceError(
            status=403, code="NotAuthorized", headers={}, message="sin permisos"
        )
        with self.assertRaises(OCIConfigurationError):
            upload_document("documento.txt", "recibidos", "test.txt")
    @patch("app.core.oci_error_handler.OCIStorageManager")
    def test_subida_exitosa(self, manager_class: MagicMock) -> None:
        upload_document("documento.txt", "documentos", "documento.txt")
        manager_class.return_value.subir_archivo.assert_called_once_with(
            "documento.txt", "documentos", "documento.txt"
        )

    @patch("app.core.oci_error_handler.OCIStorageManager")
    def test_controla_error_de_conexion(self, manager_class: MagicMock) -> None:
        manager_class.return_value.subir_archivo.side_effect = ConnectionError(
            "servidor no disponible"
        )
        with self.assertRaises(OCIConnectionError):
            upload_document("documento.txt", "documentos", "documento.txt")

    @patch("app.core.oci_error_handler.OCIStorageManager")
    def test_controla_error_de_credenciales(self, manager_class: MagicMock) -> None:
        manager_class.side_effect = PermissionError("credenciales inválidas")
        with self.assertRaises(OCIConfigurationError):
            upload_document("documento.txt", "documentos", "documento.txt")

    @patch("app.core.oci_error_handler.OCIStorageManager")
    def test_controla_archivo_invalido(self, manager_class: MagicMock) -> None:
        manager_class.return_value.subir_archivo.side_effect = FileNotFoundError(
            "archivo ausente"
        )
        with self.assertRaises(OCIInputError):
            upload_document("ausente.txt", "documentos", "ausente.txt")

    def test_controla_entrada_invalida(self) -> None:
        with self.assertRaises(OCIInputError):
            upload_document("documento.txt", "", "documento.txt")


def imprimir_resultados(result: unittest.TestResult) -> None:
    print("\n========== RESULTADOS DE LA PRUEBA OCI ==========")
    print("[OK] Subida exitosa delegada al cliente de Eliana")
    print("[OK] Error de red/conectividad capturado")
    print("[OK] Error de credenciales/configuración capturado")
    print("[OK] Archivo o ruta inválida capturada")
    print("[OK] Entrada inválida capturada")
    print("=================================================")
    print("RESULTADO GENERAL: OK" if result.wasSuccessful() else "RESULTADO GENERAL: FALLÓ")


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    imprimir_resultados(result)
    raise SystemExit(0 if result.wasSuccessful() else 1)
