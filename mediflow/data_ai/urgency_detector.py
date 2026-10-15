"""MediFlow S3-01.2: detector experimental, NO apto para triaje autónomo."""
from __future__ import annotations
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

DEFAULT_CATALOG = Path(__file__).resolve().parent / 'urgency_catalog_v1_1.json'
CLINICAL_RANK = {'none_detected': 0, 'possible_urgent_assessment': 1, 'possible_emergency': 2}


def normalize(value: str) -> str:
    value = unicodedata.normalize('NFKD', str(value).lower())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', value).strip()


def load_catalog(path: str | Path = DEFAULT_CATALOG) -> dict[str, Any]:
    with Path(path).open(encoding='utf-8') as handle:
        catalog = json.load(handle)
    if not isinstance(catalog.get('clinical_rules'), list) or not isinstance(catalog.get('document_rules'), list):
        raise ValueError('Catálogo inválido: faltan listas clinical_rules/document_rules')
    return catalog


def _code_matches(code: str, prefix: str) -> bool:
    code, prefix = code.upper().replace(' ', ''), prefix.upper().replace(' ', '')
    if not re.fullmatch(r'[A-Z][0-9]{2}(?:\.[0-9A-Z]+)?', code):
        return False
    return code == prefix or code.startswith(prefix + '.') or ('.' in prefix and code.startswith(prefix))


def _extract_text(document: str | dict[str, Any]) -> str:
    if isinstance(document, str):
        return document
    if not isinstance(document, dict):
        raise TypeError('document debe ser str o dict')
    # Solo campos clínicos conocidos; evita analizar metadatos, IDs y campos de control.
    fields = ('texto', 'texto_extraido', 'contenido', 'diagnostico_principal', 'observaciones', 'hallazgos', 'resumen_clinico', 'motivo_consulta')
    return '\n'.join(str(document[k]) for k in fields if isinstance(document.get(k), str))


def _codes(document: str | dict[str, Any], explicit_codes: list[str] | None) -> list[str]:
    values = list(explicit_codes or [])
    if isinstance(document, dict):
        for key in ('cie10_sugerido', 'codigos_cie10', 'cie10'):
            raw = document.get(key)
            if isinstance(raw, str):
                values.append(raw)
            elif isinstance(raw, list):
                values.extend(x for x in raw if isinstance(x, str))
    return sorted({c.strip().upper() for c in values if isinstance(c, str) and c.strip()})


def _context(fragment: str, term: str, catalog: dict[str, Any]) -> str:
    """Heurística local conservadora; la revisión humana sigue siendo obligatoria."""
    normalized = normalize(fragment)
    idx = normalized.find(normalize(term))
    if idx < 0:
        return 'unknown'
    before = normalized[max(0, idx - 70):idx]
    # El contexto solo se busca en la cláusula local, nunca en todo el documento.
    before = re.split(r'[.;:\n]|\bpero\b|\bsin embargo\b', before)[-1]
    if any(re.search(r'\b' + re.escape(normalize(cue)) + r'\b', before) for cue in catalog['context_rules']['negation_cues']):
        return 'negated'
    if any(re.search(r'\b' + re.escape(normalize(cue)) + r'\b', before) for cue in catalog['context_rules']['historical_cues']):
        return 'historical'
    if any(re.search(r'\b' + re.escape(normalize(cue)) + r'\b', before) for cue in catalog['context_rules']['uncertainty_cues']):
        return 'suspected'
    return 'affirmed'


def detect_urgency(document: str | dict[str, Any], *, codes: list[str] | None = None,
                   catalog_path: str | Path = DEFAULT_CATALOG) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)
    raw = _extract_text(document)
    supplied_codes = _codes(document, codes)
    matches: list[dict[str, str]] = []
    seen = set()
    # Segmentar por oraciones / líneas para reducir interferencias entre cláusulas.
    fragments = [x.strip() for x in re.split(r'[\n.!?;]+', raw) if x.strip()]
    for dimension, rules in (('clinical', catalog['clinical_rules']), ('document', catalog['document_rules'])):
        for rule in rules:
            for term in rule.get('terms', []):
                pattern = r'(?<!\w)' + re.escape(normalize(term)) + r'(?!\w)'
                for fragment in fragments:
                    if not re.search(pattern, normalize(fragment)):
                        continue
                    status = _context(fragment, term, catalog)
                    key = (dimension, rule['id'], term, status, fragment)
                    if key not in seen:
                        seen.add(key)
                        matches.append({'dimension': dimension, 'rule_id': rule['id'], 'source': 'term',
                                        'signal': term, 'context': status, 'evidence': fragment[:240]})
            for code in supplied_codes:
                if any(_code_matches(code, prefix) for prefix in rule.get('icd10_prefixes', [])):
                    key = (dimension, rule['id'], 'code', code)
                    if key not in seen:
                        seen.add(key)
                        matches.append({'dimension': dimension, 'rule_id': rule['id'], 'source': 'icd10',
                                        'signal': code, 'context': 'unverified_temporality', 'evidence': code})

    active = [m for m in matches if m['context'] in ('affirmed', 'suspected')]
    code_only = [m for m in matches if m['source'] == 'icd10']
    historical = [m for m in matches if m['context'] == 'historical']
    clinical_candidates = {r['id']: r['candidate_alert'] for r in catalog['clinical_rules']}
    level = 'none_detected'
    for match in active:
        if match['dimension'] == 'clinical':
            candidate = clinical_candidates[match['rule_id']]
            if CLINICAL_RANK[candidate] > CLINICAL_RANK[level]:
                level = candidate
    document_priority = 'priority_review' if any(m['dimension'] == 'document' for m in active) or level != 'none_detected' else 'routine'
    # Códigos sin contexto y antecedentes históricos requieren revisión, no emergencia automática.
    requires_review = bool(active or code_only or historical)
    if document_priority == 'routine' and (code_only or historical):
        document_priority = 'indeterminate'
    return {
        'catalog_version': catalog['version'],
        'clinical_alert': level,
        'document_priority': document_priority,
        'requires_human_review': requires_review,
        'matches': matches,
        'limitations': ['Detector heurístico no validado clínicamente',
                        'CIE-10 aislado no demuestra urgencia actual',
                        'Ausencia de coincidencias no descarta riesgo'],
    }
