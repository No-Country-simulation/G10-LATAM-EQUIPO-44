"""S3-01.3: evaluación paralela sin alterar contrato JSON oficial."""
from __future__ import annotations
from copy import deepcopy
from typing import Any
# Agregado por Edil: permitir import desde el paquete y desde scripts existentes.
# from urgency_detector import detect_urgency
if __package__:
    from .urgency_detector import detect_urgency
else:
    from urgency_detector import detect_urgency


def evaluate_analysis(analysis: dict[str, Any], *, source_text: str | None = None) -> dict[str, Any]:
    """Retorna informe independiente; no modifica analysis ni sus rutas.

    source_text debe proceder del texto extraído del documento original, no del
    JSON del LLM. La ausencia de texto limita la detección a los campos
    estructurados extraídos; no demuestra cobertura completa del documento.
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
    # Agregado por Edil: los nuevos campos pueden contener señales ya cubiertas
    # por el catálogo. Evaluarlos evita aceptar un informe completo ignorando
    # su conclusión, sin añadir reglas clínicas ni serializar metadatos del LLM.
    fragments = [extracted.get(field) for field in (
        'hallazgos', 'conclusion', 'procedimiento_solicitado',
        'indicacion_solicitud', 'resumen_evolucion', 'indicacion_alta',
        'destino_alta', 'seguimiento', 'contenido_certificacion',
    )]
    results = extracted.get('resultados_laboratorio')
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict):
                fragments.extend([item.get('examen'), item.get('valor')])
    payload['observaciones'] = '\n'.join(value for value in fragments if isinstance(value, str) and value.strip())
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
