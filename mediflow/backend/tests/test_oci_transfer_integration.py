"""Prueba OCI real optativa; nunca utiliza un objeto existente del equipo."""

import os
import uuid

import pytest

from app.core.environment import load_environment
from app.core.oci_client import OCIStorageManager


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("RUN_OCI_INTEGRATION") != "1",
                    reason="OCI real desactivado: requiere RUN_OCI_INTEGRATION=1")
def test_real_copy_of_own_synthetic_object():
    # Agregado por Edil: antes se movía un objeto elegido por variable y se
    # eliminaba su origen. Ahora crear únicamente nuestra muestra sintética,
    # copiarla sin borrar el original y limpiar solo esta muestra al terminar.
    load_environment()
    manager = OCIStorageManager()
    name = f"mediflow-transfer-test-{uuid.uuid4().hex}.txt"
    content = b"Synthetic software integration test. No clinical data."
    source = manager.settings.bucket_recibidos
    destination = manager.settings.bucket_procesados
    source_created = False
    try:
        manager.object_storage.put_object(
            namespace_name=manager.namespace, bucket_name=source,
            object_name=name, put_object_body=content, if_none_match="*"
        )
        source_created = True
        result = manager.copiar_archivo(name, source, destination)
        assert result.object_name == name
        assert result.source_size == result.destination_size == len(content)
        assert manager.obtener_objeto_bytes(source, name) == content
        assert manager.obtener_objeto_bytes(destination, name) == content
    finally:
        if source_created:
            # Agregado por Edil: la limpieza nunca recibe nombres del entorno.
            # Verificar contenido y versión evita eliminar un objeto ajeno.
            for bucket in (destination, source):
                try:
                    head = manager.object_storage.head_object(
                        namespace_name=manager.namespace, bucket_name=bucket,
                        object_name=name,
                    )
                except Exception as error:
                    if getattr(error, "status", None) == 404:
                        continue
                    raise
                if manager.obtener_objeto_bytes(bucket, name) == content:
                    manager.object_storage.delete_object(
                        namespace_name=manager.namespace, bucket_name=bucket,
                        object_name=name, if_match=head.headers["etag"],
                    )


# Agregado por Edil: prueba original conservada, desactivada por seguridad.
# import os
#
# import pytest
# import oci
#
# from app.core.config import settings
# from app.core.oci_transfer import OCIObjectMover
#
# def test_real_move_of_explicit_test_object():
#     """Move only an object explicitly prepared for this experiment."""
#     if os.getenv("OCI_RUN_INTEGRATION") != "1":
#         pytest.skip("Defina OCI_RUN_INTEGRATION=1 para habilitar OCI real.")
#     object_name = os.getenv("OCI_TEST_OBJECT_NAME")
#     if not object_name:
#         pytest.skip("Defina OCI_TEST_OBJECT_NAME con el objeto de prueba.")
#     config = settings.get_oci_config_dict() or oci.config.from_file()
#     client = oci.object_storage.ObjectStorageClient(config)
#     namespace = settings.OCI_NAMESPACE or client.get_namespace().data
#     mover = OCIObjectMover(client, namespace, config["region"])
#
#     result = mover.move(
#         object_name,
#         settings.OCI_BUCKET_RECIBIDOS,
#         settings.OCI_BUCKET_PROCESADOS,
#     )
#
#     assert result.object_name == object_name
#     assert result.source_size == result.destination_size
