import pytest

from app.services.servicio_orquestador import procesar_con_orquestador
from data_ai.confidence_profiles import EstadoCriterio as E, evaluar_documento
from test_orquestador_integration import document


def test_s4_demo_receta_completa_confianza_suficiente(monkeypatch):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "general")

    doc = document(score=0.95)

    evaluacion = evaluar_documento(doc)

    assert evaluacion["estados"]["paciente"] == E.PRESENTE
    assert evaluacion["estados"]["medicamentos"] == E.PRESENTE
    assert evaluacion["estados"]["profesional"] == E.PRESENTE
    assert evaluacion["estados"]["diagnostico"] == E.NO_APLICABLE

    assert evaluacion["completitud"] == 1.0
    assert evaluacion["score_operativo"] == 0.95
    assert evaluacion["es_ambiguo"] is False

    resultado = procesar_con_orquestador(
        doc,
        source_text="Receta médica sintética de prueba con datos legibles.",
    )

    assert resultado["status"] == "procesado"
    assert resultado["decision_enrutamiento"]["requiere_auditoria_humana"] is False
    assert resultado["decision_enrutamiento"]["destino_principal"] == "Cola_Farmacia"


def test_s4_demo_receta_dosis_ilegible_es_ambigua(monkeypatch):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "general")

    doc = document(score=0.95)
    doc["datos_extraidos"]["medicamentos_recetados"][0]["dosis"] = "ILLEGIBLE"

    evaluacion = evaluar_documento(doc)

    assert evaluacion["score_operativo"] == 0.0
    assert evaluacion["es_ambiguo"] is True

    resultado = procesar_con_orquestador(
        doc,
        source_text="Receta médica sintética con una dosis ilegible.",
    )

    assert resultado["status"] == "auditoria_humana"
    assert resultado["decision_enrutamiento"]["requiere_auditoria_humana"] is True
    assert resultado["decision_enrutamiento"]["destino_principal"] == "Cola_Revision_Humana"

    import pytest


@pytest.mark.parametrize(
    "tipo, estados_esperados",
    [
        (
            "Receta Médica",
            {
                "paciente": E.PRESENTE,
                "medicamentos": E.PRESENTE,
                "profesional": E.PRESENTE,
                "diagnostico": E.NO_APLICABLE,
            },
        ),
        (
            "Informe de Laboratorio",
            {
                "paciente": E.PRESENTE,
                "estudio": E.PRESENTE,
                "diagnostico": E.NO_APLICABLE,
                "resultados_unidades_rangos_fecha": E.NO_VERIFICABLE,
            },
        ),
        (
            "Informe de Estudio por Imágenes",
            {
                "paciente": E.PRESENTE,
                "estudio": E.PRESENTE,
                "diagnostico": E.NO_APLICABLE,
                "hallazgos_conclusion": E.NO_VERIFICABLE,
            },
        ),
        (
            "Orden / Solicitud de Procedimiento",
            {
                "paciente": E.PRESENTE,
                "diagnostico": E.NO_APLICABLE,
                "procedimiento_solicitado_indicacion": E.NO_VERIFICABLE,
            },
        ),
        (
            "Epicrisis / Informe de Alta",
            {
                "paciente": E.PRESENTE,
                "diagnostico": E.NO_APLICABLE,
                "evolucion_alta_seguimiento": E.NO_VERIFICABLE,
            },
        ),
        (
            "Certificado Médico",
            {
                "paciente": E.PRESENTE,
                "profesional": E.PRESENTE,
                "diagnostico": E.NO_APLICABLE,
                "motivo_periodo_firma": E.NO_VERIFICABLE,
            },
        ),
    ],
)
def test_s4_matriz_estados_por_tipo_documental(tipo, estados_esperados):
    doc = document(score=0.95)
    doc["clasificacion"]["tipo_documento"] = tipo

    evaluacion = evaluar_documento(doc)

    assert evaluacion["estados"]["tipo_registrado"] == E.PRESENTE

    for criterio, estado_esperado in estados_esperados.items():
        assert evaluacion["estados"][criterio] == estado_esperado

@pytest.mark.parametrize(
    "tipo",
    [
        "Receta Médica",
        "Informe de Laboratorio",
        "Informe de Estudio por Imágenes",
        "Orden / Solicitud de Procedimiento",
        "Epicrisis / Informe de Alta",
        "Certificado Médico",
    ],
)
def test_s4_paciente_ausente_bloquea_en_todos_los_tipos(tipo):
    doc = document(score=0.95)
    doc["clasificacion"]["tipo_documento"] = tipo
    doc["datos_extraidos"]["paciente"]["nombre"] = None

    evaluacion = evaluar_documento(doc)

    assert evaluacion["estados"]["paciente"] == E.AUSENTE
    assert "paciente" in evaluacion["bloqueos"]
    assert evaluacion["es_ambiguo"] is True

def test_s4_limite_receta_sin_medicamentos_es_ambigua():
    doc = document(score=0.95)
    doc["datos_extraidos"]["medicamentos_recetados"] = []

    evaluacion = evaluar_documento(doc)

    assert evaluacion["estados"]["medicamentos"] == E.AUSENTE
    assert "medicamentos" in evaluacion["bloqueos"]
    assert evaluacion["es_ambiguo"] is True

    resultado = procesar_con_orquestador(doc)

    assert resultado["status"] == "auditoria_humana"
    assert resultado["decision_enrutamiento"]["requiere_auditoria_humana"] is True
def test_s4_limite_informe_sin_dato_esencial_es_ambiguo():
    doc = document(score=0.95)
    doc["clasificacion"]["tipo_documento"] = "Informe de Laboratorio"
    doc["datos_extraidos"]["estudio_realizado"] = None

    evaluacion = evaluar_documento(doc)

    assert evaluacion["estados"]["estudio"] == E.AUSENTE
    assert "estudio" in evaluacion["bloqueos"]
    assert evaluacion["es_ambiguo"] is True


def test_s4_limite_tipo_no_reconocido_exige_revision():
    doc = document(score=0.99)
    doc["clasificacion"]["tipo_documento"] = "Tipo documental desconocido"

    evaluacion = evaluar_documento(doc)

    assert evaluacion["estados"]["tipo_registrado"] == E.AUSENTE
    assert evaluacion["completitud"] == 0
    assert evaluacion["es_ambiguo"] is True

    resultado = procesar_con_orquestador(doc)

    assert resultado["status"] == "auditoria_humana"
    assert resultado["decision_enrutamiento"]["requiere_auditoria_humana"] is True


def test_s4_limite_score_igual_070_no_es_ambiguo_por_umbral():
    doc = document(score=0.70)

    evaluacion = evaluar_documento(doc)

    assert evaluacion["score_operativo"] == 0.70
    assert evaluacion["es_ambiguo"] is False

    resultado = procesar_con_orquestador(doc)

    assert resultado["status"] == "procesado"


def test_s4_limite_urgente_con_baja_confianza_conserva_urgencia():
    doc = document(priority="Urgente", score=0.69)

    resultado = procesar_con_orquestador(
        doc,
        source_text="Documento sintético de prueba.",
    )

    assert resultado["status"] == "auditoria_humana"
    assert resultado["clasificacion"]["nivel_prioridad"] == "Urgente"
    assert resultado["decision_enrutamiento"]["requiere_auditoria_humana"] is True
    assert resultado["decision_enrutamiento"]["destino_principal"] == "Cola_Revision_Humana"

@pytest.mark.parametrize(
    "tipo",
    [
        "Receta Médica",
        "Informe de Laboratorio",
        "Informe de Estudio por Imágenes",
        "Orden / Solicitud de Procedimiento",
        "Epicrisis / Informe de Alta",
        "Certificado Médico",
    ],
)
def test_s4_no_verificable_bloquea_en_todos_los_tipos(tipo):
    doc = document(score=0.95)
    doc["clasificacion"]["tipo_documento"] = tipo
    doc["datos_extraidos"]["paciente"]["nombre"] = "ILLEGIBLE"

    evaluacion = evaluar_documento(doc)

    assert evaluacion["estados"]["paciente"] == E.NO_VERIFICABLE
    assert "paciente" in evaluacion["bloqueos"]
    assert evaluacion["es_ambiguo"] is True


@pytest.mark.parametrize(
    "tipo, completitud_esperada",
    [
        ("Receta Médica", 1.0),
        ("Informe de Laboratorio", 0.75),
        ("Informe de Estudio por Imágenes", 0.75),
        ("Orden / Solicitud de Procedimiento", 2 / 3),
        ("Epicrisis / Informe de Alta", 2 / 3),
        ("Certificado Médico", 0.75),
    ],
)
def test_s4_no_aplicable_sale_del_denominador(tipo, completitud_esperada):
    doc = document(score=0.95)
    doc["clasificacion"]["tipo_documento"] = tipo

    evaluacion = evaluar_documento(doc)

    assert evaluacion["estados"]["diagnostico"] == E.NO_APLICABLE
    assert evaluacion["completitud"] == pytest.approx(completitud_esperada)
