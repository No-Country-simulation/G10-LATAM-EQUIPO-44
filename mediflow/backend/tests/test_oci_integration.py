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
    object_name = f"sprint1-integration-{uuid4().hex}.txt"
    original = b"MediFlow Sprint 1 - OCI integration test"
    uploaded = False
    try:
        manager.subir_archivo_desde_memoria(original, settings.bucket_recibidos, object_name)
        uploaded = True
        destination = manager.descargar_archivo(
            settings.bucket_recibidos, object_name, tmp_path / "download.txt"
        )
        assert destination.read_bytes() == original, "El contenido descargado no coincide"
        print(f"OK upload/download: {settings.bucket_recibidos}/{object_name}")
    finally:
        if uploaded:
            # Solo se elimina el objeto único creado en esta ejecución.
            manager.object_storage.delete_object(
                namespace_name=manager.namespace,
                bucket_name=settings.bucket_recibidos,
                object_name=object_name,
            )
            print("OK: objeto de prueba eliminado")


@pytest.mark.integration
@pytest.mark.skipif(os.environ.get("RUN_OCI_INTEGRATION") != "1", reason="OCI real desactivado")
@pytest.mark.parametrize("state", ["recibido", "procesado", "auditoria_humana"])
def test_json_roundtrip_three_buckets(state):
    """Agregado por Edil: JSON sintético, no resultado clínico ni llamada a Gemini."""
    from app.core.environment import load_environment
    from app.models.schemas import TriageResponse

    load_environment()
    manager = OCIStorageManager()
    doc_id = f"DOC-INTEGRATION-{uuid4().hex.upper()}"
    bucket = manager.determinar_bucket_por_estado(state)
    object_name = f"{doc_id}.json"
    payload = TriageResponse.model_validate({
        "status": state,
        "documento_id": doc_id,
        "clasificacion": {"tipo_documento": "Registro sintetico de prueba OCI", "nivel_prioridad": "Rutina"},
        "datos_extraidos": {},
        "decision_enrutamiento": {
            "requiere_auditoria_humana": state == "auditoria_humana",
            "destino_principal": "Cola_Revision_Humana" if state == "auditoria_humana" else "Cola_Historia_Clinica",
            "justificacion_enrutamiento": "Datos artificiales para comprobar escritura y lectura JSON, sin analisis clinico.",
        },
        "almacenamiento_oci": {"bucket": bucket, "ruta_objeto": object_name, "status_backup": "exito"},
    }).model_dump()
    uploaded = False
    try:
        manager.guardar_resultado_triage(payload)
        uploaded = True
        assert manager.recuperar_json(bucket, object_name) == payload
        assert manager.recuperar_resultado_triage(doc_id) == payload
        print(f"OK JSON escritura/lectura: {bucket}/{object_name}")
    finally:
        if uploaded:
            # Agregado por Edil: limpiar exclusivamente el JSON único creado aquí.
            # No eliminar documentos originales ni otros objetos del bucket.
            manager.object_storage.delete_object(namespace_name=manager.namespace,
                bucket_name=bucket, object_name=object_name)
