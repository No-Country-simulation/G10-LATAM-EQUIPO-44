from pathlib import Path
import sys

import pytest

# Permite reutilizar el validador oficial del backend
backend_dir = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.llm_errors import LLMResponseError
from app.services.gemini_client import validate_clinical_response
def test_val_001_json_valido():
    respuesta = """
    {
      "clasificacion": {
        "tipo_documento": "Certificado Médico",
        "especialidad": "General",
        "nivel_prioridad": "Rutina",
        "score_confianza_clasificacion": 0.95
      },
      "datos_extraidos": {
        "paciente": {
          "nombre": null,
          "edad": null
        },
        "medico_solicitante": {
          "nombre": null,
          "matricula": null
        },
        "estudio_realizado": null,
        "diagnostico_principal": null,
        "cie10_sugerido": null,
        "medicamentos_recetados": []
      },
      "decision_enrutamiento": {
        "destino_principal": "Cola_Historia_Clinica",
        "requiere_auditoria_humana": false,
        "justificacion_enrutamiento": "Documento legible y sin condiciones que requieran auditoría humana."
      }
    }
    """

    resultado = validate_clinical_response(respuesta)

    assert resultado.clasificacion.nivel_prioridad == "Rutina"
    assert resultado.decision_enrutamiento.requiere_auditoria_humana is False

def test_val_002_json_mal_formado():
    respuesta = """
    {
      "clasificacion": {
        "tipo_documento": "Certificado Medico"
    """

    with pytest.raises(LLMResponseError):
        validate_clinical_response(respuesta)

def test_val_003_falta_justificacion_enrutamiento():
    respuesta = """
    {
      "clasificacion": {
        "tipo_documento": "Certificado Medico",
        "especialidad": "General",
        "nivel_prioridad": "Rutina",
        "score_confianza_clasificacion": 0.95
      },
      "datos_extraidos": {
        "paciente": {
          "nombre": null,
          "edad": null
        },
        "medico_solicitante": {
          "nombre": null,
          "matricula": null
        },
        "estudio_realizado": null,
        "diagnostico_principal": null,
        "cie10_sugerido": null,
        "medicamentos_recetados": []
      },
      "decision_enrutamiento": {
        "destino_principal": "Cola_Historia_Clinica",
        "requiere_auditoria_humana": false
      }
    }
    """

    with pytest.raises(LLMResponseError):
        validate_clinical_response(respuesta)

def test_val_004_tipo_dato_incorrecto():
    respuesta = """
    {
      "clasificacion": {
        "tipo_documento": "Certificado Medico",
        "especialidad": "General",
        "nivel_prioridad": "Rutina",
        "score_confianza_clasificacion": 0.95
      },
      "datos_extraidos": {
        "paciente": {
          "nombre": null,
          "edad": "52"
        },
        "medico_solicitante": {
          "nombre": null,
          "matricula": null
        },
        "estudio_realizado": null,
        "diagnostico_principal": null,
        "cie10_sugerido": null,
        "medicamentos_recetados": []
      },
      "decision_enrutamiento": {
        "destino_principal": "Cola_Historia_Clinica",
        "requiere_auditoria_humana": false,
        "justificacion_enrutamiento": "Documento legible y sin condiciones que requieran auditoria humana."
      }
    }
    """

    with pytest.raises(LLMResponseError):
        validate_clinical_response(respuesta)

def test_val_005_score_fuera_de_rango():
    respuesta = """
    {
      "clasificacion": {
        "tipo_documento": "Certificado Medico",
        "especialidad": "General",
        "nivel_prioridad": "Rutina",
        "score_confianza_clasificacion": 1.25
      },
      "datos_extraidos": {
        "paciente": {
          "nombre": null,
          "edad": null
        },
        "medico_solicitante": {
          "nombre": null,
          "matricula": null
        },
        "estudio_realizado": null,
        "diagnostico_principal": null,
        "cie10_sugerido": null,
        "medicamentos_recetados": []
      },
      "decision_enrutamiento": {
        "destino_principal": "Cola_Historia_Clinica",
        "requiere_auditoria_humana": false,
        "justificacion_enrutamiento": "Documento legible y sin condiciones que requieran auditoria humana."
      }
    }
    """

    with pytest.raises(LLMResponseError):
        validate_clinical_response(respuesta)

def test_val_006_boolean_incorrecto():
    respuesta = """
    {
      "clasificacion": {
        "tipo_documento": "Certificado Medico",
        "especialidad": "General",
        "nivel_prioridad": "Rutina",
        "score_confianza_clasificacion": 0.95
      },
      "datos_extraidos": {
        "paciente": {
          "nombre": null,
          "edad": null
        },
        "medico_solicitante": {
          "nombre": null,
          "matricula": null
        },
        "estudio_realizado": null,
        "diagnostico_principal": null,
        "cie10_sugerido": null,
        "medicamentos_recetados": []
      },
      "decision_enrutamiento": {
        "destino_principal": "Cola_Historia_Clinica",
        "requiere_auditoria_humana": "false",
        "justificacion_enrutamiento": "Documento legible y sin condiciones que requieran auditoria humana."
      }
    }
    """

    with pytest.raises(LLMResponseError):
        validate_clinical_response(respuesta)

def test_val_007_enrutamiento_inconsistente():
    respuesta = """
    {
      "clasificacion": {
        "tipo_documento": "Receta Medica",
        "especialidad": "General",
        "nivel_prioridad": "Rutina",
        "score_confianza_clasificacion": 0.95
      },
      "datos_extraidos": {
        "paciente": {
          "nombre": null,
          "edad": null
        },
        "medico_solicitante": {
          "nombre": null,
          "matricula": null
        },
        "estudio_realizado": null,
        "diagnostico_principal": null,
        "cie10_sugerido": null,
        "medicamentos_recetados": []
      },
      "decision_enrutamiento": {
        "destino_principal": "Cola_Farmacia",
        "requiere_auditoria_humana": true,
        "justificacion_enrutamiento": "El documento requiere revision humana."
      }
    }
    """

    with pytest.raises(LLMResponseError):
        validate_clinical_response(respuesta)