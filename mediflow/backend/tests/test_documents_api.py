"""Pruebas de los endpoints GET /api/documents y GET /api/documents/{id} (Sprint 3 - Drazen Gamboa)."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import TriageResponse


def mock_clinical_doc(doc_id: str, status_val: str, priority_val: str = "Rutina"):
    return {
        "status": status_val,
        "documento_id": doc_id,
        "clasificacion": {
            "tipo_documento": "Receta médica" if status_val == "procesado" else "Pendiente de procesamiento",
            "especialidad": "General",
            "nivel_prioridad": priority_val,
            "score_confianza_clasificacion": 0.85 if status_val != "recibido" else 0.0,
        },
        "datos_extraidos": {
            "paciente": {"nombre": "Juan Pérez", "edad": 45},
            "medico_solicitante": {"nombre": "Dra. García", "matricula": "MN-12345"},
            "estudio_realizado": None,
            "diagnostico_principal": "Faringitis aguda",
            "cie10_sugerido": "J02.9",
            "medicamentos_recetados": [{"medicamento": "Amoxicilina", "dosis": "500mg cada 8hs"}],
        },
        "decision_enrutamiento": {
            "destino_principal": "Cola_Revision_Humana" if status_val == "auditoria_humana" else "Cola_Farmacia",
            "requiere_auditoria_humana": status_val == "auditoria_humana",
            "justificacion_enrutamiento": "Caso de prueba automatizado.",
        },
        "notificacion_generada": None,
        "almacenamiento_oci": {
            "bucket": "procesados" if status_val == "procesado" else "recibidos",
            "ruta_objeto": f"{doc_id}.pdf",
            "status_backup": "exito",
        },
    }


def test_get_documents_empty_list():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.listar_resultados_triage.return_value = []
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/documents")

        assert response.status_code == 200
        assert response.json() == []
        manager.listar_resultados_triage.assert_called_once_with(status=None, limit=100)


def test_get_documents_with_items():
    docs = [
        mock_clinical_doc("DOC-001", "recibido", "Rutina"),
        mock_clinical_doc("DOC-002", "procesado", "Rutina"),
        mock_clinical_doc("DOC-003", "procesado", "Urgente"),
        mock_clinical_doc("DOC-004", "auditoria_humana", "Urgente"),
    ]
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.listar_resultados_triage.return_value = docs
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/documents")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        # Cada documento debe validar contra TriageResponse
        for item in data:
            TriageResponse.model_validate(item)


def test_get_documents_filter_status_and_priority():
    docs = [
        mock_clinical_doc("DOC-002", "procesado", "Rutina"),
        mock_clinical_doc("DOC-003", "procesado", "Urgente"),
    ]
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.listar_resultados_triage.return_value = docs
        factory.return_value = manager

        with TestClient(app) as client:
            # Filtro por status y prioridad
            response = client.get("/api/documents?status=procesado&prioridad=Urgente")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["documento_id"] == "DOC-003"
        assert data[0]["clasificacion"]["nivel_prioridad"] == "Urgente"


def test_get_documents_oci_error_handled():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.listar_resultados_triage.side_effect = RuntimeError("Conexión perdida con OCI")
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/documents")

        assert response.status_code == 500
        assert "No se pudieron recuperar los documentos de OCI" in response.json()["detail"]


def test_get_document_by_id_success():
    doc = mock_clinical_doc("DOC-CLIN-001", "procesado", "Urgente")
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = doc
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/documents/DOC-CLIN-001")

        assert response.status_code == 200
        data = response.json()
        assert data["documento_id"] == "DOC-CLIN-001"
        assert data["status"] == "procesado"
        assert data["clasificacion"]["nivel_prioridad"] == "Urgente"
        manager.recuperar_resultado_triage.assert_called_once_with("DOC-CLIN-001")


def test_get_document_by_id_not_found():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = None
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/documents/DOC-NOEXISTE")

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]


def test_get_document_by_id_invalid_characters():
    with TestClient(app) as client:
        response = client.get("/api/documents/DOC..123")
        assert response.status_code == 400
        assert "inválido" in response.json()["detail"]


def test_get_document_by_id_invalid_schema_in_storage():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        # Devuelve un dict corrupto sin campos obligatorios
        manager.recuperar_resultado_triage.return_value = {"invalido": True}
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/documents/DOC-CORRUPTO")

        assert response.status_code == 502
        assert "no cumple el contrato oficial" in response.json()["detail"]


def test_post_triage_persists_initial_json():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.settings.bucket_recibidos = "recibidos"
        manager.subir_a_recibidos.side_effect = lambda body, name: name
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.post("/api/triage", files={"file": ("test.pdf", b"%PDF-demo")})

        assert response.status_code == 201
        manager.guardar_resultado_triage.assert_called_once()
        saved_arg = manager.guardar_resultado_triage.call_args.args[0]
        assert saved_arg["status"] == "recibido"
        assert saved_arg["documento_id"].startswith("DOC-CLIN-")


def test_openapi_swagger_registration():
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        paths = schema.get("paths", {})
        assert "/api/documents" in paths
        assert "get" in paths["/api/documents"]
        assert "/api/documents/{document_id}" in paths
        assert "get" in paths["/api/documents/{document_id}"]
