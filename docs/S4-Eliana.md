# MediFlow — Contrato JSON de Auditoría Humana
**Sprint 4 | Catálogo de campos y valores permitidos**

**Responsable del contrato:** Eliana — S4-03  
**Tecnología:** FastAPI / Pydantic / OCI Object Storage  
**Versión:** 1.0 — 20/10/2026

---

## 1. Objetivo

Definir el formato JSON y el catálogo de valores permitidos para intercambiar información de auditoría humana entre el frontend, el backend y OCI Object Storage.

El contrato contempla dos estructuras:

1. **`AuditoriaReviewRequest`:** solicitud enviada por el frontend.
2. **`AuditoriaReviewRecord`:** registro completo generado por el backend para su almacenamiento en OCI.

## 2. Contrato JSON de solicitud HTTP

**Método:** `POST`  
**Endpoint:** `/api/documents/{id}/review`  
**Content-Type:** `application/json`

### Ejemplo: documento aprobado

```json
{
  "decision": "aprobado",
  "reviewer_id": "auditor_demo_01",
  "observacion": "Documento revisado correctamente",
  "expected_review_status": "pendiente"
}
```

### Ejemplo: documento rechazado

```json
{
  "decision": "rechazado",
  "reviewer_id": "auditor_demo_01",
  "observacion": "Documento ilegible",
  "expected_review_status": "pendiente"
}
```

### Catálogo de campos — Solicitud HTTP

| Campo | Tipo JSON | Obligatorio | Valores / reglas |
|---|---|---|---|
| `decision` | string | Sí | `aprobado`, `rechazado` |
| `reviewer_id` | string | Sí | Identificador no vacío del auditor |
| `observacion` | string / null | Condicional | Obligatoria si `decision = rechazado` |
| `expected_review_status` | string | Sí | `pendiente` |

**Regla:** `documento_id` se obtiene desde `{id}` en la URL, no desde el cuerpo JSON.

## 3. Contrato JSON de registro OCI

**Modelo:** `AuditoriaReviewRecord`

### Ejemplo de registro

```json
{
  "documento_id": "DOC-CLIN-ABC123",
  "review_id": "REV-20261020T153000Z-a1b2c3d4",
  "review_status": "aprobado",
  "reviewer_id": "auditor_demo_01",
  "observacion": "Documento revisado correctamente",
  "reviewed_at": "2026-10-20T15:30:00Z"
}
```

### Catálogo de campos — Registro OCI

| Campo | Tipo JSON | Obligatorio | Valores / reglas |
|---|---|---|---|
| `documento_id` | string | Sí | ID único del documento |
| `review_id` | string | Sí | ID único generado por el backend |
| `review_status` | string | Sí | `aprobado`, `rechazado` |
| `reviewer_id` | string | Sí | Identificador del auditor |
| `observacion` | string / null | Condicional | Obligatoria si se rechaza |
| `reviewed_at` | string | Sí | Fecha ISO 8601 con zona horaria UTC |

El backend genera `review_id` y `reviewed_at`. El frontend no debe enviarlos en la solicitud HTTP.

## 4. Catálogo de estados

### CAT-01 — Decisión de auditoría (`ReviewStatus`)

| Código | Descripción | Decisión final |
|---|---|---|
| `aprobado` | El auditor acepta el documento | Sí |
| `rechazado` | El auditor rechaza el documento | Sí |

**Valores no permitidos:** `solicitar_nueva_imagen`, `urgente`, `procesado` y cualquier otro valor no definido en este catálogo.

### CAT-02 — Estado esperado (`expected_review_status`)

| Código | Descripción |
|---|---|
| `pendiente` | El documento todavía no tiene una decisión final registrada |

`pendiente` no es una decisión del auditor. Es el estado esperado antes de registrar la revisión.

### CAT-03 — Formato de identificadores

| Campo | Formato | Ejemplo |
|---|---|---|
| `documento_id` | Identificador asignado por MediFlow | `DOC-CLIN-ABC123` |
| `review_id` | `REV-AAAAMMDDTHHMMSSZ-8hex` | `REV-20261020T153000Z-a1b2c3d4` |
| `reviewer_id` | Identificador del auditor | `auditor_demo_01` |

El esquema Pydantic actual exige cadenas no vacías, pero no valida mediante expresiones regulares los formatos anteriores.

### CAT-04 — Fecha y hora

| Campo | Formato | Ejemplo |
|---|---|---|
| `reviewed_at` | ISO 8601 UTC | `2026-10-20T15:30:00Z` |

La fecha es generada por el backend y debe incluir una zona horaria UTC válida.

## 5. Reglas de validación

| ID | Regla |
|---|---|
| VAL-01 | `decision` solo admite `aprobado` o `rechazado` |
| VAL-02 | `reviewer_id` debe contener al menos un carácter |
| VAL-03 | Si la decisión es `rechazado`, `observacion` es obligatoria |
| VAL-04 | Una observación de rechazo no puede contener únicamente espacios |
| VAL-05 | `expected_review_status` debe ser `pendiente` |
| VAL-06 | `documento_id` y `review_id` deben contener al menos un carácter |
| VAL-07 | `reviewed_at` debe incluir zona horaria UTC |
| VAL-08 | El backend debe comprobar el estado real antes de persistir una decisión |
| VAL-09 | No se permite sobrescribir una decisión final existente |

Las reglas VAL-08 y VAL-09 requieren implementación en backend y OCI; no quedan garantizadas únicamente por los modelos Pydantic.

## 6. Catálogo de almacenamiento OCI

**Bucket:** `auditoria_humana`

| Objeto | Ruta | Finalidad |
|---|---|---|
| Historial de revisión | `reviews/{documento_id}/{review_id}.json` | Conservar el registro individual |
| Decisión final | `reviews/{documento_id}/final.json` | Conservar la única decisión final |

La creación de `final.json` debe utilizar escritura condicional `If-None-Match: *` para impedir sobrescrituras.

## 7. Catálogo de respuestas HTTP esperadas

| Código HTTP | Significado |
|---|---|
| `200` / `201` | Revisión registrada exitosamente |
| `400` | Solicitud inválida según reglas de negocio |
| `401` | Usuario no autenticado |
| `403` | Usuario sin autorización |
| `404` | Documento inexistente |
| `409` | El documento ya tiene una decisión final |
| `422` | Error de validación del JSON |
| `5xx` | Error interno o fallo de dependencia |

Estos códigos representan el comportamiento esperado para las pruebas de integración. El formato JSON exacto de las respuestas debe verificarse con la implementación de Drazen.

## 8. Correspondencia entre contratos

| Solicitud HTTP | Registro OCI |
|---|---|
| `{id}` en URL | `documento_id` |
| `decision` | `review_status` |
| `reviewer_id` | `reviewer_id` |
| `observacion` | `observacion` |
| `expected_review_status` | Validación previa; no se almacena como campo del registro |
| Generado por backend | `review_id` |
| Generado por backend | `reviewed_at` |

## 9. Alcance del contrato

Este contrato se limita a la revisión humana y **no modifica**:

- La clasificación clínica del documento.
- La prioridad `Rutina` o `Urgente`.
- El resultado original de `TriageResponse`.
- La extracción de datos clínicos.
- El enrutamiento original del documento.

**Nota de integración:** este documento refleja los dos modelos definidos para `schemas.py` y las propuestas de interfaz y persistencia del Sprint 4. La implementación efectiva de los endpoints y su compatibilidad deben verificarse durante las pruebas de integración.

---

**Fin del contrato JSON — MediFlow Sprint 4.**