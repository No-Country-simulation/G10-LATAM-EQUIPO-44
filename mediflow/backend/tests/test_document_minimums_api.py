"""Agregado por Edil: contrato ampliado de POST a persistencia y GET.

Se ejecutan el endpoint, el pipeline y el orquestador reales. Gemini y OCI
son sustitutos locales explícitos; no se crean clientes SDK ni conexiones.
"""
from copy import deepcopy
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api import routes
from app.models.schemas import TriageResponse
from app.services import triage_pipeline


CASES = [
    ("Receta Médica", "medicamentos_recetados", [{"medicamento": "Medicamento sintético", "dosis": None}]),
    ("Informe de Laboratorio", "resultados_laboratorio", [{"examen": "Examen sintético", "valor": "Negativo", "unidad": None, "rango_referencia": None}]),
    ("Informe de Estudio por Imágenes", "conclusion", "Sin alteraciones consignadas en el documento sintético."),
    ("Orden / Solicitud de Procedimiento", "procedimiento_solicitado", "Procedimiento documental sintético"),
    ("Epicrisis / Informe de Alta", "indicacion_alta", "Cierre del episodio sintético indicado por su emisor."),
    ("Certificado Médico", "contenido_certificacion", "Constancia sintética para comprobar extracción documental."),
]

EXTENDED_FIELDS = {
    "profesional_emisor", "resultados_laboratorio", "hallazgos", "conclusion",
    "procedimiento_solicitado", "indicacion_solicitud", "resumen_evolucion",
    "indicacion_alta", "destino_alta", "seguimiento", "contenido_certificacion",
    "periodo_certificado",
}


def clinical_document(kind, *, priority="Rutina", review=False):
    return {
        "status": "auditoria_humana" if review else "procesado",
        "documento_id": "DOC-SYNTHETIC-EXTRACTED",
        # El autor no procede de la respuesta IA y la API debe descartarlo.
        "cargado_por": "invented-by-extraction",
        "clasificacion": {
            "tipo_documento": kind, "especialidad": None,
            "nivel_prioridad": priority, "score_confianza_clasificacion": 0.95,
        },
        "datos_extraidos": {
            "paciente": {"nombre": "Persona ficticia", "edad": None},
            "medico_solicitante": {"nombre": "Solicitante sintético", "matricula": None},
            "profesional_emisor": {"nombre": "Emisor sintético distinto", "matricula": None},
            "estudio_realizado": "Estudio documental sintético",
            "diagnostico_principal": None, "cie10_sugerido": None,
            "medicamentos_recetados": [], "resultados_laboratorio": [],
            "hallazgos": None, "conclusion": None, "procedimiento_solicitado": None,
            "indicacion_solicitud": None,
            "resumen_evolucion": "Resumen documental de un episodio totalmente ficticio.",
            "indicacion_alta": None, "destino_alta": None, "seguimiento": None,
            "contenido_certificacion": None, "periodo_certificado": None,
        },
        "decision_enrutamiento": {
            "destino_principal": "Cola_Revision_Humana" if review else "Cola_Historia_Clinica",
            "requiere_auditoria_humana": review,
            "justificacion_enrutamiento": "Comprobación documental con datos sintéticos.",
        },
        "notificacion_generada": None,
        "almacenamiento_oci": {"bucket": "recibidos", "ruta_objeto": "synthetic.txt", "status_backup": "exito"},
    }


class MemoryStorage:
    """Sustituto OCI sin SDK; conserva las dos escrituras del endpoint."""

    settings = SimpleNamespace(bucket_recibidos="recibidos")

    def __init__(self):
        self.documents = {}
        self.saves = []
        self.uploads = []
        self.copies = []

    def subir_a_recibidos(self, content, object_name):
        self.uploads.append((bytes(content), object_name))
        return object_name

    def guardar_resultado_triage(self, document):
        self.saves.append(deepcopy(document))
        self.documents[document["documento_id"]] = deepcopy(document)

    def recuperar_resultado_triage(self, identifier):
        return deepcopy(self.documents.get(identifier))

    def determinar_bucket_por_estado(self, state):
        return {"procesado": "procesados", "auditoria_humana": "auditoria_humana"}[state]

    def copiar_archivo(self, object_name, source, destination):
        self.copies.append((object_name, source, destination))


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "general")
    manager = MemoryStorage()
    monkeypatch.setattr(routes, "OCIStorageManager", lambda: manager)
    return manager


def use_synthetic_extraction(monkeypatch, document):
    class SyntheticGemini:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def process_document(self, content, filename, *, document_id, storage):
            assert content == b"Documento sintetico normal de prueba."
            assert filename == "synthetic.txt"
            data = deepcopy(document)
            data["documento_id"] = document_id
            data["almacenamiento_oci"] = deepcopy(storage)
            return TriageResponse.model_validate(data)

    monkeypatch.setattr(triage_pipeline, "GeminiClinicalClient", SyntheticGemini)


def post_and_get(document, monkeypatch, storage):
    use_synthetic_extraction(monkeypatch, document)
    with TestClient(app) as client:
        posted = client.post("/api/triage",
            files={"file": ("synthetic.txt", b"Documento sintetico normal de prueba.")},
            data={"analyze": "true"})
        assert posted.status_code == 201
        result = posted.json()
        recovered = client.get("/api/documents/" + result["documento_id"])
    assert recovered.status_code == 200
    assert recovered.json() == result
    assert storage.documents[result["documento_id"]] == result
    assert len(storage.uploads) == 1
    assert len(storage.copies) == 1
    assert len(storage.saves) == 2
    assert storage.saves[0]["status"] == "recibido"
    assert result["cargado_por"] is None
    return result


@pytest.mark.parametrize("kind,field,value", CASES, ids=[item[0] for item in CASES])
def test_six_complete_types_flow_through_real_pipeline_and_persist_new_fields(kind, field, value, monkeypatch, storage):
    document = clinical_document(kind)
    document["datos_extraidos"][field] = deepcopy(value)
    result = post_and_get(document, monkeypatch, storage)
    assert result["status"] == "procesado"
    assert result["decision_enrutamiento"]["requiere_auditoria_humana"] is False
    assert result["datos_extraidos"][field] == value
    assert result["datos_extraidos"]["profesional_emisor"]["nombre"] != result["datos_extraidos"]["medico_solicitante"]["nombre"]
    assert result["almacenamiento_oci"]["bucket"] == "procesados"


@pytest.mark.parametrize("kind,field,value", CASES, ids=[item[0] for item in CASES])
def test_missing_represented_minimum_still_routes_to_human_review(kind, field, value, monkeypatch, storage):
    document = clinical_document(kind)
    document["datos_extraidos"][field] = [] if isinstance(value, list) else None
    result = post_and_get(document, monkeypatch, storage)
    assert result["status"] == "auditoria_humana"
    assert result["decision_enrutamiento"]["requiere_auditoria_humana"] is True
    assert result["decision_enrutamiento"]["destino_principal"] == "Cola_Revision_Humana"
    assert result["almacenamiento_oci"]["bucket"] == "auditoria_humana"


@pytest.mark.parametrize("review", [False, True], ids=["urgent", "urgent-and-prior-review"])
def test_complete_document_never_loses_urgency_or_prior_review(review, monkeypatch, storage):
    document = clinical_document("Informe de Estudio por Imágenes", priority="Urgente", review=review)
    document["datos_extraidos"]["conclusion"] = "Conclusión documental sintética legible."
    result = post_and_get(document, monkeypatch, storage)
    assert result["clasificacion"]["nivel_prioridad"] == "Urgente"
    assert result["status"] == ("auditoria_humana" if review else "procesado")
    assert result["decision_enrutamiento"]["destino_principal"] == ("Cola_Revision_Humana" if review else "Cola_Emergencia_Medica")


def test_legacy_stored_json_is_readable_without_rewriting_history(storage):
    document = clinical_document("Informe de Laboratorio")
    document["documento_id"] = "DOC-SYNTHETIC-LEGACY"
    document.pop("cargado_por")
    for field in EXTENDED_FIELDS:
        document["datos_extraidos"].pop(field)
    storage.documents[document["documento_id"]] = deepcopy(document)
    with TestClient(app) as client:
        response = client.get("/api/documents/" + document["documento_id"])
    assert response.status_code == 200
    assert response.json()["status"] == "procesado"
    assert response.json()["datos_extraidos"]["profesional_emisor"] is None
    assert response.json()["datos_extraidos"]["resultados_laboratorio"] == []
    assert storage.documents[document["documento_id"]] == document
    assert storage.saves == []
    assert storage.uploads == []
    assert storage.copies == []
