"""Agregado por Edil: errores y paginación auditados; OCI y Gemini simulados."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from oci.exceptions import ServiceError

from app.main import app
from app.core.oci_client import OCISettings, OCIStorageManager
from test_documents_api import mock_clinical_doc


def manager_with(storage):
    return OCIStorageManager(OCISettings.from_environment({"OCI_NAMESPACE": "synthetic"}),
                             object_storage_client=storage)


@pytest.mark.parametrize("analyze", [False, True])
def test_persistence_failure_never_reports_success(analyze, caplog):
    with patch("app.api.routes.OCIStorageManager") as factory, \
         patch("app.api.routes.analyze_received_document") as llm:
        manager = factory.return_value
        manager.settings.bucket_recibidos = "recibidos"
        # Agregado por Edil: la copia termina antes de probar el fallo JSON final.
        manager.determinar_bucket_por_estado.return_value = "procesados"
        manager.subir_a_recibidos.side_effect = lambda body, name: name
        # Agregado por Edil: recepción exitosa y fallo final si hubo análisis.
        manager.guardar_resultado_triage.side_effect = [None, PermissionError("private-secret")] if analyze else PermissionError("private-secret")
        llm.side_effect = lambda content, filename, document_id, storage: mock_clinical_doc(document_id, "procesado")
        with TestClient(app) as http:
            response = http.post("/api/triage", data={"analyze": str(analyze).lower()},
                                 files={"file": ("synthetic.txt", b"contenido sintetico")})
        assert response.status_code == 503
        assert response.headers["X-Document-ID"].startswith("DOC-CLIN-")
        assert "JSON" in response.json()["detail"]
        assert "private-secret" not in response.text + caplog.text
        assert "contenido sintetico" not in caplog.text
        manager.object_storage.delete_object.assert_not_called()
        assert llm.call_count == int(analyze)
        assert manager.guardar_resultado_triage.call_count == (2 if analyze else 1)


def test_access_denied_is_error_not_empty_or_not_found():
    storage = MagicMock()
    storage.get_object.side_effect = ServiceError(403, "NotAuthorized", {}, "private")
    storage.list_objects.side_effect = ServiceError(403, "NotAuthorized", {}, "private")
    with patch("app.api.routes.OCIStorageManager", return_value=manager_with(storage)):
        with TestClient(app) as http:
            detail = http.get("/api/documents/DOC-SYNTHETIC")
            listing = http.get("/api/documents")
    assert detail.status_code == listing.status_code == 500
    assert "private" not in detail.text + listing.text


def test_absent_object_can_continue_search_in_other_buckets():
    storage = MagicMock()
    storage.get_object.side_effect = ServiceError(404, "ObjectNotFound", {}, "synthetic")
    with patch("app.api.routes.OCIStorageManager", return_value=manager_with(storage)):
        with TestClient(app) as http:
            response = http.get("/api/documents/DOC-SYNTHETIC")
    assert response.status_code == 404
    assert storage.get_object.call_count == 3


def test_corrupt_json_is_not_reported_as_missing():
    storage = MagicMock()
    storage.get_object.return_value = SimpleNamespace(data=SimpleNamespace(content=b"not JSON"))
    with patch("app.api.routes.OCIStorageManager", return_value=manager_with(storage)):
        with TestClient(app) as http:
            response = http.get("/api/documents/DOC-SYNTHETIC")
    assert response.status_code == 502


def test_list_objects_follows_all_pages():
    storage = MagicMock()
    storage.list_objects.side_effect = [
        SimpleNamespace(data=SimpleNamespace(objects=[SimpleNamespace(name="DOC-1.json")], next_start_with="NEXT")),
        SimpleNamespace(data=SimpleNamespace(objects=[SimpleNamespace(name="DOC-2.json")], next_start_with=None)),
    ]
    assert manager_with(storage).listar_objetos("procesados") == ["DOC-1.json", "DOC-2.json"]
    assert storage.list_objects.call_args_list[1].kwargs["start"] == "NEXT"


def test_repeated_page_marker_fails_instead_of_looping_forever():
    storage = MagicMock()
    storage.list_objects.return_value = SimpleNamespace(data=SimpleNamespace(objects=[], next_start_with="SAME"))
    with pytest.raises(RuntimeError, match="paginación"):
        manager_with(storage).listar_objetos("procesados")


def test_priority_filter_precedes_limit_with_actual_manager():
    storage = MagicMock()
    storage.list_objects.return_value = SimpleNamespace(data=SimpleNamespace(
        objects=[SimpleNamespace(name="DOC-1.json"), SimpleNamespace(name="DOC-2.json")], next_start_with=None))
    docs = {
        "DOC-1.json": mock_clinical_doc("DOC-1", "procesado", "Rutina"),
        "DOC-2.json": mock_clinical_doc("DOC-2", "procesado", "Urgente"),
    }
    storage.get_object.side_effect = lambda **kw: SimpleNamespace(data=SimpleNamespace(
        content=json.dumps(docs[kw["object_name"]]).encode()))
    with patch("app.api.routes.OCIStorageManager", return_value=manager_with(storage)):
        with TestClient(app) as http:
            response = http.get("/api/documents?status=procesado&prioridad=Urgente&limit=1")
    assert response.status_code == 200
    assert [doc["documento_id"] for doc in response.json()] == ["DOC-2"]


def test_id_mismatch_in_stored_payload_is_rejected():
    with patch("app.api.routes.OCIStorageManager") as factory:
        factory.return_value.recuperar_resultado_triage.return_value = mock_clinical_doc("OTHER", "procesado")
        with TestClient(app) as http:
            response = http.get("/api/documents/DOC-REQUESTED")
    assert response.status_code == 502


@pytest.mark.parametrize("status", ["unknown", "", None])
def test_unknown_state_is_not_silently_written_to_received(status):
    storage = MagicMock()
    with pytest.raises(ValueError):
        manager_with(storage).guardar_resultado_triage({"documento_id": "DOC-1", "status": status})
    storage.put_object.assert_not_called()


def test_document_id_cannot_create_an_arbitrary_json_path():
    storage = MagicMock()
    with pytest.raises(ValueError):
        manager_with(storage).guardar_resultado_triage({"documento_id": "../private", "status": "recibido"})
    storage.put_object.assert_not_called()


# Agregado por Edil: regresiones encontradas al probar un fallo real de Gemini.
def test_failed_llm_keeps_received_json_available(caplog):
    from app.services.llm_errors import LLMUnavailableError
    events = []
    with patch("app.api.routes.OCIStorageManager") as factory, patch("app.api.routes.analyze_received_document") as llm:
        manager = factory.return_value
        manager.settings.bucket_recibidos = "recibidos"
        manager.subir_a_recibidos.side_effect = lambda body, name: name
        manager.guardar_resultado_triage.side_effect = lambda payload: events.append(payload["status"])
        def fail(*args):
            events.append("gemini")
            raise LLMUnavailableError("private")
        llm.side_effect = fail
        with TestClient(app) as http:
            response = http.post("/api/triage", data={"analyze":"true"}, files={"file":("synthetic.txt",b"synthetic")})
        assert response.status_code == 503
        assert events == ["recibido", "gemini"]
        assert manager.guardar_resultado_triage.call_args.args[0]["documento_id"] == response.headers["X-Document-ID"]


def test_received_filter_does_not_return_old_completed_receipt():
    storage = MagicMock()
    def listing(**kwargs):
        names = [SimpleNamespace(name="DOC-1.json")] if kwargs["bucket_name"] in {"procesados","recibidos"} else []
        return SimpleNamespace(data=SimpleNamespace(objects=names,next_start_with=None))
    storage.list_objects.side_effect = listing
    storage.get_object.side_effect = lambda **kw: SimpleNamespace(data=SimpleNamespace(content=json.dumps(
        mock_clinical_doc("DOC-1", "procesado" if kw["bucket_name"]=="procesados" else "recibido")).encode()))
    manager = manager_with(storage)
    assert manager.listar_resultados_triage(status="recibido") == []
    assert len(manager.listar_resultados_triage()) == 1
