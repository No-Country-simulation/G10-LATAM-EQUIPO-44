"""Agregado por Edil: comprobar que el evaluador no aprueba resultados incorrectos."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validate_dataset_pipeline import compare_result, load_cases, main


def response():
    return {
        "documento_id": "DOC-SYNTHETIC", "status": "procesado",
        "clasificacion": {"tipo_documento": "Informe", "nivel_prioridad": "Urgente", "score_confianza_clasificacion": 0.9},
        "datos_extraidos": {},
        "decision_enrutamiento": {"destino_principal": "Cola_Emergencia_Medica", "requiere_auditoria_humana": False, "justificacion_enrutamiento": "Prueba ficticia."},
        "almacenamiento_oci": {"bucket": "procesados", "ruta_objeto": "synthetic.txt", "status_backup": "exito"},
    }


EXPECTED = {"priority": "Urgente", "destination": "Cola_Emergencia_Medica", "human_review": False, "status": "procesado"}


def test_exact_dataset_inventory_and_formats():
    cases = load_cases()
    assert len(cases) == 9
    assert {case["case_id"] for case in cases} == {"MF_001", "MF_004", "MF_005", "MF_006", "MF_007", "MF_008", "MF_009", "MF_011", "MF_012"}
    assert sorted(case["file"].suffix for case in cases) == [".jpg"] * 2 + [".pdf"] * 5 + [".txt"] * 2


def test_valid_urgent_case_matches():
    assert compare_result(EXPECTED, response())["matches_dataset"]


@pytest.mark.parametrize("field,value", [("priority", "Rutina"), ("destination", "Cola_Historia_Clinica"), ("human_review", True)])
def test_mismatch_cannot_pass_by_having_http_201(field, value):
    expected = copy.deepcopy(EXPECTED)
    expected[field] = value
    result = compare_result(expected, response())
    assert not result["matches_dataset"]
    assert not result["comparisons"][field]


def test_wrong_storage_and_contradictory_review_are_technical_failures():
    payload = response()
    payload["almacenamiento_oci"]["bucket"] = "recibidos"
    payload["decision_enrutamiento"]["requiere_auditoria_humana"] = True
    result = compare_result(EXPECTED, payload)
    assert not result["coherent_routing"]
    assert not result["final_storage_declared"]


def test_invalid_json_cannot_be_accepted():
    with pytest.raises(ValueError):
        compare_result(EXPECTED, {})


def test_cloud_is_disabled_by_default_and_inventory_needs_no_network():
    assert main([]) == 2
    assert main(["--check-only"]) == 0


def test_selecting_one_case_does_not_plan_a_second_dataset_run(capsys):
    assert main(["--check-only", "--case", "MF_001"]) == 0
    inventory = json.loads(capsys.readouterr().out)
    assert inventory["cases"] == 1
    assert inventory["formats"] == {".txt": 0, ".pdf": 1, ".jpg": 0}
