"""S4-04: adversariales técnicos, sin nuevas reglas clínicas."""
import pytest
from data_ai.synthetic_demo_rules import evaluate_synthetic_demo, rules_profile
from app.services.servicio_orquestador import procesar_con_orquestador

@pytest.mark.parametrize("case,text,expected", [
 ("ADV-01", "No se confirma glicemia en ayunas: 250 mg/dL.", []),
 ("ADV-02", "Antecedente de lesión por presión sacra estadio 4.", []),
 ("ADV-03", "Glucosa en ayunas: 250 mg/dL.", ["hiperglicemia_marcada"]),
 ("ADV-04", "Glicemia en ayunas: 250 mmol/L.", []),
 ("ADV-05", "ILLEGIBLE", []),
])
def test_adversarial_rules(case,text,expected):
    assert evaluate_synthetic_demo(text)["matched_rules"] == expected, case

def _document():
    return {"documento_id":"DOC-S4-DEMO","status":"procesado",
      "clasificacion":{"tipo_documento":"Informe de Laboratorio","nivel_prioridad":"Rutina","score_confianza_clasificacion":0.3},
      "datos_extraidos":{"paciente":{"nombre":"Persona Ficticia"},"medico_solicitante":{"nombre":"Profesional Ficticio"},"estudio_realizado":"Estudio sintético","medicamentos_recetados":[]},
      "decision_enrutamiento":{"destino_principal":"Cola_Historia_Clinica","requiere_auditoria_humana":False,"justificacion_enrutamiento":"Prueba sintética"},
      "almacenamiento_oci":{"bucket":"recibidos","ruta_objeto":"synthetic.txt","status_backup":"exito"}}

def test_adv06_urgent_and_review(monkeypatch):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE","synthetic_demo_v1")
    result=procesar_con_orquestador(_document(),source_text="Glicemia en ayunas: 250 mg/dL.")
    assert result["clasificacion"]["nivel_prioridad"] == "Urgente"
    assert result["decision_enrutamiento"]["requiere_auditoria_humana"] is True
    assert result["status"] == "auditoria_humana"

def test_general_default_does_not_activate_demo(monkeypatch):
    monkeypatch.delenv("TRIAGE_RULES_PROFILE",raising=False)
    assert rules_profile()=="general"
    result=procesar_con_orquestador(_document(),source_text="Glicemia en ayunas: 250 mg/dL.")
    assert result["clasificacion"]["nivel_prioridad"] == "Rutina"

def test_filename_cannot_activate_demo(monkeypatch):
    monkeypatch.delenv("TRIAGE_RULES_PROFILE",raising=False)
    assert rules_profile()=="general"
    result=procesar_con_orquestador(_document(),source_text="MF_004_URG: control sin hallazgos agudos.")
    assert result["clasificacion"]["nivel_prioridad"] == "Rutina"
