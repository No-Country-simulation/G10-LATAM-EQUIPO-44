"""Agregado por Edil: campos nuevos alimentan el detector existente, sin nube."""
from copy import deepcopy

import pytest

from data_ai.urgency_json_adapter import evaluate_analysis
from app.services.servicio_orquestador import procesar_con_orquestador
from test_orquestador_integration import document


@pytest.mark.parametrize('field', [
    'hallazgos', 'conclusion', 'procedimiento_solicitado',
    'indicacion_solicitud', 'resumen_evolucion', 'indicacion_alta',
    'destino_alta', 'seguimiento', 'contenido_certificacion',
])
def test_new_documentary_text_does_not_hide_existing_urgency(field, monkeypatch):
    monkeypatch.setenv('TRIAGE_RULES_PROFILE', 'general')
    data = document()
    data['datos_extraidos'][field] = 'dolor toracico opresivo actual'
    original = deepcopy(data)
    result = procesar_con_orquestador(data)
    assert result['clasificacion']['nivel_prioridad'] == 'Urgente'
    assert result['status'] == 'auditoria_humana'
    assert result['decision_enrutamiento']['requiere_auditoria_humana'] is True
    assert data == original


def test_lab_textual_result_uses_catalog_without_new_numeric_thresholds():
    result = evaluate_analysis({'datos_extraidos': {
        'resultados_laboratorio': [{'examen': 'Texto de ejemplo', 'valor': 'dolor toracico opresivo actual'}],
    }})
    assert result['suggested_priority'] == 'Urgente'
    assert result['requires_human_review'] is True


def test_issuer_name_is_not_used_as_clinical_evidence():
    result = evaluate_analysis({'datos_extraidos': {
        'profesional_emisor': {'nombre': 'dolor toracico opresivo actual', 'matricula': None},
    }})
    assert result['suggested_priority'] is None
    assert result['requires_human_review'] is False


def test_negated_conclusion_does_not_create_a_new_urgency_rule():
    result = evaluate_analysis({'datos_extraidos': {'conclusion': 'Sin dolor toracico opresivo.'}})
    assert result['suggested_priority'] is None
    assert result['requires_human_review'] is False
