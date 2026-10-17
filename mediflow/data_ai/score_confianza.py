# Umbral operativo acordado para el MVP / Demo de MediFlow.
# Un valor mayor representa mayor confianza.
# Si el score operativo queda por debajo de este valor,
# el resultado se considera ambiguo por confianza.
UMBRAL_CONFIANZA_MVP = 0.70

# Agregado por Edil: un booleano no representa una confianza numérica.
# Python acepta True como 1; rechazarlo evita aceptar entradas mal tipadas.
def _validar_numero(valor, nombre):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise TypeError(f"{nombre} debe ser un número, no un booleano")


def calcular_completitud(
    criterios_cumplidos: list[bool],
) -> float:
    """
    Calcula la proporcion de criterios de completitud cumplidos.

    Ejemplo:
    [True, True, False, True] -> 0.75
    """

    if not criterios_cumplidos:
        raise ValueError(
            "Debe existir al menos un criterio de completitud"
        )

    if not all(
        isinstance(criterio, bool)
        for criterio in criterios_cumplidos
    ):
        raise TypeError(
            "Todos los criterios deben ser booleanos"
        )

    cantidad_cumplidos = sum(criterios_cumplidos)
    cantidad_total = len(criterios_cumplidos)

    return cantidad_cumplidos / cantidad_total


def calcular_score_operativo(
    score_clasificacion: float,
    completitud: float,
    alerta_critica: bool,
) -> float:
    """
    Calcula el score operativo de confianza de MediFlow.

    Reglas:
    - score_clasificacion debe estar entre 0.0 y 1.0.
    - completitud debe estar entre 0.0 y 1.0.
    - si existe una alerta critica, el score operativo es 0.0.
    - en caso contrario, se utiliza el menor valor entre
      score_clasificacion y completitud.
    """

    _validar_numero(score_clasificacion, "score_clasificacion")
    _validar_numero(completitud, "completitud")
    if not 0.0 <= score_clasificacion <= 1.0:
        raise ValueError(
            "score_clasificacion debe estar entre 0.0 y 1.0"
        )

    if not 0.0 <= completitud <= 1.0:
        raise ValueError(
            "completitud debe estar entre 0.0 y 1.0"
        )

    if not isinstance(alerta_critica, bool):
        raise TypeError(
            "alerta_critica debe ser un booleano"
        )

    if alerta_critica:
        return 0.0

    return min(score_clasificacion, completitud)


def es_ambiguo(
    score_operativo: float,
    umbral: float = UMBRAL_CONFIANZA_MVP,
) -> bool:
    """
    Determina si un resultado debe considerarse ambiguo.

    Un resultado es ambiguo cuando su score operativo
    queda por debajo del umbral configurado.
    """

    _validar_numero(score_operativo, "score_operativo")
    _validar_numero(umbral, "umbral")
    if not 0.0 <= score_operativo <= 1.0:
        raise ValueError(
            "score_operativo debe estar entre 0.0 y 1.0"
        )

    if not 0.0 <= umbral <= 1.0:
        raise ValueError(
            "umbral debe estar entre 0.0 y 1.0"
        )

    return score_operativo < umbral

def evaluar_confianza(
    score_clasificacion: float,
    criterios_cumplidos: list[bool],
    alerta_critica: bool,
    umbral: float = UMBRAL_CONFIANZA_MVP,
) -> dict:
    """
    Ejecuta el flujo completo del modelo de confianza.

    Devuelve:
    - completitud
    - score_operativo
    - es_ambiguo
    """

    completitud = calcular_completitud(
        criterios_cumplidos
    )

    score_operativo = calcular_score_operativo(
        score_clasificacion=score_clasificacion,
        completitud=completitud,
        alerta_critica=alerta_critica,
    )

    # Agregado por Edil: conservar el cálculo original y validar siempre el umbral.
    # Una alerta crítica obliga a revisión incluso cuando el umbral sea cero.
    # Antes solo se devolvía el resultado de es_ambiguo(score_operativo, umbral).
    resultado_ambiguo = es_ambiguo(
        score_operativo=score_operativo,
        umbral=umbral,
    )
    resultado_ambiguo = alerta_critica or resultado_ambiguo

    return {
        "completitud": completitud,
        "score_operativo": score_operativo,
        "es_ambiguo": resultado_ambiguo,
    }

def detectar_alerta_dosis_ilegible(
    dosis_medicamentos: list[str | None],
) -> bool:
    """
    Detecta si existe al menos una dosis marcada explícitamente
    como ilegible.

    Esta señal puede utilizarse como alerta critica objetiva.
    """

    return any(
        dosis == "ILLEGIBLE"
        for dosis in dosis_medicamentos
    )

def evaluar_confianza_con_dosis(
    score_clasificacion: float,
    criterios_cumplidos: list[bool],
    dosis_medicamentos: list[str | None],
    umbral: float = UMBRAL_CONFIANZA_MVP,
) -> dict:
    """
    Evalua la confianza incorporando como alerta critica
    la presencia de una dosis explicitamente ilegible.
    """

    alerta_critica = detectar_alerta_dosis_ilegible(
        dosis_medicamentos
    )

    return evaluar_confianza(
        score_clasificacion=score_clasificacion,
        criterios_cumplidos=criterios_cumplidos,
        alerta_critica=alerta_critica,
        umbral=umbral,
    )
