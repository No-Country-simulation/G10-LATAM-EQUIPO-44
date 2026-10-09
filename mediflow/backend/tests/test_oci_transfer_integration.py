import os

import pytest
import oci

from app.core.config import settings
from app.core.oci_transfer import OCIObjectMover

def test_real_move_of_explicit_test_object():
    """Move only an object explicitly prepared for this experiment."""
    if os.getenv("OCI_RUN_INTEGRATION") != "1":
        pytest.skip("Defina OCI_RUN_INTEGRATION=1 para habilitar OCI real.")
    object_name = os.getenv("OCI_TEST_OBJECT_NAME")
    if not object_name:
        pytest.skip("Defina OCI_TEST_OBJECT_NAME con el objeto de prueba.")
    config = settings.get_oci_config_dict() or oci.config.from_file()
    client = oci.object_storage.ObjectStorageClient(config)
    namespace = settings.OCI_NAMESPACE or client.get_namespace().data
    mover = OCIObjectMover(client, namespace, config["region"])

    result = mover.move(
        object_name,
        settings.OCI_BUCKET_RECIBIDOS,
        settings.OCI_BUCKET_PROCESADOS,
    )

    assert result.object_name == object_name
    assert result.source_size == result.destination_size
