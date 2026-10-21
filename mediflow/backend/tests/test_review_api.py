"""Pruebas exhaustivas de los endpoints HTTP de revisión humana (Sprint 4 - Drazen Gamboa / S4-01).

Endpoints probados:
- GET /api/reviews/pending
- POST /api/documents/{document_id}/review
- GET /api/documents/{document_id}/review-history
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.error_handler import (
    DuplicateReviewError,
    OCIPersistenceError,
    OCITimeoutError,
    ReviewValidationError,
)
from app.core.oci_client import ReviewRecord


def mock_triage_doc(doc_id: str, status_val: str = "auditoria_humana", requires_human: bool = True):
    return {
        "status": status_val,
        "documento_id": doc_id,
        "clasificacion": {
            "tipo_documento": "Epicrisis clínica",
            "especialidad": "Cardiología",
            "nivel_prioridad": "Urgente",
            "score_confianza_clasificacion": 0.65,
        },
        "datos_extraidos": {
            "paciente": {"nombre": "María Rodríguez", "edad": 58},
            "medico_solicitante": {"nombre": "Dr. Benítez", "matricula": "MN-98765"},
            "estudio_realizado": "Ecocardiograma",
            "diagnostico_principal": "Insuficiencia cardíaca descompensada",
            "cie10_sugerido": "I50.9",
            "medicamentos_recetados": [{"medicamento": "Furosemida", "dosis": "40mg"}],
        },
        "decision_enrutamiento": {
            "destino_principal": "Cola_Revision_Humana",
            "requiere_auditoria_humana": requires_human,
            "justificacion_enrutamiento": "Score de confianza bajo (0.65) en caso urgente.",
        },
        "notificacion_generada": None,
        "almacenamiento_oci": {
            "bucket": "auditoria_humana",
            "ruta_objeto": f"{doc_id}.pdf",
            "status_backup": "exito",
        },
    }


# ==============================================================================
# TESTS GET /api/reviews/pending
# ==============================================================================

def test_get_pending_reviews_empty():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.list_pending_reviews.return_value = []
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/reviews/pending")

        assert response.status_code == 200
        assert response.json() == []
        manager.list_pending_reviews.assert_called_once()


def test_get_pending_reviews_with_items():
    pending_items = [
        mock_triage_doc("DOC-PEND-001"),
        mock_triage_doc("DOC-PEND-002"),
    ]
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.list_pending_reviews.return_value = pending_items
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/reviews/pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["documento_id"] == "DOC-PEND-001"
        assert data[1]["documento_id"] == "DOC-PEND-002"


def test_get_pending_reviews_oci_timeout_returns_504():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.list_pending_reviews.side_effect = OCITimeoutError("OCI timed out")
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/reviews/pending")

        assert response.status_code == 504
        assert "tiempo de espera" in response.json()["detail"].lower()


def test_get_pending_reviews_oci_error_returns_502():
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.list_pending_reviews.side_effect = OCIPersistenceError("OCI failure")
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get("/api/reviews/pending")

        assert response.status_code == 502
        assert "completar la operación" in response.json()["detail"].lower()


# ==============================================================================
# TESTS POST /api/documents/{id}/review
# ==============================================================================

def test_post_review_approved_success():
    doc_id = "DOC-CLIN-100"
    triage_doc = mock_triage_doc(doc_id)

    mock_saved_record = ReviewRecord(
        documento_id=doc_id,
        review_id="REV-20261021T120000Z-a1b2c3d4",
        review_status="aprobado",
        reviewer_id="auditor_drazen",
        observacion="Todo correcto tras auditoría médica.",
        reviewed_at="2026-10-21T12:00:00Z",
    )

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        manager.get_latest_review_status.return_value = "pendiente"
        manager.save_review_record.return_value = mock_saved_record
        factory.return_value = manager

        payload = {
            "decision": "aprobado",
            "reviewer_id": "auditor_drazen",
            "observacion": "Todo correcto tras auditoría médica.",
            "expected_review_status": "pendiente",
        }

        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["documento_id"] == doc_id
        assert data["review_status"] == "aprobado"
        assert data["reviewer_id"] == "auditor_drazen"
        assert data["observacion"] == "Todo correcto tras auditoría médica."
        assert data["review_id"] == "REV-20261021T120000Z-a1b2c3d4"
        assert data["reviewed_at"] == "2026-10-21T12:00:00Z"

        # Verificar que el payload a OCI tuvo exactamente los 6 campos requeridos por Brando
        manager.save_review_record.assert_called_once()
        record_sent = manager.save_review_record.call_args[0][0]
        assert set(record_sent.keys()) == {
            "documento_id", "review_id", "review_status", "reviewer_id", "observacion", "reviewed_at"
        }
        assert record_sent["review_status"] == "aprobado"


def test_post_review_approved_without_observation_success():
    doc_id = "DOC-CLIN-101"
    triage_doc = mock_triage_doc(doc_id)

    mock_saved_record = ReviewRecord(
        documento_id=doc_id,
        review_id="REV-20261021T120000Z-11223344",
        review_status="aprobado",
        reviewer_id="auditor_drazen",
        observacion=None,
        reviewed_at="2026-10-21T12:00:00Z",
    )

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        manager.get_latest_review_status.return_value = "pendiente"
        manager.save_review_record.return_value = mock_saved_record
        factory.return_value = manager

        payload = {
            "decision": "aprobado",
            "reviewer_id": "auditor_drazen",
            "observacion": None,
            "expected_review_status": "pendiente",
        }

        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 200
        assert response.json()["observacion"] is None


def test_post_review_rejected_with_observation_success():
    doc_id = "DOC-CLIN-102"
    triage_doc = mock_triage_doc(doc_id)

    mock_saved_record = ReviewRecord(
        documento_id=doc_id,
        review_id="REV-20261021T120000Z-99887766",
        review_status="rechazado",
        reviewer_id="auditor_drazen",
        observacion="Diagnóstico incongruente con el estudio presentado.",
        reviewed_at="2026-10-21T12:00:00Z",
    )

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        manager.get_latest_review_status.return_value = "pendiente"
        manager.save_review_record.return_value = mock_saved_record
        factory.return_value = manager

        payload = {
            "decision": "rechazado",
            "reviewer_id": "auditor_drazen",
            "observacion": "Diagnóstico incongruente con el estudio presentado.",
            "expected_review_status": "pendiente",
        }

        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 200
        assert response.json()["review_status"] == "rechazado"


def test_post_review_rejected_without_observation_returns_422():
    doc_id = "DOC-CLIN-103"
    payload = {
        "decision": "rechazado",
        "reviewer_id": "auditor_drazen",
        "observacion": None,
        "expected_review_status": "pendiente",
    }
    with TestClient(app) as client:
        response = client.post(f"/api/documents/{doc_id}/review", json=payload)

    assert response.status_code == 422
    assert "observación es obligatoria" in response.text.lower()


def test_post_review_empty_reviewer_id_returns_422():
    doc_id = "DOC-CLIN-104"
    payload = {
        "decision": "aprobado",
        "reviewer_id": "   ",
        "observacion": "OK",
        "expected_review_status": "pendiente",
    }
    with TestClient(app) as client:
        response = client.post(f"/api/documents/{doc_id}/review", json=payload)

    assert response.status_code == 422


def test_post_review_invalid_decision_returns_422():
    doc_id = "DOC-CLIN-105"
    payload = {
        "decision": "indeciso",
        "reviewer_id": "auditor_drazen",
        "expected_review_status": "pendiente",
    }
    with TestClient(app) as client:
        response = client.post(f"/api/documents/{doc_id}/review", json=payload)

    assert response.status_code == 422


def test_post_review_invalid_document_id_returns_400():
    payload = {
        "decision": "aprobado",
        "reviewer_id": "auditor_drazen",
        "expected_review_status": "pendiente",
    }
    with TestClient(app) as client:
        response = client.post("/api/documents/id con espacios inválidos!/review", json=payload)

    assert response.status_code == 400


def test_post_review_document_not_found_returns_404():
    doc_id = "DOC-INEXISTENTE"
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = None
        factory.return_value = manager

        payload = {
            "decision": "aprobado",
            "reviewer_id": "auditor_drazen",
            "expected_review_status": "pendiente",
        }
        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"].lower()


def test_post_review_document_not_in_human_audit_status_returns_400():
    doc_id = "DOC-PROCESADO-YA"
    triage_doc = mock_triage_doc(doc_id, status_val="procesado", requires_human=False)

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        factory.return_value = manager

        payload = {
            "decision": "aprobado",
            "reviewer_id": "auditor_drazen",
            "expected_review_status": "pendiente",
        }
        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 400
        assert "auditoría humana" in response.json()["detail"].lower()


def test_post_review_already_reviewed_returns_409():
    doc_id = "DOC-YA-REVISADO"
    triage_doc = mock_triage_doc(doc_id)

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        manager.get_latest_review_status.return_value = "aprobado"
        factory.return_value = manager

        payload = {
            "decision": "aprobado",
            "reviewer_id": "auditor_drazen",
            "expected_review_status": "pendiente",
        }
        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 409
        assert "decisión final" in response.json()["detail"].lower()


def test_post_review_concurrency_conflict_412_from_oci_returns_409():
    doc_id = "DOC-CONCURRENTE"
    triage_doc = mock_triage_doc(doc_id)

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        manager.get_latest_review_status.return_value = "pendiente"
        # Simular que al momento exacto de guardar, otro auditor ganó la carrera en OCI
        manager.save_review_record.side_effect = DuplicateReviewError("La revisión ya existe.")
        factory.return_value = manager

        payload = {
            "decision": "aprobado",
            "reviewer_id": "auditor_drazen",
            "expected_review_status": "pendiente",
        }
        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 409
        assert "ya existe" in response.json()["detail"].lower()


def test_post_review_oci_timeout_returns_504():
    doc_id = "DOC-TIMEOUT"
    triage_doc = mock_triage_doc(doc_id)

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        manager.get_latest_review_status.return_value = "pendiente"
        manager.save_review_record.side_effect = OCITimeoutError("OCI timeout")
        factory.return_value = manager

        payload = {
            "decision": "aprobado",
            "reviewer_id": "auditor_drazen",
            "expected_review_status": "pendiente",
        }
        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 504


def test_post_review_oci_persistence_failure_returns_502():
    doc_id = "DOC-OCI-FAIL"
    triage_doc = mock_triage_doc(doc_id)

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        manager.get_latest_review_status.return_value = "pendiente"
        manager.save_review_record.side_effect = OCIPersistenceError("OCI 500 error")
        factory.return_value = manager

        payload = {
            "decision": "aprobado",
            "reviewer_id": "auditor_drazen",
            "expected_review_status": "pendiente",
        }
        with TestClient(app) as client:
            response = client.post(f"/api/documents/{doc_id}/review", json=payload)

        assert response.status_code == 502


# ==============================================================================
# TESTS GET /api/documents/{id}/review-history
# ==============================================================================

def test_get_review_history_success():
    doc_id = "DOC-HIST-001"
    triage_doc = mock_triage_doc(doc_id)

    history_records = [
        ReviewRecord(
            documento_id=doc_id,
            review_id="REV-001",
            review_status="rechazado",
            reviewer_id="auditor_01",
            observacion="Falta firma del médico tratante.",
            reviewed_at="2026-10-20T10:00:00Z",
        ),
        ReviewRecord(
            documento_id=doc_id,
            review_id="REV-002",
            review_status="aprobado",
            reviewer_id="auditor_02",
            observacion="Documento rectificado y aprobado.",
            reviewed_at="2026-10-21T11:00:00Z",
        ),
    ]

    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = triage_doc
        manager.list_reviews_for_document.return_value = history_records
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get(f"/api/documents/{doc_id}/review-history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["review_id"] == "REV-001"
        assert data[0]["review_status"] == "rechazado"
        assert data[1]["review_id"] == "REV-002"
        assert data[1]["review_status"] == "aprobado"


def test_get_review_history_document_not_found_returns_404():
    doc_id = "DOC-HIST-INEXISTENTE"
    with patch("app.api.routes.OCIStorageManager") as factory:
        manager = MagicMock()
        manager.recuperar_resultado_triage.return_value = None
        manager.list_reviews_for_document.return_value = []
        factory.return_value = manager

        with TestClient(app) as client:
            response = client.get(f"/api/documents/{doc_id}/review-history")

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"].lower()


def test_get_review_history_invalid_id_returns_400():
    with TestClient(app) as client:
        response = client.get("/api/documents/id inv@lido!!/review-history")

    assert response.status_code == 400
