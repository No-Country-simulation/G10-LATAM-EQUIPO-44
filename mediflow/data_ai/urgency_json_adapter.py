"""S3-01.3: evaluación paralela sin alterar contrato JSON oficial."""
from __future__ import annotations
from copy import deepcopy
from typing import Any
from data_ai.urgency_detector import detect_urgency


def evaluate_analysis(analysis: dict[str, Any], *, source_text: str | None = None) -> dict[str, Any]:
    """Retorna informe independiente; no modifica analysis ni sus rutas.

    source_text debe proceder del texto extraído del documento original, no del
    JSON del LLM. La ausencia de texto limita la detección a diagnóstico/CIE10.
    """
    if not isinstance(analysis, dict):
        raise TypeError('analysis debe ser dict')
    extracted = analysis.get('datos_extraidos') or {}
    if not isinstance(extracted, dict):
        raise ValueError('datos_extraidos debe ser objeto')
    payload = {
        'diagnostico_principal': extracted.get('diagnostico_principal'),
        'cie10_sugerido': extracted.get('cie10_sugerido'),
    }
    if source_text is not None:
        if not isinstance(source_text, str):
            raise TypeError('source_text debe ser str')
        payload['texto_extraido'] = source_text
    result = detect_urgency(payload)
    result['input_coverage'] = 'full_text_and_structured' if source_text is not None else 'structured_only'
    result['review_recommended'] = (result['requires_human_review'] or source_text is None)
    result['suggested_priority'] = ('Urgente' if result['clinical_alert'] != 'none_detected' or
                                    result['document_priority'] == 'priority_review' else None)
    result['suggested_destination'] = ('Cola_Revision_Humana' if result['review_recommended'] else None)
    result['integration_policy'] = 'advisory_only_no_automatic_downgrade_or_reroute'
    return result


def make_sidecar(analysis: dict[str, Any], *, source_text: str | None = None) -> dict[str, Any]:
    """Envelope fuera del esquema Gemini: conservar analysis exactamente."""
    return {'analysis': deepcopy(analysis), 'urgency_assessment': evaluate_analysis(analysis, source_text=source_text)}
