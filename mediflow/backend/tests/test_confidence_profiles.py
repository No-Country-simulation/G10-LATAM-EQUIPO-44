"""S3-02.1 / S3-02.4: política documental provisional, sin nube."""
from copy import deepcopy
import json

import pytest

from app.services.servicio_orquestador import procesar_con_orquestador
from data_ai.confidence_profiles import (
    EstadoCriterio as E, cargar_perfiles, evaluar_criterio, evaluar_documento,
)
from test_orquestador_integration import document


@pytest.fixture(autouse=True)
def general(monkeypatch):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "general")


@pytest.mark.parametrize("profile", ["general", "synthetic_demo_v1"])
@pytest.mark.parametrize("missing", ["medicamentos", "paciente", "tipo", "elemento"])
def test_essential_missing_blocks_even_high_score(monkeypatch, profile, missing):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", profile)
    doc = document(score=0.99)
    if missing == "medicamentos":
        doc["datos_extraidos"]["medicamentos_recetados"] = []
    elif missing == "paciente":
        doc["datos_extraidos"].pop("paciente")
    elif missing == "elemento":
        doc["datos_extraidos"]["medicamentos_recetados"].append({"medicamento": " "})
    else:
        doc["clasificacion"]["tipo_documento"] = "Informe médico arbitrario"
    before = deepcopy(doc)
    result = procesar_con_orquestador(doc)
    assert result["status"] == "auditoria_humana"
    assert result["decision_enrutamiento"]["destino_principal"] == "Cola_Revision_Humana"
    assert doc == before


@pytest.mark.parametrize("kind", [
    "Informe de Laboratorio", "Informe de Estudio por Imágenes",
    "Orden / Solicitud de Procedimiento", "Epicrisis / Informe de Alta", "Certificado Médico",
])
def test_unrepresented_essential_is_never_counted_as_fulfilled(kind):
    doc = document()
    doc["clasificacion"]["tipo_documento"] = kind
    result = evaluar_documento(doc)
    assert E.NO_VERIFICABLE in result["estados"].values()
    assert result["completitud"] < 1
    assert result["es_ambiguo"]
    assert procesar_con_orquestador(doc)["status"] == "auditoria_humana"


def test_certificate_without_diagnosis_is_not_penalized_for_diagnosis():
    doc = document()
    doc["clasificacion"]["tipo_documento"] = "Certificado Médico"
    doc["datos_extraidos"]["estudio_realizado"] = None
    result = evaluar_documento(doc)
    assert result["estados"]["diagnostico"] == E.NO_APLICABLE
    assert result["completitud"] == 3 / 4
    assert result["bloqueos"] == ["motivo_periodo_firma"]
    doc["datos_extraidos"]["diagnostico_principal"] = "Texto sintético"
    assert evaluar_documento(doc) == result


def test_states_do_not_infer_not_applicable_from_null():
    rule = dict(id="x", path="diagnostico_principal", required=True, applicable=True, verifiable=True)
    assert evaluar_criterio({}, rule) == E.AUSENTE
    assert evaluar_criterio({"diagnostico_principal": "ILLEGIBLE"}, rule) == E.NO_VERIFICABLE
    assert evaluar_criterio({"diagnostico_principal": "Texto"}, rule) == E.PRESENTE
    assert evaluar_criterio({}, dict(rule, applicable=False)) == E.NO_APLICABLE
    assert evaluar_criterio({}, dict(rule, verifiable=False)) == E.NO_VERIFICABLE


def test_nonverifiable_can_block_even_above_threshold():
    version, profiles = deepcopy(cargar_perfiles())
    profile = profiles["receta medica"]
    profile["criteria"].append(dict(id="evidencia_pendiente", path=None, required=True, applicable=True, verifiable=False))
    result = evaluar_documento(document(), configuracion=(version, profiles))
    assert result["completitud"] == 4 / 5
    assert result["score_operativo"] == 0.8
    assert result["es_ambiguo"] is True


def test_only_excluded_criteria_cannot_manufacture_acceptance_for_unknown():
    doc = document()
    doc["clasificacion"]["tipo_documento"] = ""
    result = evaluar_documento(doc, configuracion=("empty-test", {}))
    assert result["completitud"] == 0
    assert result["es_ambiguo"]


@pytest.mark.parametrize("kind", [" RECETA   MEDICA ", "Receta Médica"])
def test_canonical_normalization(kind):
    doc = document()
    doc["clasificacion"]["tipo_documento"] = kind
    assert evaluar_documento(doc)["es_ambiguo"] is False


def test_configuration_rejects_colliding_aliases(tmp_path):
    version, profiles = cargar_perfiles()
    profile = deepcopy(profiles["receta medica"])
    profile["aliases"] = [" RECETA MEDICA "]
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(dict(version=version, profiles=[profile])), encoding="utf-8")
    with pytest.raises(ValueError, match="ambiguo"):
        cargar_perfiles(path)


@pytest.mark.parametrize("protection", ["dose", "low", "review", "status", "destination"])
def test_profiles_preserve_review_and_urgent_priority(protection):
    doc = document(priority="Urgente")
    if protection == "dose":
        doc["datos_extraidos"]["medicamentos_recetados"][0]["dosis"] = "ILLEGIBLE"
    elif protection == "low":
        doc["clasificacion"]["score_confianza_clasificacion"] = 0.69
    elif protection == "status":
        doc["status"] = "auditoria_humana"
    elif protection == "destination":
        doc["decision_enrutamiento"]["destino_principal"] = "Cola_Revision_Humana"
    else:
        doc["decision_enrutamiento"]["requiere_auditoria_humana"] = True
    result = procesar_con_orquestador(doc)
    assert result["status"] == "auditoria_humana"
    assert result["clasificacion"]["nivel_prioridad"] == "Urgente"


@pytest.mark.parametrize("alias", ["Informe de imagenología", "Orden / procedimiento"])
def test_dataset_aliases_registered(alias):
    doc = document()
    doc["clasificacion"]["tipo_documento"] = alias
    assert evaluar_documento(doc)["estados"]["tipo_registrado"] == E.PRESENTE


@pytest.mark.parametrize("kind", ["Receta Médica", "Informe de Laboratorio", "Informe de Estudio por Imágenes", "Orden / Solicitud de Procedimiento", "Epicrisis / Informe de Alta", "Certificado Médico"])
def test_patient_is_essential_in_every_profile(kind):
    doc = document()
    doc["clasificacion"]["tipo_documento"] = kind
    doc["datos_extraidos"]["paciente"] = {"nombre": None}
    assert "paciente" in evaluar_documento(doc)["bloqueos"]


def test_demo_does_not_waive_illegible_verifiable_essential(monkeypatch):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "synthetic_demo_v1")
    doc = document()
    doc["datos_extraidos"]["medicamentos_recetados"][0]["medicamento"] = "ILLEGIBLE"
    assert procesar_con_orquestador(doc)["status"] == "auditoria_humana"


def test_optional_values_do_not_inflate_or_penalize_completeness():
    config = deepcopy(cargar_perfiles())
    config[1]["receta medica"]["criteria"].append(dict(id="opcional", path="cie10_sugerido", required=False, applicable=True, verifiable=True))
    doc = document()
    absent = evaluar_documento(doc, configuracion=config)
    doc["datos_extraidos"]["cie10_sugerido"] = "Texto sintético"
    present = evaluar_documento(doc, configuracion=config)
    assert absent["completitud"] == present["completitud"] == 1
    assert absent["estados"]["opcional"] == E.AUSENTE
    assert present["estados"]["opcional"] == E.PRESENTE
