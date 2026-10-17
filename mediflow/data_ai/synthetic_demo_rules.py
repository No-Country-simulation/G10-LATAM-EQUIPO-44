"""Reglas YA existentes del dataset, solo para la demo sintética opt-in.

No son criterios clínicos validados. No ampliar este perfil a datos reales.
"""

import json
import os
from pathlib import Path
import re

from .urgency_detector import _context, load_catalog, normalize

POLICY = Path(__file__).resolve().parent / "rules/triage_rules_v1.json"
RULE_IDS = {
    "hiperglicemia_marcada", "hallazgo_radiologico_sospechoso",
    "lesion_por_presion_estadio_4", "pie_diabetico_wagner_3",
}


def rules_profile() -> str:
    # Agregado por Edil: activación por entorno del servidor, nunca por nombre
    # de archivo, ID, etiqueta del CSV o instrucciones del documento.
    profile = os.environ.get("TRIAGE_RULES_PROFILE", "general").strip()
    if profile not in {"general", "synthetic_demo_v1"}:
        raise ValueError("Perfil de reglas no reconocido.")
    return profile


def evaluate_synthetic_demo(source_text: str | None) -> dict:
    with POLICY.open(encoding="utf-8") as handle:
        policy = json.load(handle)
    defined = {rule["id"] for rule in policy["rules"] if rule["scenario"] == "URG"}
    if policy["version"] != "1.2-dataset-sintetico" or defined != RULE_IDS:
        raise ValueError("La política experimental requiere revisión de compatibilidad.")
    result = {"profile": "synthetic_demo_v1", "policy_version": policy["version"],
              "matched_rules": [], "suggested_priority": None}
    if source_text is None:
        return result
    if not isinstance(source_text, str):
        raise TypeError("La evidencia de texto debe ser una cadena.")
    catalog = load_catalog()
    sentences = re.split(r"\.(?!\d)|[;!?]", normalize(source_text))
    matches = set()
    spiculated_lung = False
    suspected_lung_neoplasia = False

    def positive(sentence, match):
        if match is None:
            return False
        # Agregado por Edil: negar el hallazgo o un modificador no es una
        # coincidencia positiva. Alcance inmediato, sin anular otra oración
        # por un "no" sobre derrame pleural u otro hallazgo independiente.
        before = sentence[max(0, match.start() - 70):match.start()]
        if re.search(r"\b(?:no|sin)\s*$|\bno\s+(?:se\s+)?(?:observa(?:n)?|identifica(?:n)?|confirma|presenta|hay|evidencia)\s*$", before):
            return False
        return _context(sentence, match.group(), catalog) in {"affirmed", "suspected"}

    for sentence in sentences:
        # Agregado por Edil: condición exacta del dataset (250), no un nuevo
        # umbral clínico >=250 ni una regla para cualquier valor fuera de rango.
        glucose = re.search(r"\b(?:glicemia|glucosa)\s+en\s+ayunas\s*(?::\s*)?(?:resultado\s*:\s*)?250(?:[.,]0+)?\s*mg\s*/\s*dl\b", sentence)
        if positive(sentence, glucose):
            matches.add("hiperglicemia_marcada")
        pressure = re.search(r"\blesion(?:es)?\s+por\s+presion(?:\s+[a-z]+){0,4}\s+estadio\s*(?:4|iv)\b", sentence)
        if positive(sentence, pressure):
            matches.add("lesion_por_presion_estadio_4")
        foot = re.search(r"\bpie\s+diabetico\b", sentence)
        wagner = re.search(r"\bwagner\s*(?:grado\s*)?3\b", sentence)
        ulcer = re.search(r"\bulcera\b", sentence)
        if positive(sentence, foot) and positive(sentence, wagner) and positive(sentence, ulcer):
            matches.add("pie_diabetico_wagner_3")
        lung = re.search(r"\blesion(?:es)?\s+pulmonar(?:es)?\b", sentence)
        spiculated = re.search(r"\bespiculad[oa]s?\b", sentence)
        suspicion = re.search(r"\b(?:sospechos[oa]s?|sugestiv[oa]s?|sugerentes?)\b", sentence)
        neoplasia = re.search(r"\bneoplasi(?:a|co|ca)s?\b", sentence)
        # La muestra tiene descripción y conclusión en oraciones distintas.
        # Exigir ambas evidencias; no transformar cualquier sospecha en urgencia.
        spiculated_lung |= positive(sentence, lung) and positive(sentence, spiculated)
        suspected_lung_neoplasia |= positive(sentence, lung) and positive(sentence, suspicion) and positive(sentence, neoplasia)
    if spiculated_lung and suspected_lung_neoplasia:
        matches.add("hallazgo_radiologico_sospechoso")
    result["matched_rules"] = sorted(matches)
    if matches:
        result["suggested_priority"] = "Urgente"
    # No decide auditoría, no borra alertas previas y no devuelve fragmentos
    # clínicos: el orquestador conserva las protecciones generales existentes.
    return result
