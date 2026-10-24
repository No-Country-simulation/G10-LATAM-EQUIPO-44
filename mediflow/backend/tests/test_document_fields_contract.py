"""Agregado por Edil: ampliación documental, sin OCI ni llamadas Gemini."""
from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    DatosExtraidosSchema, DOCUMENTARY_EXTENSION_FIELDS, TriageResponse,
)
from app.services.gemini_client import (
    clinical_output_schema, clinical_validation_schema, validate_clinical_response,
)
from app.services.llm_errors import LLMResponseError


KINDS = [
    "Receta Médica", "Informe de Laboratorio", "Informe de Estudio por Imágenes",
    "Orden / Solicitud de Procedimiento", "Epicrisis / Informe de Alta", "Certificado Médico",
]


def legacy_payload():
    return {
        "clasificacion": {"tipo_documento": "Receta Médica", "especialidad": None,
                          "nivel_prioridad": "Rutina", "score_confianza_clasificacion": 0.95},
        "datos_extraidos": {
            "paciente": {"nombre": "Persona ficticia", "edad": None},
            "medico_solicitante": {"nombre": "Solicitante ficticio", "matricula": None},
            "estudio_realizado": None, "diagnostico_principal": None, "cie10_sugerido": None,
            "medicamentos_recetados": [{"medicamento": "Producto sintético", "dosis": None}],
        },
        "decision_enrutamiento": {"destino_principal": "Cola_Farmacia", "requiere_auditoria_humana": False,
                                   "justificacion_enrutamiento": "Ejemplo de software, sin información clínica real."},
    }


def complete_payload(kind):
    payload = legacy_payload()
    payload["clasificacion"]["tipo_documento"] = kind
    extracted = DatosExtraidosSchema.model_validate(payload["datos_extraidos"]).model_dump()
    extracted["profesional_emisor"] = {"nombre": "Emisor ficticio", "matricula": None}
    if kind == "Informe de Laboratorio":
        extracted.update(estudio_realizado="Examen sintético", resultados_laboratorio=[
            {"examen": "Examen sintético", "valor": "0", "unidad": None, "rango_referencia": None}])
    elif kind == "Informe de Estudio por Imágenes":
        extracted.update(estudio_realizado="Estudio sintético", hallazgos="Texto de hallazgos ficticios")
    elif kind == "Orden / Solicitud de Procedimiento":
        extracted.update(procedimiento_solicitado="Procedimiento sintético", indicacion_solicitud=None)
    elif kind == "Epicrisis / Informe de Alta":
        extracted.update(resumen_evolucion="Resumen ficticio del episodio", indicacion_alta="Constancia ficticia de cierre")
    elif kind == "Certificado Médico":
        extracted.update(contenido_certificacion="Contenido certificante ficticio", periodo_certificado=None)
    payload["datos_extraidos"] = extracted
    return payload


def test_old_extraction_is_read_without_inventing_new_content_or_roles():
    payload = legacy_payload()
    before = deepcopy(payload)
    result = validate_clinical_response(json.dumps(payload))
    assert result.datos_extraidos.profesional_emisor is None
    assert result.datos_extraidos.resultados_laboratorio == []
    for name in DOCUMENTARY_EXTENSION_FIELDS - {"resultados_laboratorio"}:
        assert getattr(result.datos_extraidos, name) is None
    assert result.datos_extraidos.medico_solicitante.nombre == "Solicitante ficticio"
    assert payload == before


def test_stored_triage_json_remains_readable_without_rewriting_input():
    data = {**legacy_payload(), "documento_id": "DOC-SYNTHETIC-HISTORY", "status": "procesado",
            "almacenamiento_oci": {"bucket": "procesados", "ruta_objeto": "synthetic.txt", "status_backup": "exito"}}
    before = deepcopy(data)
    parsed = TriageResponse.model_validate(data)
    assert parsed.datos_extraidos.conclusion is None
    assert parsed.datos_extraidos.profesional_emisor is None
    assert data == before


@pytest.mark.parametrize("kind", KINDS)
def test_documentary_fields_for_each_real_catalog_type_are_valid(kind):
    payload = complete_payload(kind)
    before = deepcopy(payload)
    parsed = validate_clinical_response(json.dumps(payload))
    assert parsed.datos_extraidos.model_dump() == payload["datos_extraidos"]
    assert parsed.clasificacion.tipo_documento == kind
    assert payload == before


@pytest.mark.parametrize("value", ["0", "Negativo", "<0,05", "Texto literal de resultado"])
def test_lab_value_is_literal_and_accepts_zero_and_qualitative_result(value):
    payload = complete_payload("Informe de Laboratorio")
    payload["datos_extraidos"]["resultados_laboratorio"][0]["valor"] = value
    parsed = validate_clinical_response(json.dumps(payload))
    assert parsed.datos_extraidos.resultados_laboratorio[0].valor == value
    assert parsed.datos_extraidos.resultados_laboratorio[0].unidad is None


@pytest.mark.parametrize("field", [
    "paciente", "medico_solicitante", "estudio_realizado", "diagnostico_principal",
    "cie10_sugerido", "medicamentos_recetados",
])
def test_compatibility_does_not_relax_any_original_required_key(field):
    payload = legacy_payload()
    del payload["datos_extraidos"][field]
    with pytest.raises(LLMResponseError):
        validate_clinical_response(json.dumps(payload))


@pytest.mark.parametrize("field,value", [
    ("profesional_emisor", "not an object"),
    ("profesional_emisor", {"nombre": "Emisor ficticio"}),
    ("profesional_emisor", {"nombre": "Emisor ficticio", "matricula": None, "rol": "inventado"}),
    ("resultados_laboratorio", None),
    ("resultados_laboratorio", {}),
    ("resultados_laboratorio", [None]),
    ("resultados_laboratorio", [{"examen": "Examen", "valor": True, "unidad": None, "rango_referencia": None}]),
    ("resultados_laboratorio", [{"examen": "Examen", "valor": 0, "unidad": None, "rango_referencia": None}]),
    ("resultados_laboratorio", [{"examen": "Examen", "valor": "0", "unidad": False, "rango_referencia": None}]),
    ("resultados_laboratorio", [{"examen": "Examen", "unidad": None, "rango_referencia": None}]),
    ("resultados_laboratorio", [{"examen": "Examen", "valor": "", "unidad": None, "rango_referencia": None}]),
    ("resultados_laboratorio", [{"examen": "Examen", "valor": "0", "unidad": None, "rango_referencia": None, "extra": "no"}]),
    ("hallazgos", True), ("conclusion", []), ("procedimiento_solicitado", {}),
    ("indicacion_alta", 123), ("periodo_certificado", {"desde": "fecha inventada"}),
])
def test_present_new_fields_are_strictly_validated(field, value):
    payload = legacy_payload()
    payload["datos_extraidos"][field] = value
    with pytest.raises(LLMResponseError):
        validate_clinical_response(json.dumps(payload))


def test_every_laboratory_result_is_validated_not_only_first_element():
    payload = complete_payload("Informe de Laboratorio")
    payload["datos_extraidos"]["resultados_laboratorio"].append(
        {"examen": "Segundo examen", "valor": False, "unidad": None, "rango_referencia": None})
    with pytest.raises(LLMResponseError):
        validate_clinical_response(json.dumps(payload))


def test_unknown_extraction_property_is_not_silently_accepted():
    payload = legacy_payload()
    payload["datos_extraidos"]["campo_inventado"] = "no permitido"
    with pytest.raises(LLMResponseError):
        validate_clinical_response(json.dumps(payload))


def test_generation_requests_complete_schema_and_compatibility_is_read_only():
    generated = clinical_output_schema()
    data_schema = generated["$defs"]["DatosExtraidosSchema"]
    assert set(data_schema["required"]) == set(data_schema["properties"])
    assert DOCUMENTARY_EXTENSION_FIELDS <= set(data_schema["required"])
    assert not data_schema["additionalProperties"]
    lab_schema = generated["$defs"]["ResultadoLaboratorioSchema"]
    assert set(lab_schema["required"]) == {"examen", "valor", "unidad", "rango_referencia"}
    compatible = clinical_validation_schema()["$defs"]["DatosExtraidosSchema"]
    assert set(compatible["required"]) == set(data_schema["required"]) - DOCUMENTARY_EXTENSION_FIELDS
    assert clinical_output_schema() == generated


def test_new_api_model_requires_real_result_content_and_forbids_unknown_result_fields():
    with pytest.raises(ValidationError):
        DatosExtraidosSchema.model_validate({"resultados_laboratorio": [{"examen": "Examen"}]})
    with pytest.raises(ValidationError):
        DatosExtraidosSchema.model_validate({"resultados_laboratorio": [{"examen": "Examen", "valor": "0", "extra": "no"}]})
