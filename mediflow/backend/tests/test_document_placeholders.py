"""Agregado por Edil: marcadores de ausencia no completan mínimos documentales."""
import pytest

from data_ai.confidence_profiles import evaluar_documento
from app.services.servicio_orquestador import procesar_con_orquestador
from test_document_minimums import KINDS, complete_document


@pytest.mark.parametrize('placeholder', ['null', 'None', ' N/A ', 'No aplica', 'No disponible', 'No consta', 'Sin datos', 'Sin información'])
@pytest.mark.parametrize('kind', KINDS)
def test_placeholder_patient_blocks_all_types(kind, placeholder, monkeypatch):
    monkeypatch.setenv('TRIAGE_RULES_PROFILE', 'general')
    data = complete_document(kind)
    data['datos_extraidos']['paciente']['nombre'] = placeholder
    assert evaluar_documento(data)['es_ambiguo'] is True
    assert procesar_con_orquestador(data)['status'] == 'auditoria_humana'


@pytest.mark.parametrize('value', ['0', 'Negativo', 'No reactivo', 'Sin alteraciones', 'Na'])
def test_valid_literal_lab_values_remain_usable(value):
    data = complete_document(KINDS[1])
    data['datos_extraidos']['resultados_laboratorio'][0]['valor'] = value
    assert evaluar_documento(data)['es_ambiguo'] is False


def test_placeholder_in_one_lab_result_is_not_hidden_by_another_result():
    data = complete_document(KINDS[1])
    data['datos_extraidos']['resultados_laboratorio'].append({'examen': 'Segundo examen', 'valor': 'N/A'})
    assert evaluar_documento(data)['es_ambiguo'] is True
