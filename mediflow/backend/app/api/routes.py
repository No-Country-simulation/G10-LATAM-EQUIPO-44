import uuid
from pathlib import PurePosixPath
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from starlette.concurrency import run_in_threadpool
from app.core.oci_client import OCIStorageManager
from app.models.schemas import TriageResponse
# Agregado por Edil: la nueva integración se mantiene en un servicio separado.
from app.services.triage_pipeline import analyze_received_document
from app.services.llm_errors import (
    LLMConfigurationError, LLMAuthenticationError, LLMInputError,
    LLMQuotaError, LLMTimeoutError, LLMNetworkError, LLMUnavailableError,
    LLMRequestError, LLMResponseError,
)

router = APIRouter(prefix="/api", tags=["Triage"])

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
MAX_FILE_BYTES = 10 * 1024 * 1024

@router.post("/triage", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
# Agregado por Edil: analyze permite integrar IA sin retirar la recepción original.
async def post_triage(file: UploadFile = File(...), analyze: bool = Form(False)):
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
        bucket_name = gestor.settings.bucket_recibidos
        backup_status = "exito"

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo almacenar el documento en OCI."
        )

    # Agregado por Edil: OCI se completa antes de la IA. Ante fallos se conserva
    # el original en recibidos; no se borra ni se finge una respuesta procesada.
    if analyze:
        storage = {
            "bucket": bucket_name, "ruta_objeto": object_name, "status_backup": backup_status,
        }
        try:
            return await run_in_threadpool(
                analyze_received_document, file_bytes, file.filename, doc_id, storage
            )
        except LLMConfigurationError:
            code, message = 503, "El análisis IA no está configurado."
        except LLMAuthenticationError:
            code, message = 502, "No se pudo autenticar el servicio de análisis."
        except LLMQuotaError:
            code, message = 429, "El servicio de análisis alcanzó su límite de solicitudes."
        except LLMTimeoutError:
            code, message = 504, "El servicio de análisis agotó el tiempo de espera."
        except (LLMNetworkError, LLMUnavailableError):
            code, message = 503, "El servicio de análisis no está disponible."
        except (LLMRequestError, LLMResponseError):
            code, message = 502, "El servicio de análisis devolvió una respuesta inválida."
        except LLMInputError:
            code, message = 422, "El documento no puede analizarse en su formato actual."
        except Exception:
            code, message = 500, "No se pudo completar el análisis."
        raise HTTPException(status_code=code, detail=message, headers={"X-Document-ID": doc_id})

    # Agregado por Edil: se conserva a continuación la respuesta original de recepción.
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
            "justificacion_enrutamiento": f"Archivo almacenado en '{bucket_name}/{object_name}'"
        },
        "notificacion_generada": None,
        "almacenamiento_oci": {
            "bucket": bucket_name,
            "ruta_objeto": object_name,
            "status_backup": backup_status
        }
    }
