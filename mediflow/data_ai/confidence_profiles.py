"""Perfiles internos provisionales del MVP; no amplían el contrato público."""
from __future__ import annotations

import json
import unicodedata
from enum import Enum
from pathlib import Path

from .score_confianza import evaluar_confianza_con_dosis


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
    config = json.loads(Path(path or Path(__file__).parent / "rules/confidence_profiles_mvp.json").read_text(encoding="utf-8"))
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
            if rule["applicable"] and rule["verifiable"] and not rule.get("path"):
                raise ValueError("Criterio verificable sin ruta")
        for alias in [profile["name"], *profile["aliases"]]:
            key = normalizar_tipo(alias)
            if not key or key in index:
                raise ValueError("Alias vacío o ambiguo")
            index[key] = profile
    return config["version"], index


def _presence(value):
    if value == "ILLEGIBLE":
        return EstadoCriterio.NO_VERIFICABLE
    if isinstance(value, str) and value.strip():
        return EstadoCriterio.PRESENTE
    return EstadoCriterio.AUSENTE


def evaluar_criterio(datos, rule):
    if not rule["applicable"]:
        return EstadoCriterio.NO_APLICABLE
    if not rule["verifiable"]:
        return EstadoCriterio.NO_VERIFICABLE
    path = rule["path"]
    if "[]." in path:
        field, leaf = path.split("[].")
        values = datos.get(field)
        if not isinstance(values, list) or not values:
            return EstadoCriterio.AUSENTE
        states = [_presence(item.get(leaf)) if isinstance(item, dict) else EstadoCriterio.AUSENTE for item in values]
        # Cada elemento debe ser usable; all([]) nunca aprueba una receta vacía.
        if EstadoCriterio.NO_VERIFICABLE in states:
            return EstadoCriterio.NO_VERIFICABLE
        return EstadoCriterio.PRESENTE if all(s == EstadoCriterio.PRESENTE for s in states) else EstadoCriterio.AUSENTE
    value = datos
    for part in path.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return _presence(value)


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
