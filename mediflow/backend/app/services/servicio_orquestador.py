"""
Servicio integrador (Sprint 3): Envuelve la extracción de IA (Sprint 2) 
y la pasa por el orquestador LangGraph sin modificar el código original.
"""

from app.services.triage_pipeline import analyze_received_document
from app.core.orquestador import pipeline_v1_2
from app.models.schemas import TriageResponse

def procesar_con_orquestador(content: bytes, filename: str, document_id: str, storage: dict) -> TriageResponse:
    # 1. Extracción original
    triage_pydantic_obj = analyze_received_document(content, filename, document_id, storage)
    documento_dict = triage_pydantic_obj.model_dump()
    
    # ¡NUEVO! Rescatamos la justificación original antes de que el orquestador la sobreescriba
    justificacion_original = documento_dict["decision_enrutamiento"].get("justificacion_enrutamiento", "")
    
    # 2. Orquestador
    resultado_orquestacion = pipeline_v1_2.invoke({"documento": documento_dict})
    decision_final = resultado_orquestacion["decision_enrutamiento"]
    
    # ¡NUEVO! Si LangGraph no tiene una justificación, le devolvemos la original
    if "justificacion_enrutamiento" not in decision_final:
        decision_final["justificacion_enrutamiento"] = justificacion_original + " (Auditado por LangGraph)"
        
    # 3. Combinamos los datos en lugar de reemplazarlos destructivamente
    documento_dict["decision_enrutamiento"].update(decision_final)
    
    # Actualizamos estado
    if decision_final.get("status"):
        documento_dict["status"] = decision_final["status"]
        
    # 4. Sellado final y validación estricta
    documento_final = TriageResponse.model_validate(documento_dict)
    
    return documento_final