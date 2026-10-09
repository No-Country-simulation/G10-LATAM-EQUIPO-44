import uuid
from pathlib import PurePosixPath
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from starlette.concurrency import run_in_threadpool
from app.core.config import settings
from app.core.oci_client import OCIStorageManager
from app.core.llm_client import CohereClient, LLMError, LLMInputError
from app.models.schemas import TriageResponse

router = APIRouter(prefix="/api", tags=["Triage"])

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
MAX_FILE_BYTES = 10 * 1024 * 1024

@router.post("/triage", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
async def post_triage(file: UploadFile = File(...)):
    # 1. Validar que llegó un archivo
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe enviar un archivo válido."
        )

    # 2. Generar identificadores únicos
    extension = PurePosixPath(file.filename.replace("\\", "/")).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Formato de archivo no permitido.")
    file_bytes = await file.read(MAX_FILE_BYTES + 1)
    if not file_bytes:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MiB.")
    doc_id = f"DOC-CLIN-{uuid.uuid4().hex.upper()}"
    object_name = f"{doc_id}{extension}"

    try:
        # 3. Leer los bytes en memoria

        # 4. Instanciar gestor y subir a OCI
        gestor = await run_in_threadpool(OCIStorageManager)
        object_name = await run_in_threadpool(gestor.subir_a_recibidos, file_bytes, object_name)
        bucket_name = gestor.settings.bucket_name
        backup_status = "exito"

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo almacenar el documento en OCI."
        )

    extraction = None
    if extension in ALLOWED_EXTENSIONS and settings.LLM_PROVIDER.lower() == "cohere":
        try:
            extraction = await run_in_threadpool(
                CohereClient.from_settings().extract_document,
                file_bytes,
                file.filename,
            )
        except LLMInputError:
            extraction = None
        except LLMError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="No se pudo obtener una respuesta valida del proveedor LLM.",
            ) from error

    response = {
        "status": "procesado" if extraction else "recibido",
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
            "justificacion_enrutamiento": f"Archivo almacenado en '{bucket_name}/{object_name}'"
        },
        "notificacion_generada": None,
        "almacenamiento_oci": {
            "bucket": bucket_name,
            "ruta_objeto": object_name,
            "status_backup": backup_status
        }
    }
    if extraction:
        unexpected = set(extraction) - {"clasificacion", "datos_extraidos"}
        if unexpected:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="La respuesta del LLM contiene campos no esperados.",
            )
        response["clasificacion"] = extraction.get("clasificacion", {})
        response["datos_extraidos"] = extraction.get("datos_extraidos", {})
        response["decision_enrutamiento"]["justificacion_enrutamiento"] = (
            f"Extraccion Cohere completada; archivo almacenado en '{bucket_name}/{object_name}'"
        )
        try:
            return TriageResponse.model_validate(response).model_dump()
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="La respuesta del LLM no cumple el contrato JSON.",
            ) from error
    return response
