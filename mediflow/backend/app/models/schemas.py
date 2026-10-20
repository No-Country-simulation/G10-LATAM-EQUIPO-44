from typing import Optional, Literal
from pydantic import BaseModel, Field

#importaciones agregadas por eliana
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, model_validator

class ClasificacionSchema(BaseModel):
    tipo_documento: str = Field(..., examples=["Pendiente de procesamiento"])
    especialidad: Optional[str] = None
    # Agregado por Edil: Eliana y Nicolás permiten solo Rutina o Urgente.
    # Pendiente describe el procesamiento, no una prioridad clínica.
    nivel_prioridad: Literal["Rutina", "Urgente"] = Field(default="Rutina")
    score_confianza_clasificacion: float = Field(default=0.0, ge=0.0, le=1.0)

class PacienteSchema(BaseModel):
    nombre: Optional[str] = None
    edad: Optional[int] = None

class MedicoSchema(BaseModel):
    nombre: Optional[str] = None
    matricula: Optional[str] = None

# Agregado por Edil: se amplía el contrato de Eliana de forma opcional para
# usar los nombres oficiales de su actualización y aceptar dosis ausente sin inventarla.
class MedicamentoSchema(BaseModel):
    medicamento: str
    dosis: Optional[str] = None


class DatosExtraidosSchema(BaseModel):
    paciente: PacienteSchema = Field(default_factory=PacienteSchema)
    medico_solicitante: MedicoSchema = Field(default_factory=MedicoSchema)
    estudio_realizado: Optional[str] = None
    diagnostico_principal: Optional[str] = None
    cie10_sugerido: Optional[str] = None
    medicamentos_recetados: list[MedicamentoSchema] = Field(default_factory=list)

class DecisionEnrutamientoSchema(BaseModel):
    destino_principal: str = Field(default="Cola_Procesamiento_Inicial")
    requiere_auditoria_humana: bool = Field(default=False)
    justificacion_enrutamiento: str

class AlmacenamientoOCISchema(BaseModel):
    bucket: str
    ruta_objeto: str
    status_backup: str

class TriageResponse(BaseModel):
    # Agregado por Edil: estados acordados en la matriz de Laura.
    status: Literal["recibido", "procesado", "auditoria_humana"] = Field(default="recibido", examples=["recibido"])
    documento_id: str
    clasificacion: ClasificacionSchema
    datos_extraidos: DatosExtraidosSchema
    decision_enrutamiento: DecisionEnrutamientoSchema
    notificacion_generada: Optional[dict] = None
    almacenamiento_oci: AlmacenamientoOCISchema


# === CONTRATO DE AUDITORÍA SPRINT 4 ===

# 1. Definimos los estados permitidos para la auditoría
class ReviewStatus(str, Enum):
    aprobado = "aprobado"
    rechazado = "rechazado"
    solicitar_nueva_imagen = "solicitar_nueva_imagen"

# 2. El modelo exacto basado en el contrato en concenso con brando y drazen
class AuditoriaReviewRequest(BaseModel):
    documento_id: str = Field(..., description="ID único del documento generado por OCI/Backend")
    review_id: str = Field(..., description="ID único de esta revisión manual")
    review_status: ReviewStatus = Field(..., description="Veredicto final de la revisión")
    reviewer_id: str = Field(..., description="Identificador del auditor (ej. auditor_demo_01)")
    observacion: Optional[str] = Field(None, description="Comentarios adicionales del auditor")
    reviewed_at: datetime = Field(..., description="Marca de tiempo en formato ISO 8601 (UTC)")

    # 3. Validación estricta: Si se rechaza, la observación es obligatoria
    @model_validator(mode='after')
    def validar_observacion_rechazo(self):
        if self.review_status == ReviewStatus.rechazado and not self.observacion:
            raise ValueError("La observación es obligatoria cuando se rechaza un documento.")
        return self