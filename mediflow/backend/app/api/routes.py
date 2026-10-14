from typing import Optional, Literal
import uuid
from pathlib import PurePosixPath
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, status
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
            result = await run_in_threadpool(
                analyze_received_document, file_bytes, file.filename, doc_id, storage
            )
            # Agregado por Drazen (S3-04A): persistir JSON final generado por IA en OCI
            try:
                await run_in_threadpool(gestor.guardar_resultado_triage, result)
            except Exception:
                pass
            return result
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
    initial_response = {
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
    # Agregado por Drazen (S3-04A): persistir JSON en bucket recibidos
    try:
        await run_in_threadpool(gestor.guardar_resultado_triage, initial_response)
    except Exception:
        pass
    return initial_response


# ==============================================================================
# ENDPOINTS GET - CONSULTA DE DOCUMENTOS (Agregado por Drazen - S3-03)
# ==============================================================================

@router.get(
    "/documents",
    response_model=list[TriageResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar documentos clínicos",
    description="Retorna la lista de documentos clínicos y resultados de triaje persistidos en OCI Object Storage."
)
async def get_documents(
    status_filter: Optional[Literal["recibido", "procesado", "auditoria_humana"]] = Query(
        default=None, alias="status", description="Filtrar por estado del documento ('recibido', 'procesado', 'auditoria_humana')"
    ),
    prioridad: Optional[Literal["Rutina", "Urgente"]] = Query(
        default=None, description="Filtrar por nivel de prioridad clínica ('Rutina', 'Urgente')"
    ),
    limit: int = Query(
        default=100, ge=1, le=500, description="Límite máximo de documentos a retornar (1-500)"
    ),
):
    """
    S3-03.1 / S3-03.3: Lista los documentos clínicos almacenados en OCI.
    Permite filtrar por estado (recibido/procesado/auditoria_humana) y prioridad.
    """
    try:
        gestor = await run_in_threadpool(OCIStorageManager)
        raw_docs = await run_in_threadpool(
            gestor.listar_resultados_triage, status=status_filter, limit=limit
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudieron recuperar los documentos de OCI."
        )

    documentos: list[TriageResponse] = []
    for doc in raw_docs:
        try:
            validated = TriageResponse.model_validate(doc)
            if prioridad and validated.clasificacion.nivel_prioridad != prioridad:
                continue
            documentos.append(validated)
        except Exception:
            continue
    return documentos


@router.get(
    "/documents/{document_id}",
    response_model=TriageResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar documento clínico por ID",
    description="Recupera el detalle y resultado de triaje de un documento clínico persistido en OCI Object Storage."
)
async def get_document_by_id(document_id: str):
    """
    S3-03.2 / S3-03.4: Consulta un documento específico por su ID.
    Busca el JSON correspondiente en los buckets de OCI y devuelve el contrato validado.
    """
    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar un identificador de documento válido."
        )
    document_id = document_id.strip()
    if "/" in document_id or "\\" in document_id or ".." in document_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de documento inválido."
        )

    try:
        gestor = await run_in_threadpool(OCIStorageManager)
        doc_data = await run_in_threadpool(gestor.recuperar_resultado_triage, document_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al consultar el almacenamiento en OCI."
        )

    if doc_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento '{document_id}' no encontrado."
        )

    try:
        return TriageResponse.model_validate(doc_data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El documento almacenado en OCI no cumple el contrato oficial de datos."
        )
