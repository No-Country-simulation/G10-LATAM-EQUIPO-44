"""S3-05: orden real de módulos y conservación de decisiones; transportes locales."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import orquestador
from app.models.schemas import TriageResponse
from test_s3_complete_pipeline import MemoryStorage, clinical


@pytest.mark.parametrize("scenario,protection,profile", [
    ("normal", None, "general"),
    ("urgent", None, "synthetic_demo_v1"),
    ("audit", "prior_review", "general"),
    *[("urgent", protection, profile) for profile in ("general", "synthetic_demo_v1")
      for protection in ("low_score", "illegible_dose", "prior_review")],
])
def test_order_and_post_get_conserve_contract_and_review(monkeypatch, scenario, protection, profile):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", profile)
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "model-under-test")
    events=[]
    storage=MemoryStorage(events)
    payload=clinical(review=protection in ("prior_review", "illegible_dose"))
    if scenario == "urgent" and profile == "general":
        # Prioridad de clasificación previa: nunca se rebaja por confianza.
        payload["clasificacion"]["nivel_prioridad"]="Urgente"
    if protection == "low_score": payload["clasificacion"]["score_confianza_clasificacion"]=0.69
    if protection == "illegible_dose": payload["datos_extraidos"]["medicamentos_recetados"][0]["dosis"]="ILLEGIBLE"
    if protection == "prior_destination": payload["decision_enrutamiento"]["destino_principal"]="Cola_Revision_Humana"
    source=b"Glicemia en ayunas: 250 mg/dL." if profile == "synthetic_demo_v1" else b"Synthetic software control."
    confidence=orquestador._confidence_is_ambiguous
    urgency=orquestador._urgency_requires_review
    def confidence_trace(doc):
        events.append("confidence")
        return confidence(doc)
    def urgency_trace(doc, **kwargs):
        events.append("urgency")
        return urgency(doc, **kwargs)
    monkeypatch.setattr(orquestador,"_confidence_is_ambiguous",confidence_trace)
    monkeypatch.setattr(orquestador,"_urgency_requires_review",urgency_trace)
    with patch("app.api.routes.OCIStorageManager",return_value=storage), patch("app.services.gemini_client.genai.Client") as sdk:
        def generate(**kwargs):
            events.append("classification")
            return SimpleNamespace(text=json.dumps(payload),candidates=None)
        sdk.return_value.models.generate_content.side_effect=generate
        with TestClient(app) as client:
            response=client.post("/api/triage",data={"analyze":"true"},files={"file":("synthetic.txt",source)})
            assert response.status_code == 201
            result=response.json()
            recovered=client.get("/api/documents/"+result["documento_id"])
    review=protection is not None
    expected_state="auditoria_humana" if review else "procesado"
    expected_priority="Urgente" if scenario=="urgent" else "Rutina"
    expected_destination="Cola_Revision_Humana" if review else "Cola_Emergencia_Medica" if scenario=="urgent" else "Cola_Farmacia"
    assert events == ["original","recibido","classification","confidence","urgency","copia",expected_state]
    assert result["status"]==expected_state
    assert result["clasificacion"]["nivel_prioridad"]==expected_priority
    assert result["decision_enrutamiento"]["destino_principal"]==expected_destination
    assert result["decision_enrutamiento"]["requiere_auditoria_humana"] is review
    bucket="auditoria_humana" if review else "procesados"
    assert result["almacenamiento_oci"]["bucket"]==bucket
    assert set(result)==set(TriageResponse.model_fields)
    assert set(result["decision_enrutamiento"])=={"destino_principal","requiere_auditoria_humana","justificacion_enrutamiento"}
    assert recovered.status_code==200 and recovered.json()==result
    assert sdk.return_value.models.generate_content.call_count==1


def test_general_never_invokes_demo_rules_even_if_demo_phrase_is_present(monkeypatch):
    from app.services.servicio_orquestador import procesar_con_orquestador
    from test_orquestador_integration import document
    monkeypatch.setenv("TRIAGE_RULES_PROFILE","general")
    def forbidden(*args,**kwargs): pytest.fail("Regla exclusiva de demo activada en general")
    monkeypatch.setattr(orquestador,"evaluate_synthetic_demo",forbidden)
    result=procesar_con_orquestador(document(),source_text="Glicemia en ayunas: 250 mg/dL.")
    assert result["clasificacion"]["nivel_prioridad"]=="Rutina"
    assert result["decision_enrutamiento"]["destino_principal"]=="Cola_Farmacia"


@pytest.mark.parametrize("profile", ["general", "synthetic_demo_v1"])
@pytest.mark.parametrize("protection", ["prior_status", "prior_destination"])
def test_existing_review_markers_at_orchestration_entry_are_preserved(monkeypatch, profile, protection):
    from app.services.servicio_orquestador import procesar_con_orquestador
    from test_orquestador_integration import document
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", profile)
    doc=document(priority="Urgente")
    if protection == "prior_status": doc["status"]="auditoria_humana"
    else: doc["decision_enrutamiento"]["destino_principal"]="Cola_Revision_Humana"
    result=procesar_con_orquestador(doc)
    assert result["status"]=="auditoria_humana"
    assert result["clasificacion"]["nivel_prioridad"]=="Urgente"
    assert result["decision_enrutamiento"]["destino_principal"]=="Cola_Revision_Humana"
    assert result["decision_enrutamiento"]["requiere_auditoria_humana"] is True


@pytest.mark.parametrize("profile", ["general", "synthetic_demo_v1"])
@pytest.mark.parametrize("contradiction", ["illegible_without_review", "review_queue_without_flag"])
def test_contradictory_classification_is_rejected_before_orchestration_and_copy(monkeypatch, profile, contradiction):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", profile)
    monkeypatch.setenv("GEMINI_API_KEY", "unit-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "model-under-test")
    payload=clinical()
    if contradiction=="illegible_without_review": payload["datos_extraidos"]["medicamentos_recetados"][0]["dosis"]="ILLEGIBLE"
    else: payload["decision_enrutamiento"]["destino_principal"]="Cola_Revision_Humana"
    events=[]
    storage=MemoryStorage(events)
    with patch("app.api.routes.OCIStorageManager",return_value=storage), patch("app.services.gemini_client.genai.Client") as sdk:
        sdk.return_value.models.generate_content.return_value=SimpleNamespace(text=json.dumps(payload),candidates=None)
        with TestClient(app) as client:
            response=client.post("/api/triage",data={"analyze":"true"},files={"file":("synthetic.txt",b"Synthetic software fixture.")})
            assert response.status_code==502
            recovered=client.get("/api/documents/"+response.headers["X-Document-ID"])
    assert events==["original","recibido"]
    assert recovered.status_code==200 and recovered.json()["status"]=="recibido"
