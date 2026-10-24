"""Agregado por Edil: mínimos documentales versionados del MVP.

La fórmula de confianza y el detector de urgencia se conservan separados.
El snapshot previo se utiliza únicamente para la demo sintética existente.
"""
from __future__ import annotations

import json
import re
import unicodedata
from enum import Enum
from pathlib import Path

from .score_confianza import evaluar_confianza_con_dosis

RULES_ROOT = Path(__file__).parent / "rules"
LEGACY_DEMO_PROFILES = RULES_ROOT / "confidence_profiles_legacy_demo_v1.json"


def _valid_path(value):
    return isinstance(value, str) and bool(re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(?:\[\])?(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[\])?)*", value
    )) and not value.endswith("[]")


class EstadoCriterio(str, Enum):
    PRESENTE = "PRESENTE"
    AUSENTE = "AUSENTE"
    NO_APLICABLE = "NO_APLICABLE"
    NO_VERIFICABLE = "NO_VERIFICABLE"


def normalizar_tipo(value):
    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())


def cargar_perfiles(path=None):
    config = json.loads(Path(path or RULES_ROOT / "confidence_profiles_mvp.json").read_text(encoding="utf-8"))
    index = {}
    if not config.get("version") or not config.get("profiles"):
        raise ValueError("Configuración de confianza vacía")
    for profile in config["profiles"]:
        ids = set()
        for rule in profile["criteria"]:
            if rule["id"] in ids:
                raise ValueError("Criterio duplicado")
            ids.add(rule["id"])
            for flag in ("required", "applicable", "verifiable"):
                if not isinstance(rule[flag], bool):
                    raise ValueError("Indicador de criterio inválido")
            # Agregado por Edil: una alternativa OR es configuración explícita,
            # no una sustitución de diagnóstico por hallazgos en el código.
            alternatives = rule.get("any_of_paths")
            if alternatives is not None:
                if (rule.get("path") is not None or not isinstance(alternatives, list)
                        or len(alternatives) < 2 or any(not _valid_path(p) for p in alternatives)
                        or len(set(alternatives)) != len(alternatives)):
                    raise ValueError("Alternativas de criterio inválidas")
            elif rule["applicable"] and rule["verifiable"] and not _valid_path(rule.get("path")):
                raise ValueError("Criterio verificable sin ruta válida")
        for alias in [profile["name"], *profile["aliases"]]:
            key = normalizar_tipo(alias)
            if not key or key in index:
                raise ValueError("Alias vacío o ambiguo")
            index[key] = profile
    return config["version"], index


def _presence(value):
    if isinstance(value, str):
        normalized = normalizar_tipo(value)
        if normalized == "illegible":
            return EstadoCriterio.NO_VERIFICABLE
        # Agregado por Edil: un marcador textual de ausencia no demuestra un
        # dato extraído. Comparar el valor completo evita confundir resultados
        # válidos como "Negativo", "No reactivo", "0" o el examen "Na".
        if normalized in {"", "null", "none", "n/a", "n.a.", "no aplica",
                          "no disponible", "no consta", "sin datos", "sin informacion"}:
            return EstadoCriterio.AUSENTE
        return EstadoCriterio.PRESENTE
    return EstadoCriterio.AUSENTE


def _all_states(states):
    if EstadoCriterio.NO_VERIFICABLE in states:
        return EstadoCriterio.NO_VERIFICABLE
    return (EstadoCriterio.PRESENTE if states and all(s == EstadoCriterio.PRESENTE for s in states)
            else EstadoCriterio.AUSENTE)


def _path_presence(datos, path):
    parts = path.split(".")

    def visit(value, position):
        if position == len(parts):
            return _presence(value)
        if not isinstance(value, dict):
            return EstadoCriterio.AUSENTE
        part = parts[position]
        if part.endswith("[]"):
            values = value.get(part[:-2])
            if not isinstance(values, list) or not values:
                return EstadoCriterio.AUSENTE
            # Cada resultado necesita su examen y su valor; nunca all([]).
            return _all_states([visit(item, position + 1) for item in values])
        return visit(value.get(part), position + 1)

    return visit(datos, 0)


def evaluar_criterio(datos, rule):
    if not rule["applicable"]:
        return EstadoCriterio.NO_APLICABLE
    if not rule["verifiable"]:
        return EstadoCriterio.NO_VERIFICABLE
    if rule.get("any_of_paths") is not None:
        states = [_path_presence(datos, path) for path in rule["any_of_paths"]]
        # Agregado por Edil: un texto legible no elimina otro esencial marcado
        # ilegible. La regla OR solo resuelve ausencias, nunca borra esa señal.
        if EstadoCriterio.NO_VERIFICABLE in states:
            return EstadoCriterio.NO_VERIFICABLE
        return EstadoCriterio.PRESENTE if EstadoCriterio.PRESENTE in states else EstadoCriterio.AUSENTE
    return _path_presence(datos, rule["path"])


def evaluar_documento(documento, *, configuracion=None):
    version, profiles = configuracion if configuracion is not None else cargar_perfiles()
    classification = documento.get("clasificacion") or {}
    datos = documento.get("datos_extraidos") or {}
    profile = profiles.get(normalizar_tipo(classification.get("tipo_documento")))
    states = {"tipo_registrado": EstadoCriterio.PRESENTE if profile else EstadoCriterio.AUSENTE}
    evaluated = [bool(profile)]
    blockers = [] if profile else ["tipo_registrado"]
    if profile:
        for rule in profile["criteria"]:
            state = evaluar_criterio(datos, rule)
            states[rule["id"]] = state
            if rule["required"] and state != EstadoCriterio.NO_APLICABLE:
                evaluated.append(state == EstadoCriterio.PRESENTE)
                if state != EstadoCriterio.PRESENTE:
                    blockers.append(rule["id"])
    doses = [item.get("dosis") for item in (datos.get("medicamentos_recetados") or []) if isinstance(item, dict)]
    result = evaluar_confianza_con_dosis(
        classification.get("score_confianza_clasificacion", 0.0), evaluated, doses,
    )
    # Bloqueo documental independiente: no convertir ausencias en alertas clínicas.
    result["es_ambiguo"] = bool(blockers) or result["es_ambiguo"]
    return dict(result, perfil=profile["name"] if profile else None, version=version,
                estados=states, bloqueos=blockers)
