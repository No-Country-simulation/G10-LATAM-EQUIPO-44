"""Agregado por Edil: regresiones detectadas al integrar las ramas del equipo."""
import pytest
from mediflow.data_ai.score_confianza import evaluar_confianza, calcular_score_operativo, es_ambiguo
from mediflow.data_ai.urgency_detector import detect_urgency
from mediflow.data_ai.urgency_json_adapter import evaluate_analysis


def test_detector_uses_catalog_from_repository_without_override():
    result = detect_urgency("Control de rutina sin hallazgos nuevos.")
    assert result["clinical_alert"] == "none_detected"


def test_adapter_can_be_imported_as_package():
    result = evaluate_analysis({"datos_extraidos": {}}, source_text="Control de rutina.")
    assert result["integration_policy"] == "advisory_only_no_automatic_downgrade_or_reroute"


def test_critical_alert_requires_review_even_at_zero_threshold():
    result = evaluar_confianza(0.95, [True], True, 0.0)
    assert result["score_operativo"] == 0.0
    assert result["es_ambiguo"] is True


@pytest.mark.parametrize("classification,completeness", [(True, 1.0), (0.9, False)])
def test_boolean_scores_are_rejected(classification, completeness):
    with pytest.raises(TypeError):
        calcular_score_operativo(classification, completeness, False)


def test_boolean_threshold_is_rejected():
    with pytest.raises(TypeError):
        es_ambiguo(0.9, True)
