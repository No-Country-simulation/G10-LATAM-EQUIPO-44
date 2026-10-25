from typing import Optional, Literal
from datetime import datetime, timezone
import json
import re
from pydantic import ValidationError
import logging
import uuid
from pathlib import PurePosixPath
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Request, status, Depends
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from app.core.oci_client import OCIStorageManager
from app.core.review_auth import Principal, require_auditor
from app.models.schemas import (
    TriageResponse,
    AuditoriaReviewRequest,
    AuditoriaReviewResponse,
    AuditoriaReviewRecord,
    ReviewStatus,
)
from app.core.error_handler import (
    DuplicateReviewError,
    ReviewValidationError,
    ReviewNotFoundError,
    OCITimeoutError,
    OCIPersistenceError,
    OCIPermissionDeniedError,
    OCIIncompleteResponseError,
    OCICredentialsError,
)
# Agregado por Edil: la nueva integración se mantiene en un servicio separado.
from app.services.triage_pipeline import analyze_received_document
from app.services.llm_errors import (
    LLMConfigurationError, LLMAuthenticationError, LLMInputError,
    LLMQuotaError, LLMTimeoutError, LLMNetworkError, LLMUnavailableError,
    LLMRequestError, LLMResponseError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Triage"])

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
MAX_FILE_BYTES = 10 * 1024 * 1024

@router.post("/triage", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
# Agregado por Edil: analyze permite integrar IA sin retirar la recepción original.
async def post_triage(request: Request, file: UploadFile = File(...), analyze: bool = Form(False)):
    # Agregado por Edil: el autor de la carga procede de la identidad verificada
    # por el servidor. No es el médico extraído del documento ni un campo de IA.
    # Las cargas sin identidad y los JSON históricos conservan null.
    principal = getattr(request.state, "mediflow_principal", None)
    cargado_por = principal.login if isinstance(principal, Principal) else None
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

    except Exception as error:
        # Agregado por Edil: registrar solo categoria e ID, nunca credenciales ni documento.
        logger.warning("triage_storage_failed category=%s document_id=%s", type(error).__name__, doc_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo almacenar el documento en OCI."
        )

    # Agregado por Edil: persistir la recepción antes de llamar a Gemini.
    # Si el proveedor falla, GET puede recuperar el documento recibido sin fingir análisis.
    # Agregado por Edil: se conserva a continuación la respuesta original de recepción.
    # 5. Respuesta según el contrato JSON oficial (Estado 'recibido' según Matriz de Estados)
    initial_response = {
        "status": "recibido",
        "cargado_por": cargado_por,
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

    # Drazen S3-04A: la recepción también queda consultable mediante su JSON.
    await _persist_triage_result(gestor, initial_response, doc_id)

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
            # Agregado por Edil: conservar el autor original también al finalizar
            # el análisis; una respuesta del LLM nunca puede reemplazarlo.
            result = TriageResponse.model_validate(result).model_copy(
                update={"cargado_por": cargado_por}
            )
            # Agregado por Edil: integrar copia verificada de Brando antes de
            # confirmar el resultado final. Nunca borrar el original recibido.
            result = await _copy_original_to_result_bucket(gestor, result, doc_id, bucket_name, object_name)
            # Drazen S3-04A: guardar resultado; Edil: no ocultar el fallo de escritura.
            await _persist_triage_result(gestor, result, doc_id)
            return result
        except HTTPException:
            raise
        except LLMConfigurationError as error:
            code, message = 503, "El análisis IA no está configurado."
            logger.warning("triage_analysis_failed category=%s http_status=%s document_id=%s", type(error).__name__, code, doc_id)
        except LLMAuthenticationError as error:
            code, message = 502, "No se pudo autenticar el servicio de análisis."
            logger.warning("triage_analysis_failed category=%s http_status=%s document_id=%s", type(error).__name__, code, doc_id)
        except LLMQuotaError as error:
            code, message = 429, "El servicio de análisis alcanzó su límite de solicitudes."
            logger.warning("triage_analysis_failed category=%s http_status=%s document_id=%s", type(error).__name__, code, doc_id)
        except LLMTimeoutError as error:
            code, message = 504, "El servicio de análisis agotó el tiempo de espera."
            logger.warning("triage_analysis_failed category=%s http_status=%s document_id=%s", type(error).__name__, code, doc_id)
        except (LLMNetworkError, LLMUnavailableError) as error:
            code, message = 503, "El servicio de análisis no está disponible."
            logger.warning("triage_analysis_failed category=%s http_status=%s document_id=%s", type(error).__name__, code, doc_id)
        except (LLMRequestError, LLMResponseError) as error:
            code, message = 502, "El servicio de análisis devolvió una respuesta inválida."
            logger.warning("triage_analysis_failed category=%s http_status=%s document_id=%s", type(error).__name__, code, doc_id)
        except LLMInputError as error:
            code, message = 422, "El documento no puede analizarse en su formato actual."
            logger.warning("triage_analysis_failed category=%s http_status=%s document_id=%s", type(error).__name__, code, doc_id)
        except Exception as error:
            code, message = 500, "No se pudo completar el análisis."
            logger.warning("triage_analysis_failed category=%s http_status=%s document_id=%s", type(error).__name__, code, doc_id)
        raise HTTPException(status_code=code, detail=message, headers={"X-Document-ID": doc_id})

    # Agregado por Edil: conservar aquí el código anterior como referencia.
    # Antes se guardaba la recepción solo cuando analyze era false.
    # # Agregado por Edil: se conserva a continuación la respuesta original de recepción.
    # # 5. Respuesta según el contrato JSON oficial (Estado 'recibido' según Matriz de Estados)
    # initial_response = {
    # "status": "recibido",
    # "documento_id": doc_id,
    # "clasificacion": {
    # "tipo_documento": "Pendiente de procesamiento",
    # "especialidad": "General",
    # "nivel_prioridad": "Rutina",
    # "score_confianza_clasificacion": 0.0
    # },
    # "datos_extraidos": {
    # "paciente": {"nombre": None, "edad": None},
    # "medico_solicitante": {"nombre": None, "matricula": None},
    # "estudio_realizado": None,
    # "diagnostico_principal": None,
    # "cie10_sugerido": None
    # },
    # "decision_enrutamiento": {
    # "destino_principal": "Cola_Procesamiento_Inicial",
    # "requiere_auditoria_humana": False,
    # "justificacion_enrutamiento": f"Archivo almacenado en '{bucket_name}/{object_name}'"
    # },
    # "notificacion_generada": None,
    # "almacenamiento_oci": {
    # "bucket": bucket_name,
    # "ruta_objeto": object_name,
    # "status_backup": backup_status
    # }
    # }
    #
    # # Drazen S3-04A: la recepción también queda consultable mediante su JSON.
    # await _persist_triage_result(gestor, initial_response, doc_id)
    # return initial_response
    return initial_response


async def _copy_original_to_result_bucket(gestor, payload, document_id, source_bucket, object_name):
    try:
        result = TriageResponse.model_validate(payload, strict=True)
        if result.documento_id != document_id or result.status == "recibido":
            raise ValueError("El resultado no corresponde al análisis recibido.")
        target_bucket = gestor.determinar_bucket_por_estado(result.status)
        if not isinstance(target_bucket, str) or not target_bucket.strip() or target_bucket == source_bucket:
            raise ValueError("El bucket final no es válido.")
        await run_in_threadpool(gestor.copiar_archivo, object_name, source_bucket, target_bucket)
        # El contrato sigue describiendo un archivo original, ahora su copia
        # verificada; no se añaden hashes ni campos internos al JSON público.
        data = result.model_dump()
        data["almacenamiento_oci"] = {
            "bucket": target_bucket, "ruta_objeto": object_name, "status_backup": "exito",
        }
        return TriageResponse.model_validate(data, strict=True)
    except Exception as error:
        logger.warning("triage_verified_copy_failed category=%s document_id=%s", type(error).__name__, document_id)
        raise HTTPException(status_code=503,
            detail="No se pudo verificar la copia OCI. El documento original sigue recibido.",
            headers={"X-Document-ID": document_id}) from None


async def _persist_triage_result(gestor, payload, document_id: str):
    # Agregado por Edil: una escritura fallida no puede devolver 201 silenciosamente.
    # El original ya está en recibidos; conservarlo y facilitar su identificación.
    try:
        validated = TriageResponse.model_validate(payload)
        if validated.documento_id != document_id:
            raise ValueError("El resultado no corresponde al documento recibido.")
        await run_in_threadpool(gestor.guardar_resultado_triage, validated.model_dump())
    except Exception as error:
        logger.warning("triage_json_persistence_failed category=%s document_id=%s", type(error).__name__, document_id)
        raise HTTPException(status_code=503,
            detail="No se pudo guardar el resultado JSON en OCI. El documento original sigue recibido.",
            headers={"X-Document-ID": document_id}) from None


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
            gestor.listar_resultados_triage, status=status_filter, limit=limit, prioridad=prioridad
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=502, detail="Un JSON almacenado en OCI es inválido.") from None
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
        except ValidationError:
            # Agregado por Edil: no devolver un listado parcial fingiendo éxito.
            raise HTTPException(status_code=502, detail="Un documento almacenado no cumple el contrato oficial.") from None
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
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", document_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de documento inválido."
        )

    try:
        gestor = await run_in_threadpool(OCIStorageManager)
        doc_data = await run_in_threadpool(gestor.recuperar_resultado_triage, document_id)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=502, detail="El JSON almacenado en OCI es inválido.") from None
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
        validated = TriageResponse.model_validate(doc_data)
        if validated.documento_id != document_id:
            raise ValueError("El identificador almacenado no coincide.")
        return validated
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El documento almacenado en OCI no cumple el contrato oficial de datos."
        )


# Agregado por Edil: el ojo consulta el original privado, nunca una URL pública de OCI.
# Solo el autor autenticado o un auditor pueden leer sus bytes.
@router.get("/documents/{document_id}/original", summary="Ver original almacenado en OCI")
async def get_document_original(document_id: str, request: Request):
    principal = getattr(request.state, "mediflow_principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="Inicia sesión para ver el archivo original.")
    document = await get_document_by_id(document_id)
    if not principal.can_review and document.cargado_por != principal.login:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver este original.")
    location = document.almacenamiento_oci
    extension = PurePosixPath(location.ruta_objeto).suffix.lower()
    if (extension not in ALLOWED_EXTENSIONS or "\\" in location.ruta_objeto
        or ".." in PurePosixPath(location.ruta_objeto).parts
        or PurePosixPath(location.ruta_objeto).name != document_id + extension):
        raise HTTPException(status_code=502, detail="La referencia del original no es válida.")
    mime = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".txt": "text/plain"}[extension]
    def read_original():
        gestor = OCIStorageManager()
        allowed = {gestor.settings.bucket_recibidos, gestor.settings.bucket_procesados, gestor.settings.bucket_auditoria}
        if location.bucket not in allowed:
            raise ValueError("Unexpected storage bucket")
        stored = gestor.object_storage.get_object(namespace_name=gestor.namespace,
            bucket_name=location.bucket, object_name=location.ruta_objeto)
        try:
            content = stored.data.raw.read(MAX_FILE_BYTES + 1)
        finally:
            close = getattr(stored.data.raw, "close", None)
            if callable(close): close()
        if not isinstance(content, bytes) or not content or len(content) > MAX_FILE_BYTES:
            raise ValueError("Invalid original size")
        return content
    try:
        content = await run_in_threadpool(read_original)
    except Exception as error:
        if getattr(error, "status", None) == 404:
            raise HTTPException(status_code=404, detail="El original no está disponible en OCI.") from None
        raise HTTPException(status_code=502, detail="No se pudo recuperar el original de OCI.") from None
    return Response(content, media_type=mime, headers={
        "Content-Disposition": f'inline; filename="{document_id}{extension}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
    })


# ==============================================================================
# ENDPOINTS DE REVISIÓN HUMANA (Sprint 4 - Drazen Gamboa / S4-01)
# ==============================================================================

def review_exception_to_http(error: Exception) -> HTTPException:
    """Traduce excepciones de dominio y OCI a códigos de estado HTTP contractuales."""
    if isinstance(error, HTTPException):
        return error
    if isinstance(error, ReviewValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )
    if isinstance(error, DuplicateReviewError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    if isinstance(error, ReviewNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    if isinstance(error, OCITimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="OCI agotó el tiempo de espera.",
        )
    if isinstance(
        error,
        (OCIPermissionDeniedError, OCIIncompleteResponseError, OCIPersistenceError, OCICredentialsError),
    ):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OCI no pudo completar la operación.",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Error interno del servidor.",
    )


@router.get(
    "/reviews/pending",
    response_model=list[TriageResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar documentos pendientes de auditoría humana",
    description="Retorna la lista de resultados de triaje en auditoría humana que no tienen una decisión final registrada."
)
async def get_pending_reviews():
    """
    S4-01: Consulta en OCI los documentos en cola de auditoría humana
    que todavía se encuentran en estado 'pendiente' (sin objeto _final.json).
    """
    try:
        gestor = await run_in_threadpool(OCIStorageManager)
        pending_raw = await run_in_threadpool(gestor.list_pending_reviews)
    except Exception as error:
        raise review_exception_to_http(error)

    pending_docs: list[TriageResponse] = []
    for doc in pending_raw:
        try:
            validated = TriageResponse.model_validate(doc)
            pending_docs.append(validated)
        except ValidationError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Un documento pendiente en OCI no cumple el contrato oficial de datos."
            )
    return pending_docs


@router.post(
    "/documents/{document_id}/review",
    response_model=AuditoriaReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Registrar decisión de auditoría humana",
    description="Registra la decisión definitiva de un auditor sobre un documento en auditoría humana y la persiste en OCI."
)
async def post_document_review(
    document_id: str,
    review_request: AuditoriaReviewRequest,
    auditor: Principal = Depends(require_auditor),
):
    """
    S4-01: Procesa y persiste una decisión de auditoría humana:
    - Valida que el documento exista y esté disponible para auditoría.
    - Comprueba que no tenga decisión previa (estado 'pendiente').
    - Genera review_id y timestamp UTC con sufijo 'Z'.
    - Persiste el registro de 6 campos en OCI via _final.json y copia espejo.
    - Maneja errores de validación (422), duplicados/concurrencia (409) y OCI (502/504).
    """
    # Agregado por Edil: el campo contractual del navegador no autentica;
    # debe coincidir con la identidad comprobada por el servidor.
    if review_request.reviewer_id != auditor.login:
        raise HTTPException(status_code=403, detail="El auditor no coincide con la identidad autenticada.")
    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar un identificador de documento válido."
        )
    document_id = document_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", document_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de documento inválido."
        )

    try:
        gestor = await run_in_threadpool(OCIStorageManager)
        doc_data = await run_in_threadpool(gestor.recuperar_resultado_triage, document_id)
    except Exception as error:
        raise review_exception_to_http(error)

    if doc_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento '{document_id}' no encontrado."
        )

    # Validar que el documento requiera o esté disponible para auditoría humana
    doc_status = doc_data.get("status")
    requiere_auditoria = doc_data.get("decision_enrutamiento", {}).get("requiere_auditoria_humana", False)
    if doc_status != "auditoria_humana" and not requiere_auditoria:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El documento '{document_id}' no está en estado de auditoría humana."
        )

    # Verificar que el documento continúe pendiente
    try:
        current_status = await run_in_threadpool(gestor.get_latest_review_status, document_id)
    except Exception as error:
        raise review_exception_to_http(error)

    if current_status != "pendiente":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El documento '{document_id}' ya cuenta con una decisión final registrada ({current_status})."
        )

    # Generar identificador único de revisión y timestamp UTC con sufijo Z
    now_utc = datetime.now(timezone.utc)
    review_timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    review_id = f"REV-{now_utc.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"

    # Construir el registro exacto de seis campos para OCI
    record_payload = {
        "documento_id": document_id,
        "review_id": review_id,
        "review_status": review_request.decision.value,
        "reviewer_id": auditor.login,
        "observacion": review_request.observacion,
        "reviewed_at": review_timestamp,
    }

    try:
        record = await run_in_threadpool(gestor.save_review_record, record_payload)
    except Exception as error:
        raise review_exception_to_http(error)

    return AuditoriaReviewResponse.model_validate(record.to_dict())


@router.get(
    "/documents/{document_id}/review-history",
    response_model=list[AuditoriaReviewResponse],
    status_code=status.HTTP_200_OK,
    summary="Consultar historial de revisiones de un documento",
    description="Retorna el historial ordenado de revisiones y decisiones tomadas sobre un documento clínico."
)
async def get_document_review_history(document_id: str):
    """
    S4-01: Recupera todas las revisiones registradas para un documento desde OCI,
    ordenadas cronológicamente por fecha de revisión.
    """
    if not document_id or not document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar un identificador de documento válido."
        )
    document_id = document_id.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{1,128}", document_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identificador de documento inválido."
        )

    try:
        gestor = await run_in_threadpool(OCIStorageManager)
        doc_data = await run_in_threadpool(gestor.recuperar_resultado_triage, document_id)
        history = await run_in_threadpool(gestor.list_reviews_for_document, document_id)
    except Exception as error:
        raise review_exception_to_http(error)

    if doc_data is None and not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento '{document_id}' no encontrado."
        )

    return [AuditoriaReviewResponse.model_validate(item.to_dict()) for item in history]


# Agregado por Edil: se conserva abajo el prototipo de Eliana como referencia.
# No se registra /auditoria/revision: devolvía éxito sin escribir en OCI y usa
# campos que no existen en la solicitud HTTP definitiva. El endpoint real
# de Drazen, /documents/{document_id}/review, persiste mediante Brando.
# from fastapi import APIRouter, HTTPException
# # (Asegúrate de usar el 'router' o 'app' que ya esté definido en tu archivo,
# # generalmente es algo como @router.post o @app.post)
#
# @router.post("/auditoria/revision", summary="Registrar decisión de auditoría humana")
# async def registrar_revision_humana(request: AuditoriaReviewRequest):
#     """
#     Endpoint para que el frontend (Flor) envíe la decisión final
#     de un auditor médico (aprobado/rechazado).
#     """
#     try:
#         # Aquí es donde se conectará la función "save_review()" de Drazen
#         # para guardar en el bucket "auditoria_humana" con el prefijo "reviews/"
#
#         # Simulación de la lógica de OCI esperada para tus pruebas de integración:
#         oci_path = f"reviews/{request.documento_id}/final.json"
#
#         # Si Drazen ya subió su código, aquí llamaríamos a:
#         # await drazen_service.save_review(request)
#
#         return {
#             "status": "exito",
#             "mensaje": f"Revisión guardada en OCI exitosamente.",
#             "datos_auditoria": {
#                 "documento_id": request.documento_id,
#                 "review_status": request.review_status,
#                 "reviewer_id": request.reviewer_id,
#                 "ruta_oci_asignada": oci_path
#             }
#         }
#
#     except ValueError as e:
#         # Atrapa el error si alguien rechaza sin poner observación
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         # Atrapa errores de concurrencia (HTTP 409) o fallos de OCI
#         raise HTTPException(status_code=500, detail=f"Error al guardar revisión: {str(e)}")
