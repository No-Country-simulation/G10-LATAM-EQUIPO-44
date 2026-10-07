import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.core.config import settings
from app.core.oci_client import OCIStorageManager
from app.models.schemas import TriageResponse

router = APIRouter(prefix="/api", tags=["Triage"])

@router.post("/triage", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
async def post_triage(file: UploadFile = File(...)):
    # 1. Validar que llegó un archivo
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe enviar un archivo válido."
        )

    # 2. Generar identificadores únicos
    doc_id = f"DOC-CLIN-2026-{uuid.uuid4().hex[:4].upper()}"
    object_name = f"{doc_id}_{file.filename}"
    bucket_recibidos = settings.OCI_BUCKET_RECIBIDOS

    try:
        # 3. Leer los bytes en memoria
        file_bytes = await file.read()

        # 4. Instanciar gestor y subir a OCI
        gestor = OCIStorageManager()
        gestor.subir_archivo_desde_memoria(
            contenido_bytes=file_bytes,
            nombre_bucket=bucket_recibidos,
            nombre_destino=object_name
        )
        backup_status = "exito"

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir a OCI: {str(err)}"
        )

    # 5. Respuesta según el contrato JSON oficial (Estado 'recibido' según Matriz de Estados)
    return {
        "status": "recibido",
        "documento_id": doc_id,
        "clasificacion": {
            "tipo_documento": "Pendiente de procesamiento",
            "especialidad": "General",
            "nivel_prioridad": "Rutina",
            "score_confianza_clasificacion": 0.0
        },
        "datos_extraidos": {
            "paciente": {"nombre": None, "edad": None},
            "medico_solicitante": {"nombre": None, "matricula": None},
            "estudio_realizado": None,
            "diagnostico_principal": None,
            "cie10_sugerido": None
        },
        "decision_enrutamiento": {
            "destino_principal": "Cola_Procesamiento_Inicial",
            "requiere_auditoria_humana": False,
            "justificacion_enrutamiento": f"Archivo subido correctamente al bucket '{bucket_recibidos}'"
        },
        "notificacion_generada": None,
        "almacenamiento_oci": {
            "bucket": bucket_recibidos,
            "ruta_objeto": object_name,
            "status_backup": backup_status
        }
    }
