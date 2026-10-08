"""Prueba OCI real: requiere autorización explícita mediante RUN_OCI_INTEGRATION."""

import os
from dataclasses import replace
from uuid import uuid4

import pytest

from app.core.oci_client import OCISettings, OCIStorageManager


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("RUN_OCI_INTEGRATION") != "1",
    reason="OCI real desactivado; habilitar RUN_OCI_INTEGRATION=1 explícitamente",
)
def test_upload_download_recibidos(tmp_path):
    # Fuerza autenticación por perfil local. Nunca imprime ni copia credenciales.
    settings = replace(
        OCISettings.from_environment(),
        user_ocid=None, fingerprint=None, key_file=None, tenancy_ocid=None, region=None,
    )
    manager = OCIStorageManager(settings)
    object_name = settings.prefix_recibidos + f"sprint1-integration-{uuid4().hex}.txt"
    original = b"MediFlow Sprint 1 - OCI integration test"
    uploaded = False
    try:
        manager.subir_archivo_desde_memoria(original, settings.bucket_name, object_name)
        uploaded = True
        destination = manager.descargar_archivo(
            settings.bucket_name, object_name, tmp_path / "download.txt"
        )
        assert destination.read_bytes() == original, "El contenido descargado no coincide"
        print(f"OK upload/download: {settings.bucket_name}/{object_name}")
    finally:
        if uploaded:
            # Solo se elimina el objeto único creado en esta ejecución.
            manager.object_storage.delete_object(
                namespace_name=manager.namespace,
                bucket_name=settings.bucket_name,
                object_name=object_name,
            )
            print("OK: objeto de prueba eliminado")
