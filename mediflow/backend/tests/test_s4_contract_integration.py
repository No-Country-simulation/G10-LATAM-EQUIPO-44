"""Agregado por Edil: regresiones de los conflictos Eliana/Drazen, sin OCI."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.main import app
from app.api.routes import router
from app.models.schemas import AuditoriaReviewRequest, AuditoriaReviewRecord, AuditoriaReviewResponse


def record():
    return {
        "documento_id": "DOC-SYNTHETIC-INTEGRATION", "review_id": "REV-SYNTHETIC-1",
        "review_status": "aprobado", "reviewer_id": "auditor_sintetico",
        "observacion": None, "reviewed_at": "2026-10-23T12:00:00Z",
    }


def test_integration_registers_real_routes_once_and_not_simulated_success():
    # FastAPI puede conservar routers incluidos de forma diferida en app.routes.
    # Verificar sus rutas declaradas y la exposición pública mediante OpenAPI.
    pairs = [(method, route.path) for route in router.routes for method in getattr(route, "methods", [])]
    for method, path in [("GET", "/api/reviews/pending"), ("POST", "/api/documents/{document_id}/review"),
                         ("GET", "/api/documents/{document_id}/review-history")]:
        assert pairs.count((method, path)) == 1
        assert method.lower() in app.openapi()["paths"][path]
    assert not any(path == "/api/auditoria/revision" for _, path in pairs)


@pytest.mark.parametrize("changes", [
    {}, {"expected_review_status": "aprobado"}, {"expected_review_status": "pendiente", "documento_id": "DOC-EXTRA"},
])
def test_contract_requires_explicit_expected_state_and_no_extra_fields(changes):
    with pytest.raises(ValidationError):
        AuditoriaReviewRequest.model_validate({"decision": "aprobado", "reviewer_id": "synthetic", **changes})


def test_request_trimmed_reviewer_and_observation_rules():
    request = AuditoriaReviewRequest(decision="aprobado", reviewer_id=" synthetic ", expected_review_status="pendiente")
    assert request.reviewer_id == "synthetic"
    assert request.observacion is None
    with pytest.raises(ValidationError):
        AuditoriaReviewRequest(decision="rechazado", reviewer_id="synthetic", observacion=" ", expected_review_status="pendiente")


@pytest.mark.parametrize("stamp", ["ayer", "2026-10-23T12:00:00", "2026-10-23T12:00:00+01:00", "2026-10-23T12:00:00+00:00", 1792756800])
def test_response_and_record_reject_non_contract_timestamp(stamp):
    data = {**record(), "reviewed_at": stamp}
    for model in [AuditoriaReviewRecord, AuditoriaReviewResponse]:
        with pytest.raises(ValidationError):
            model.model_validate(data)


def test_record_datetime_utc_and_serialization_preserve_six_fields():
    parsed = AuditoriaReviewRecord.model_validate(record())
    assert parsed.reviewed_at.tzinfo is not None
    assert parsed.model_dump(mode="json") == record()
    parsed = AuditoriaReviewRecord.model_validate({**record(), "reviewed_at": datetime(2026, 10, 23, tzinfo=timezone.utc)})
    assert parsed.reviewed_at.utcoffset().total_seconds() == 0
    with pytest.raises(ValidationError):
        AuditoriaReviewRecord.model_validate({**record(), "reviewed_at": datetime(2026, 10, 23)})
    with pytest.raises(ValidationError):
        AuditoriaReviewRecord.model_validate({**record(), "extra": "not allowed"})
    data = record()
    del data["observacion"]
    with pytest.raises(ValidationError):
        AuditoriaReviewRecord.model_validate(data)
