# CONTRATO JSON DE AUDITORÍA HUMANA — SPRINT 4

**Proyecto:** MediFlow  
**Sprint:** 4  
**Responsable del contrato:** Eliana — S4-03 Integración y contratos JSON  
**Fecha de actualización:** 20 de octubre de 2026  
**Estado:** Contrato actualizado según la implementación de persistencia OCI de Brando. Integración HTTP pendiente de validación conjunta.

---

## 1. Objetivo

Definir el contrato JSON utilizado en el proceso de auditoría humana de documentos clínicos que requieren revisión.

El contrato establece:

- Los datos enviados por el frontend al backend.
- Las validaciones obligatorias de una decisión de auditoría.
- El registro definitivo que el backend debe almacenar en Oracle Cloud Infrastructure (OCI).
- Las rutas de almacenamiento y las reglas para evitar decisiones duplicadas.
- Los criterios de integración y pruebas entre frontend, API y persistencia OCI.

Este documento sirve como referencia compartida para Edil (frontend e integración), Drazen (backend), Brando (OCI), María (QA) y Eliana (contratos e integración).

## 2. Flujo funcional

1. MediFlow procesa un documento y determina si requiere auditoría humana.
2. El documento queda disponible en la cola de revisión.
3. Un auditor consulta el documento y selecciona **aprobar** o **rechazar**.
4. El frontend envía la decisión al backend mediante una solicitud HTTP.
5. El backend valida la solicitud y comprueba que el documento continúa pendiente.
6. El backend genera los datos de identificación y fecha de la revisión.
7. El backend solicita a OCI la persistencia del registro definitivo.
8. La API informa el resultado de la operación.

**Regla principal:** un documento solo puede tener una decisión final. Una vez aprobado o rechazado, no debe volver a registrarse una decisión definitiva mediante el mismo flujo.

## 3. Estados de auditoría

| Estado | Descripción |
|---|---|
| `pendiente` | El documento todavía no tiene una decisión final de auditoría. |
| `aprobado` | El auditor aprobó el documento. |
| `rechazado` | El auditor rechazó el documento. |

`pendiente` es el estado inicial de revisión. No constituye una decisión final y, por tanto, no es un valor permitido en el campo `decision` de la solicitud ni en `review_status` del registro definitivo.

Los valores finales permitidos son exclusivamente `aprobado` y `rechazado`.

## 4. Contrato HTTP: solicitud de auditoría

**Endpoint previsto:** `POST /api/documents/{documento_id}/review`

El frontend debe enviar un objeto JSON con los siguientes campos:

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `decision` | string | Sí | `aprobado` o `rechazado` |
| `reviewer_id` | string | Sí | Identificador no vacío ni compuesto únicamente por espacios |
| `observacion` | string o null | No, salvo rechazo | Obligatoria y no vacía cuando `decision` es `rechazado` |
| `expected_review_status` | string | Sí | Valor fijo `pendiente` |

El identificador `documento_id` se proporciona en la ruta HTTP, no en el cuerpo de la solicitud.

### 4.1 Ejemplo de aprobación

```json
{
  "decision": "aprobado",
  "reviewer_id": "auditor_demo_01",
  "observacion": "Documento sintético revisado",
  "expected_review_status": "pendiente"
}
```

La observación de una aprobación puede ser `null` o una cadena de texto.

### 4.2 Ejemplo de rechazo

```json
{
  "decision": "rechazado",
  "reviewer_id": "auditor_demo_01",
  "observacion": "El documento presenta información insuficiente para su validación.",
  "expected_review_status": "pendiente"
}
```

### 4.3 Ejemplo inválido

```json
{
  "decision": "rechazado",
  "reviewer_id": "auditor_demo_01",
  "observacion": null,
  "expected_review_status": "pendiente"
}
```

La solicitud debe rechazarse porque una decisión `rechazado` exige una observación con contenido.

### 4.4 Validaciones

El backend debe comprobar:

- Que `decision` pertenezca al catálogo permitido.
- Que `reviewer_id` no esté vacío ni contenga solamente espacios.
- Que `observacion` tenga contenido cuando la decisión sea `rechazado`.
- Que `expected_review_status` sea exactamente `pendiente`.
- Que el documento exista y se encuentre disponible para revisión.
- Que el estado real del documento continúe pendiente antes de registrar la decisión.
- Que el usuario esté autorizado para ejecutar la operación, según las reglas de autenticación y autorización de la API.

El campo `reviewer_id` identifica al auditor en el registro, pero **no sustituye la autenticación ni la autorización del backend**.

## 5. Contrato OCI: registro definitivo de auditoría

Una vez validada la solicitud, el backend debe construir el registro definitivo que se enviará al componente de persistencia OCI.

El registro contiene **exactamente seis campos**.

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `documento_id` | string | Sí | Entre 1 y 128 caracteres; letras, números, `_` y `-` |
| `review_id` | string | Sí | Identificador válido de revisión |
| `review_status` | string | Sí | `aprobado` o `rechazado` |
| `reviewer_id` | string | Sí | Identificador no vacío ni compuesto únicamente por espacios |
| `observacion` | string o null | Sí | Obligatoria con contenido para un rechazo; puede ser `null` para aprobación |
| `reviewed_at` | string | Sí | Fecha y hora ISO 8601 UTC terminada en `Z` |

No deben enviarse campos adicionales al registro OCI.

### 5.1 Ejemplo de registro aprobado

```json
{
  "documento_id": "DOC-CLIN-ABC123",
  "review_id": "REV-20261020T153000Z-a1b2c3d4",
  "review_status": "aprobado",
  "reviewer_id": "auditor_demo_01",
  "observacion": null,
  "reviewed_at": "2026-10-20T15:30:00Z"
}
```

### 5.2 Ejemplo de registro rechazado

```json
{
  "documento_id": "DOC-CLIN-ABC124",
  "review_id": "REV-20261020T154000Z-b2c3d4e5",
  "review_status": "rechazado",
  "reviewer_id": "auditor_demo_02",
  "observacion": "El documento contiene información insuficiente.",
  "reviewed_at": "2026-10-20T15:40:00Z"
}
```

Los identificadores y las fechas anteriores son ejemplos sintéticos, no registros de producción.

## 6. Catálogo y formatos de identificadores

### 6.1 `documento_id`

Patrón permitido:

```text
[A-Za-z0-9_-]{1,128}
```

Ejemplos válidos:

- `DOC-CLIN-ABC123`
- `documento_001`
- `ABC123`

No se permiten espacios, barras de ruta ni caracteres fuera del patrón indicado.

### 6.2 `review_id`

La implementación OCI acepta:

**Formato con prefijo `REV-`:**

```text
REV-[A-Za-z0-9_-]{1,64}
```

**O un identificador UUID versión 4.**

Ejemplos:

```text
REV-001
REV-20261020T153000Z-a1b2c3d4
```

El formato con fecha y sufijo es un ejemplo válido, pero no constituye un requisito obligatorio. El backend es responsable de generar un identificador compatible.

### 6.3 `reviewed_at`

El registro enviado a OCI debe contener una fecha ISO 8601 en UTC, representada como cadena y terminada en `Z`.

Ejemplo válido:

```text
2026-10-20T15:30:00Z
```

El formato con sufijo `+00:00` no debe enviarse a OCI, aunque represente la misma zona horaria.

El modelo Pydantic puede trabajar internamente con un objeto `datetime` en UTC. Antes de persistir, el backend debe serializarlo al formato aceptado por OCI.

## 7. Transformación del contrato HTTP al registro OCI

El backend debe transformar los campos de la solicitud de la siguiente manera:

| Origen | Destino OCI | Responsable |
|---|---|---|
| Parámetro de ruta `documento_id` | `documento_id` | Backend |
| Generación interna | `review_id` | Backend |
| `decision` | `review_status` | Backend |
| `reviewer_id` | `reviewer_id` | Backend |
| `observacion` | `observacion` | Backend |
| Fecha y hora UTC generada | `reviewed_at` | Backend |

`expected_review_status` se utiliza para comprobar el estado esperado de la revisión y **no debe almacenarse** dentro del registro OCI.

El frontend no debe generar `review_id` ni `reviewed_at`.

## 8. Persistencia en OCI

**Bucket de auditoría:** `auditoria_humana`

La implementación de Brando utiliza dos objetos para una revisión definitiva.

### 8.1 Registro final

```text
reviews/{documento_id}/_final.json
```

Ejemplo:

```text
reviews/DOC-CLIN-ABC123/_final.json
```

Este objeto representa la decisión final del documento.

La implementación utiliza una escritura condicional de OCI con `if_none_match="*"`, de modo que no se sobrescriba un registro final existente.

### 8.2 Copia por identificador de revisión

```text
reviews/{documento_id}/{review_id}.json
```

Ejemplo:

```text
reviews/DOC-CLIN-ABC123/REV-20261020T153000Z-a1b2c3d4.json
```

El objeto por `review_id` contiene el mismo registro serializado que `_final.json`.

### 8.3 Orden de escritura

La implementación de Brando escribe primero `_final.json` y posteriormente el objeto identificado por `review_id`.

Si `_final.json` ya existe, OCI puede responder con un error de precondición `412`. La API debe tratarlo como un intento de registrar una decisión duplicada.

**Consideración de integración:** si la escritura de `_final.json` se completa y falla la escritura de la copia por `review_id`, el documento ya puede tener una decisión final persistida. El backend debe manejar ese escenario sin asumir que ambas escrituras se revirtieron automáticamente.

## 9. Operaciones disponibles en el componente OCI

Brando implementó las siguientes operaciones de persistencia y consulta:

| Operación | Finalidad |
|---|---|
| `save_review_record(record)` | Guardar un registro definitivo |
| `get_review_record(documento_id, review_id)` | Recuperar una revisión específica |
| `list_reviews_for_document(documento_id)` | Listar revisiones de un documento |
| `get_latest_review_status(documento_id)` | Obtener el estado actual de revisión |
| `list_pending_reviews()` | Obtener documentos pendientes de auditoría |

La función `get_latest_review_status` utiliza la existencia del registro final para distinguir entre `pendiente` y una decisión definitiva.

La función `list_pending_reviews` está orientada a construir la cola de auditoría humana, excluyendo documentos que ya tienen una decisión final.

Estas son operaciones internas del componente OCI; **no deben confundirse con endpoints HTTP ya verificados**.

## 10. Endpoints HTTP previstos para integración

| Método | Endpoint | Función |
|---|---|---|
| `GET` | `/api/reviews/pending` | Consultar documentos pendientes |
| `POST` | `/api/documents/{documento_id}/review` | Registrar una decisión de auditoría |
| `GET` | `/api/documents/{documento_id}/review-history` | Consultar historial de revisiones, si se habilita |

La disponibilidad, las respuestas y el comportamiento de estos endpoints deben comprobarse con la implementación de Drazen.

La cola de auditoría debe utilizar la lógica específica de documentos pendientes, no asumir que todos los documentos con estado de triaje `auditoria_humana` siguen sin decisión final.

## 11. Manejo de errores esperado

La siguiente tabla establece el comportamiento de integración recomendado. Los códigos HTTP deben verificarse contra los endpoints reales.

| Situación | HTTP esperado |
|---|---|
| Solicitud con campos inválidos | `422` |
| Documento o revisión inexistente | `404` |
| Documento con decisión final existente | `409` |
| Error de autenticación | `401` |
| Usuario sin permisos | `403` |
| Error de autenticación, permisos o persistencia OCI | `502` |
| Tiempo de espera agotado en OCI | `504` |

La escritura duplicada de `_final.json` debe impedir que se sobrescriba una decisión existente.

Una respuesta exitosa de la API debe representar una persistencia confirmada conforme a la política de éxito definida para las escrituras OCI. No debe informarse éxito antes de conocer el resultado de la operación.

## 15. Criterio de aceptación del contrato

El contrato se considerará integrado cuando:

1. El frontend pueda enviar una decisión válida utilizando el contrato HTTP definido.
2. El backend valide correctamente los campos y el estado previo del documento.
3. El backend genere un registro de exactamente seis campos compatible con OCI.
4. OCI persista y permita recuperar la decisión final.
5. Una segunda decisión no sobrescriba la primera.
6. La consulta de pendientes excluya documentos ya revisados.
7. Las pruebas de integración estén ejecutadas y sus resultados documentados.

---

**Conclusión:** este documento define el contrato JSON compartido para el Sprint 4 de MediFlow y refleja las reglas de persistencia OCI implementadas por Brando. La validación final depende de las pruebas de integración entre los componentes del equipo.