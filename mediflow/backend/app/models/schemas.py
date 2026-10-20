import re
from datetime import datetime
from enum import Enum
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

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

class ReviewStatus(str, Enum):
    aprobado = "aprobado"
    rechazado = "rechazado"


# Solicitud enviada desde el frontend a la API
class AuditoriaReviewRequest(BaseModel):
    decision: ReviewStatus = Field(..., description="Decisión del auditor")
    reviewer_id: str = Field(..., min_length=1, description="Identificador del auditor")
    observacion: Optional[str] = Field(default=None, description="Observación del auditor")
    expected_review_status: Literal["pendiente"] = Field(..., description="Estado esperado antes de registrar la revisión")

    @field_validator("reviewer_id")
    @classmethod
    def validar_reviewer_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El identificador del auditor es obligatorio.")
        return value

    @model_validator(mode="after")
    def validar_observacion_rechazo(self):
        if (self.decision == ReviewStatus.rechazado and not (self.observacion or "").strip()):
            raise ValueError("La observación es obligatoria cuando se rechaza un documento.")
        return self


# Registro completo generado por el backend y almacenado en OCI
class AuditoriaReviewRecord(BaseModel):
    documento_id: str = Field(..., min_length=1)
    review_id: str = Field(..., min_length=1)
    review_status: ReviewStatus
    reviewer_id: str = Field(..., min_length=1)
    observacion: Optional[str] = None
    reviewed_at: datetime

    @field_validator("documento_id")
    @classmethod
    def validar_documento_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
            raise ValueError("El identificador del documento no es válido.")
        return value

    @field_validator("review_id")
    @classmethod
    def validar_review_id(cls, value: str) -> str:
        formato_rev = re.fullmatch(r"REV-[A-Za-z0-9_-]{1,64}", value)

        try:
            es_uuid4 = UUID(value).version == 4
        except (ValueError, AttributeError):
            es_uuid4 = False

        if not formato_rev and not es_uuid4:
            raise ValueError("El identificador de revisión no es válido.")
        return value

    @field_validator("reviewer_id")
    @classmethod
    def validar_reviewer_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("El identificador del auditor es obligatorio.")
        return value

    @model_validator(mode="after")
    def validar_registro(self):
        if (self.review_status == ReviewStatus.rechazado and not (self.observacion or "").strip()):
            raise ValueError("La observación es obligatoria cuando se rechaza un documento.")

        if (self.reviewed_at.utcoffset() is None or self.reviewed_at.utcoffset().total_seconds() != 0):
            raise ValueError("reviewed_at debe incluir una fecha con zona horaria UTC.")

        return self