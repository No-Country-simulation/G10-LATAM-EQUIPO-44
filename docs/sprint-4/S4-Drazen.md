# S4-01 — API HTTP de Revisión y Auditoría Humana

**Responsable:** Drazen Gamboa  
**Sprint:** 4  
**Rama:** `feature/s4-drazen-review-api`  
**Fecha:** 21 de octubre de 2026  
**Estado:** Implementación completada, validada contra el cliente OCI de Brando y contrato de Eliana, con 20 pruebas unitarias/integración automatizadas aprobadas.

---

## 1. Resumen de la Entrega

Se implementó la lógica de auditoría y revisión humana en la capa API de MediFlow conectada al gestor de persistencia OCI (`OCIStorageManager`) y a los manejadores de excepciones de dominio:

1. **Esquemas Pydantic ([schemas.py](file:///c:/Users/draze/OneDrive/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/models/schemas.py)):**
   - `ReviewStatus`: Enum con valores `"aprobado"` y `"rechazado"`.
   - `AuditoriaReviewRequest`: Solicitud enviada por el frontend con validadores para `reviewer_id` no vacío, `observacion` obligatoria ante rechazo y `expected_review_status` fijo en `"pendiente"`.
   - `AuditoriaReviewResponse`: Respuesta serializada con los 6 campos definitivos (`documento_id`, `review_id`, `review_status`, `reviewer_id`, `observacion`, `reviewed_at`).
   - `AuditoriaReviewRecord`: Modelo del registro persistible con validaciones de formato de IDs y fechas UTC.

2. **Endpoints HTTP ([routes.py](file:///c:/Users/draze/OneDrive/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/api/routes.py)):**
   - `GET /api/reviews/pending`: Consulta en OCI los documentos en estado `auditoria_humana` que aún no tienen decisión final registrada. Retorna `list[TriageResponse]`.
   - `POST /api/documents/{document_id}/review`: Valida existencia y estado del documento, comprueba que continúe pendiente, genera `review_id` y timestamp UTC (`Z`), y persiste el registro exacto de 6 campos en OCI vía `save_review_record`. Retorna `AuditoriaReviewResponse`.
   - `GET /api/documents/{document_id}/review-history`: Recupera el historial completo de revisiones de un documento ordenado cronológicamente. Retorna `list[AuditoriaReviewResponse]`.

3. **Manejo de Excepciones y Códigos HTTP ([main.py](file:///c:/Users/draze/OneDrive/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/main.py) y [routes.py](file:///c:/Users/draze/OneDrive/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/api/routes.py)):**
   - `400 Bad Request`: Formato de identificador de documento inválido o documento no elegible para auditoría.
   - `404 Not Found`: Documento inexistente o sin revisiones.
   - `409 Conflict`: Intento de registrar una decisión sobre un documento ya auditado o carrera de concurrencia en OCI (HTTP 412 condicional).
   - `422 Unprocessable Entity`: Cuerpos JSON inválidos (rechazo sin observación, auditor vacío, campos no permitidos).
   - `502 Bad Gateway`: Fallo en la comunicación, permisos o persistencia OCI.
   - `504 Gateway Timeout`: Timeout en operaciones OCI.

---

## 2. Detalle de Endpoints Implementados

### 2.1 `GET /api/reviews/pending`
- **Método:** `GET`
- **Ruta:** `/api/reviews/pending`
- **Respuesta 200 OK:**
  ```json
  [
    {
      "status": "auditoria_humana",
      "documento_id": "DOC-PEND-001",
      "clasificacion": {
        "tipo_documento": "Epicrisis clínica",
        "especialidad": "Cardiología",
        "nivel_prioridad": "Urgente",
        "score_confianza_clasificacion": 0.65
      },
      ...
    }
  ]
  ```

### 2.2 `POST /api/documents/{document_id}/review`
- **Método:** `POST`
- **Ruta:** `/api/documents/{document_id}/review`
- **Cuerpo Solicitud:**
  ```json
  {
    "decision": "aprobado",
    "reviewer_id": "auditor_drazen",
    "observacion": "Aprobado tras cotejo clínico",
    "expected_review_status": "pendiente"
  }
  ```
- **Respuesta 200 OK:**
  ```json
  {
    "documento_id": "DOC-CLIN-100",
    "review_id": "REV-20261021T120000Z-a1b2c3d4",
    "review_status": "aprobado",
    "reviewer_id": "auditor_drazen",
    "observacion": "Aprobado tras cotejo clínico",
    "reviewed_at": "2026-10-21T12:00:00Z"
  }
  ```

### 2.3 `GET /api/documents/{document_id}/review-history`
- **Método:** `GET`
- **Ruta:** `/api/documents/{document_id}/review-history`
- **Respuesta 200 OK:**
  ```json
  [
    {
      "documento_id": "DOC-HIST-001",
      "review_id": "REV-001",
      "review_status": "rechazado",
      "reviewer_id": "auditor_01",
      "observacion": "Falta firma del médico tratante.",
      "reviewed_at": "2026-10-20T10:00:00Z"
    },
    {
      "documento_id": "DOC-HIST-001",
      "review_id": "REV-002",
      "review_status": "aprobado",
      "reviewer_id": "auditor_02",
      "observacion": "Documento rectificado y aprobado.",
      "reviewed_at": "2026-10-21T11:00:00Z"
    }
  ]
  ```

---

## 3. Pruebas Automatizadas

Se crearon 20 pruebas en [test_review_api.py](file:///c:/Users/draze/OneDrive/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/tests/test_review_api.py) cubriendo el 100% de los escenarios contractuales y de borde:

```bash
cd mediflow/backend
$env:PYTHONPATH="."
.venv/Scripts/python.exe -m pytest tests/test_review_api.py -v
```

Resultado: **20 passed in 1.90s**.  
Suite completa backend: **362 passed, 6 skipped in 5.16s** (cero regresiones).
