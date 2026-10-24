"""Agregado por Edil: mínimos documentales reales con datos sintéticos, sin nube."""
from copy import deepcopy
import json

import pytest

from app.services.servicio_orquestador import procesar_con_orquestador
from data_ai.confidence_profiles import (
    LEGACY_DEMO_PROFILES, EstadoCriterio as E, cargar_perfiles, evaluar_criterio, evaluar_documento,
)
from test_orquestador_integration import document

KINDS = [
    "Receta Médica", "Informe de Laboratorio", "Informe de Estudio por Imágenes",
    "Orden / Solicitud de Procedimiento", "Epicrisis / Informe de Alta", "Certificado Médico",
]


def complete_document(kind):
    doc = document()
    doc["clasificacion"]["tipo_documento"] = kind
    doc["datos_extraidos"].update({
        "resultados_laboratorio": [{"examen": "Examen sintético", "valor": "Negativo", "unidad": None, "rango_referencia": None}],
        "hallazgos": "Hallazgos textuales sintéticos.", "conclusion": None,
        "procedimiento_solicitado": "Procedimiento descrito en la fuente sintética.",
        "indicacion_solicitud": None, "resumen_evolucion": "Resumen del episodio sintético.",
        "indicacion_alta": "Cierre del episodio consignado literalmente.",
        "destino_alta": None, "seguimiento": None,
        "contenido_certificacion": "Contenido certificante de prueba.", "periodo_certificado": None,
    })
    return doc


@pytest.fixture(autouse=True)
def general(monkeypatch):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "general")


@pytest.mark.parametrize("kind", KINDS)
def test_six_complete_standard_documents_can_be_processed(kind):
    doc = complete_document(kind)
    before = deepcopy(doc)
    assessment = evaluar_documento(doc)
    result = procesar_con_orquestador(doc, source_text="Documento sintético de control habitual.")
    assert assessment["version"] == "s4-minimos-documentales-v1"
    assert assessment["completitud"] == 1
    assert assessment["score_operativo"] == 0.95
    assert assessment["bloqueos"] == []
    assert result["status"] == "procesado"
    assert not result["decision_enrutamiento"]["requiere_auditoria_humana"]
    assert doc == before


@pytest.mark.parametrize("kind,field", [
    (KINDS[0], "profesional_emisor"), (KINDS[1], "resultados_laboratorio"),
    (KINDS[2], "hallazgos"), (KINDS[3], "procedimiento_solicitado"),
    (KINDS[4], "resumen_evolucion"), (KINDS[4], "indicacion_alta"),
    (KINDS[5], "contenido_certificacion"), (KINDS[5], "profesional_emisor"),
])
def test_missing_new_essential_cannot_be_hidden_by_high_classification(kind, field):
    doc = complete_document(kind)
    doc["clasificacion"]["score_confianza_clasificacion"] = 0.99
    doc["datos_extraidos"][field] = [] if field == "resultados_laboratorio" else None
    assessment = evaluar_documento(doc)
    assert assessment["bloqueos"]
    assert assessment["es_ambiguo"]
    assert procesar_con_orquestador(doc)["status"] == "auditoria_humana"


@pytest.mark.parametrize("leaf", ["examen", "valor"])
def test_every_lab_result_needs_its_own_exam_and_value(leaf):
    doc = complete_document(KINDS[1])
    doc["datos_extraidos"]["resultados_laboratorio"].append({"examen": "Segundo examen", "valor": "0", "unidad": None, "rango_referencia": None})
    assert evaluar_documento(doc)["completitud"] == 1
    doc["datos_extraidos"]["resultados_laboratorio"][1][leaf] = " "
    assert evaluar_documento(doc)["es_ambiguo"]


@pytest.mark.parametrize("leaf", ["examen", "valor"])
def test_illegible_lab_component_remains_not_verifiable(leaf):
    doc = complete_document(KINDS[1])
    doc["datos_extraidos"]["resultados_laboratorio"][0][leaf] = "  illegible  "
    assessment = evaluar_documento(doc)
    assert E.NO_VERIFICABLE in assessment["estados"].values()
    assert assessment["es_ambiguo"]


@pytest.mark.parametrize("provided", ["hallazgos", "conclusion"])
def test_images_allow_either_explicit_content_field(provided):
    doc = complete_document(KINDS[2])
    doc["datos_extraidos"]["hallazgos"] = None
    doc["datos_extraidos"][provided] = "Texto documental sintético legible."
    assert evaluar_documento(doc)["es_ambiguo"] is False


def test_legible_alternative_does_not_erase_explicit_illegibility():
    doc = complete_document(KINDS[2])
    doc["datos_extraidos"]["conclusion"] = "ILLEGIBLE"
    assert evaluar_documento(doc)["estados"]["hallazgos_conclusion"] == E.NO_VERIFICABLE
    assert procesar_con_orquestador(doc)["status"] == "auditoria_humana"


def test_requester_diagnosis_and_performed_study_do_not_supply_other_roles():
    recipe = complete_document(KINDS[0])
    recipe["datos_extraidos"]["profesional_emisor"] = None
    assert "profesional" in evaluar_documento(recipe)["bloqueos"]
    image = complete_document(KINDS[2])
    image["datos_extraidos"]["hallazgos"] = None
    image["datos_extraidos"]["diagnostico_principal"] = "Diagnóstico textual sintético."
    assert "hallazgos_conclusion" in evaluar_documento(image)["bloqueos"]
    order = complete_document(KINDS[3])
    order["datos_extraidos"]["procedimiento_solicitado"] = None
    assert "procedimiento_solicitado" in evaluar_documento(order)["bloqueos"]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("protection", ["low", "prior_review", "dose"])
def test_new_documentary_minimums_preserve_existing_protections(kind, protection):
    doc = complete_document(kind)
    doc["clasificacion"]["nivel_prioridad"] = "Urgente"
    if protection == "low":
        doc["clasificacion"]["score_confianza_clasificacion"] = 0.69
    elif protection == "prior_review":
        doc["decision_enrutamiento"].update(requiere_auditoria_humana=True, destino_principal="Cola_Revision_Humana")
    else:
        doc["datos_extraidos"]["medicamentos_recetados"][0]["dosis"] = "ILLEGIBLE"
    result = procesar_con_orquestador(doc)
    assert result["status"] == "auditoria_humana"
    assert result["clasificacion"]["nivel_prioridad"] == "Urgente"


def test_nullable_dose_and_optional_units_do_not_manufacture_critical_alerts():
    doc = complete_document(KINDS[0])
    doc["datos_extraidos"]["medicamentos_recetados"][0]["dosis"] = None
    assert evaluar_documento(doc)["es_ambiguo"] is False
    lab = complete_document(KINDS[1])
    assert evaluar_documento(lab)["completitud"] == 1
    lab["datos_extraidos"]["resultados_laboratorio"][0].update(unidad="unidad consignada", rango_referencia="rango consignado")
    assert evaluar_documento(lab)["completitud"] == 1


@pytest.mark.parametrize("kind", KINDS[1:])
def test_legacy_payload_missing_new_fields_does_not_pass_general(kind):
    doc = document()
    doc["clasificacion"]["tipo_documento"] = kind
    assert procesar_con_orquestador(doc)["status"] == "auditoria_humana"


@pytest.mark.parametrize("kind", KINDS)
def test_synthetic_demo_uses_explicit_old_profile_compatibility(monkeypatch, kind):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "synthetic_demo_v1")
    doc = document()
    doc["clasificacion"]["tipo_documento"] = kind
    old = evaluar_documento(doc, configuracion=cargar_perfiles(LEGACY_DEMO_PROFILES))
    assert old["version"] == "s3-laura-mvp-provisional-1"
    assert procesar_con_orquestador(doc)["status"] == "procesado"


@pytest.mark.parametrize("alternatives,path", [([], None), (["hallazgos"], None), (["hallazgos", "hallazgos"], None), (["hallazgos", 2], None), (["hallazgos", "conclusion"], "hallazgos"), (["hallazgos", "bad..path"], None)])
def test_invalid_or_configuration_is_rejected(tmp_path, alternatives, path):
    profile = deepcopy(cargar_perfiles()[1]["receta medica"])
    profile["criteria"][0].update(path=path, any_of_paths=alternatives)
    config = tmp_path / "profiles.json"
    config.write_text(json.dumps({"version": "invalid-test", "profiles": [profile]}), encoding="utf-8")
    with pytest.raises(ValueError):
        cargar_perfiles(config)


def test_unknown_document_and_non_applicable_values_keep_their_semantics():
    doc = complete_document(KINDS[0])
    doc["clasificacion"]["tipo_documento"] = "Tipo no catalogado"
    result = evaluar_documento(doc)
    assert result["completitud"] == 0 and result["es_ambiguo"]
    rule = {"path": "contenido_certificacion", "required": True, "applicable": False, "verifiable": True}
    assert evaluar_criterio({}, rule) == E.NO_APLICABLE
