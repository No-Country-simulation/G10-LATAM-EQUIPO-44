from mediflow.data_ai.score_confianza import (
    calcular_completitud,
    calcular_score_operativo,
    detectar_alerta_dosis_ilegible,
    es_ambiguo,
    evaluar_confianza,
    evaluar_confianza_con_dosis,
)


def test_score_001_documento_confiable():
    resultado = calcular_score_operativo(
        score_clasificacion=0.95,
        completitud=0.90,
        alerta_critica=False,
    )

    assert resultado == 0.90


def test_score_002_completitud_limita_score():
    resultado = calcular_score_operativo(
        score_clasificacion=0.95,
        completitud=0.40,
        alerta_critica=False,
    )

    assert resultado == 0.40


def test_score_003_alerta_critica_domina():
    resultado = calcular_score_operativo(
        score_clasificacion=0.95,
        completitud=0.95,
        alerta_critica=True,
    )

    assert resultado == 0.0


def test_score_004_detecta_ambiguo_segun_umbral():
    resultado = es_ambiguo(
        score_operativo=0.55,
        umbral=0.60,
    )

    assert resultado is True

def test_score_005_completitud_total():
    resultado = calcular_completitud(
        [True, True, True, True]
    )

    assert resultado == 1.0


def test_score_006_completitud_parcial():
    resultado = calcular_completitud(
        [True, True, False, True]
    )

    assert resultado == 0.75


def test_score_007_completitud_sin_criterios():
    import pytest

    with pytest.raises(ValueError):
        calcular_completitud([])


def test_score_008_completitud_rechaza_tipo_incorrecto():
    import pytest

    with pytest.raises(TypeError):
        calcular_completitud(
            [True, True, "si"]
        )

UMBRAL_PRUEBA = 0.60


def test_score_009_caso_normal_no_es_ambiguo():
    completitud = calcular_completitud(
        [True, True, True, True]
    )

    score = calcular_score_operativo(
        score_clasificacion=0.95,
        completitud=completitud,
        alerta_critica=False,
    )

    assert score == 0.95
    assert es_ambiguo(score, UMBRAL_PRUEBA) is False


def test_score_010_caso_ambiguo_por_alerta_critica():
    completitud = calcular_completitud(
        [True, True, True, False]
    )

    score = calcular_score_operativo(
        score_clasificacion=0.95,
        completitud=completitud,
        alerta_critica=True,
    )

    assert score == 0.0
    assert es_ambiguo(score, UMBRAL_PRUEBA) is True


def test_score_011_urgente_no_significa_ambiguo():
    completitud = calcular_completitud(
        [True, True, True, True]
    )

    score = calcular_score_operativo(
        score_clasificacion=0.90,
        completitud=completitud,
        alerta_critica=False,
    )

    assert score == 0.90
    assert es_ambiguo(score, UMBRAL_PRUEBA) is False

def test_score_012_evaluacion_completa_confiable():
    resultado = evaluar_confianza(
        score_clasificacion=0.90,
        criterios_cumplidos=[True, True, True, True],
        alerta_critica=False,
        umbral=UMBRAL_PRUEBA,
    )

    assert resultado["completitud"] == 1.0
    assert resultado["score_operativo"] == 0.90
    assert resultado["es_ambiguo"] is False


def test_score_013_evaluacion_completa_ambigua():
    resultado = evaluar_confianza(
        score_clasificacion=0.95,
        criterios_cumplidos=[True, True, True, False],
        alerta_critica=True,
        umbral=UMBRAL_PRUEBA,
    )

    assert resultado["completitud"] == 0.75
    assert resultado["score_operativo"] == 0.0
    assert resultado["es_ambiguo"] is True

def test_score_014_score_igual_al_umbral_no_es_ambiguo():
    resultado = es_ambiguo(
        score_operativo=0.60,
        umbral=0.60,
    )

    assert resultado is False


def test_score_015_score_apenas_debajo_es_ambiguo():
    resultado = es_ambiguo(
        score_operativo=0.599,
        umbral=0.60,
    )

    assert resultado is True

def test_score_016_detecta_dosis_ilegible():
    resultado = detectar_alerta_dosis_ilegible(
        ["500 mg", "ILLEGIBLE"]
    )

    assert resultado is True


def test_score_017_dosis_legibles_no_generan_alerta():
    resultado = detectar_alerta_dosis_ilegible(
        ["500 mg", "10 ml"]
    )

    assert resultado is False


def test_score_018_dosis_ausente_no_equivale_a_ilegible():
    resultado = detectar_alerta_dosis_ilegible(
        [None]
    )

    assert resultado is False
def test_score_019_respuesta_mediflow_dosis_ilegible_es_ambigua():
    respuesta_llm = {
        "clasificacion": {
            "tipo_documento": "Receta Medica",
            "score_confianza_clasificacion": 0.95,
        },
        "datos_extraidos": {
            "medicamentos_recetados": [
                {
                    "medicamento": "Amoxicilina",
                    "dosis": "ILLEGIBLE",
                }
            ]
        },
    }

    dosis = [
        item["dosis"]
        for item in respuesta_llm["datos_extraidos"]["medicamentos_recetados"]
    ]

    resultado = evaluar_confianza_con_dosis(
        score_clasificacion=respuesta_llm["clasificacion"][
            "score_confianza_clasificacion"
        ],
        criterios_cumplidos=[True, True, True, False],
        dosis_medicamentos=dosis,
        umbral=UMBRAL_PRUEBA,
    )

    assert resultado["score_operativo"] == 0.0
    assert resultado["es_ambiguo"] is True


def test_score_020_respuesta_mediflow_dosis_legible_no_es_ambigua():
    respuesta_llm = {
        "clasificacion": {
            "tipo_documento": "Receta Medica",
            "score_confianza_clasificacion": 0.95,
        },
        "datos_extraidos": {
            "medicamentos_recetados": [
                {
                    "medicamento": "Amoxicilina",
                    "dosis": "500 mg",
                }
            ]
        },
    }

    dosis = [
        item["dosis"]
        for item in respuesta_llm["datos_extraidos"]["medicamentos_recetados"]
    ]

    resultado = evaluar_confianza_con_dosis(
        score_clasificacion=respuesta_llm["clasificacion"][
            "score_confianza_clasificacion"
        ],
        criterios_cumplidos=[True, True, True, True],
        dosis_medicamentos=dosis,
        umbral=UMBRAL_PRUEBA,
    )

    assert resultado["score_operativo"] == 0.95
    assert resultado["es_ambiguo"] is False