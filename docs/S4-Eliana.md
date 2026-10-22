# CONTRATO JSON DE AUDITORÍA HUMANA — SPRINT 4

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

## 10. Endpoints HTTP de integración

| Método | Endpoint | Función |
|---|---|---|
| `GET` | `/api/reviews/pending` | Consultar documentos pendientes |
| `POST` | `/api/documents/{documento_id}/review` | Registrar una decisión de auditoría |
| `GET` | `/api/documents/{documento_id}/review-history` | Consultar historial de revisiones |

Los tres endpoints fueron ejecutados mediante FastAPI TestClient contra la implementación HTTP de Drazen, utilizando OCI real para el escenario E2E de aprobación. Se verificaron respuestas HTTP 200 en las consultas y el registro de aprobación, además de HTTP 409 ante un segundo intento de decisión final. El rechazo E2E y la exclusión de documentos revisados de la cola fueron validados posteriormente mediante HTTP y OCI real.

La cola de auditoría debe utilizar la lógica específica de documentos pendientes, no asumir que todos los documentos con estado de triaje `auditoria_humana` siguen sin decisión final.

## 11. Manejo de errores esperado

La siguiente tabla establece los códigos HTTP esperados. En la prueba E2E de aprobación se verificó HTTP 409 para una segunda decisión final; los demás escenarios de error requieren evidencia específica antes de considerarse validados.

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

**Conclusión:** el contrato JSON compartido del Sprint 4 cuenta con evidencia E2E satisfactoria para el escenario de aprobación, incluyendo endpoints HTTP, persistencia OCI real, historial y prevención de decisiones duplicadas. Las pruebas E2E de rechazo y exclusión de revisados fueron completadas satisfactoriamente. La aceptación integral continúa pendiente de la integración de auditoría humana con frontend y demás validaciones aplicables.

---

## 16. Evidencias de integración E2E — 21 de octubre de 2026

**Responsable:** Eliana — S4-03

**Entorno:** Backend local, FastAPI TestClient y OCI Object Storage real.

**Resultado:** PASS para el escenario de aprobación.

### 16.1 Pruebas ejecutadas

| Verificación | Resultado |
|---|---|
| Validación del contrato `TriageResponse` | PASS |
| Almacenamiento y recuperación del documento en OCI | PASS |
| `GET /api/reviews/pending` | HTTP 200 |
| `POST /api/documents/{id}/review` | HTTP 200 |
| Persistencia de decisión `aprobado` en OCI | PASS |
| Existencia de `_final.json` y copia por `review_id` | PASS |
| `GET /api/documents/{id}/review-history` | HTTP 200 |
| Segunda aprobación del mismo documento | HTTP 409 |
| Historial sin duplicados | PASS — 1 revisión |
| Limpieza de objetos sintéticos | PASS — 3/3 eliminados y ausencia confirmada con HTTP 404 |

### 16.2 Identificadores de prueba

- Documento sintético: `DOC-S4-E2E-1796FA11CDE14DCF`
- Revisión: `REV-20261021T234111Z-ef731fdb`
- Auditor sintético: `auditor_s4_e2e`
- Estado final verificado: `aprobado`
- Bucket OCI: `auditoria_humana`

Los objetos sintéticos fueron eliminados después de las pruebas.

### 16.3 Pruebas automatizadas

- Pruebas HTTP de auditoría: **20 passed**.
- Suite general: **315 passed, 6 skipped**.
- Los seis casos omitidos no se consideran aprobados.

### 16.4 Alcance y pendientes

La prueba confirmó el funcionamiento del flujo de aprobación
entre los endpoints HTTP y la persistencia OCI.

Validaciones E2E completadas posteriormente:

1. Rechazo de documentos mediante HTTP y OCI real: PASS.
2. Exclusión de documentos revisados de la cola de pendientes: PASS.

**Matriz de evidencias:** `sprint-4/MATRIZ-PRUEBAS-S4-03.md`.

**Conclusión:** escenario E2E de aprobación aprobado. No se declara
completada la integración integral del Sprint 4.


## 17. Actualización de evidencias S4-03

### 17.1 Escenarios E2E adicionales

**Resultado: PASS.**

- Rechazo HTTP con persistencia OCI real: PASS.
- Exclusión de documentos aprobados de la cola: PASS.
- Exclusión de documentos rechazados de la cola: PASS.
- Consulta de historial de revisiones: HTTP 200.
- Prevención de segunda decisión final: HTTP 409.
- Limpieza de objetos sintéticos: verificada mediante HTTP 404.

Los identificadores, verificaciones y objetos eliminados están
documentados en `sprint-4/MATRIZ-PRUEBAS-S4-03.md`.

### 17.2 Pruebas del frontend web

Comando ejecutado:

`node --test ../frontend_web/tests/*.test.js`

**Resultado: 40 PASS, 0 FAIL, 0 SKIP.**

La suite cubre consultas HTTP de documentos, validación JSON,
detalle individual, manejo de errores e historial general.

Estas pruebas no demuestran una integración E2E de la pantalla
de auditoría humana con FastAPI y OCI.

### 17.3 Integración frontend — S4-03-17

**Estado: PENDIENTE.**

La inspección del frontend web confirmó que el historial general
utiliza una API real por defecto, mientras que la pantalla de
auditoría utiliza documentos de ejemplo y registra decisiones
en memoria.

Se requiere que las personas encargadas del frontend revisen la conexión y
validación de:

- `GET /api/reviews/pending`.
- `POST /api/documents/{documento_id}/review`.
- `GET /api/documents/{documento_id}/review-history`.
- Manejo de errores HTTP y conflictos 409.
- Confirmación visual únicamente después de persistencia exitosa.

**Conclusión actualizada:** los escenarios E2E de aprobación,
rechazo, historial y exclusión de pendientes están verificados
con OCI real. La integración integral del Sprint 4 permanece
pendiente de S4-03-17 y las validaciones restantes.




flowchart TD
    A["Ingesta de documento<br/>Archivo + cargado_por"] --> B["Procesamiento IA<br/>Extracción y clasificación"]
    B --> C["Almacenamiento OCI<br/>Resultado JSON"]
    C --> D{"¿Requiere auditoría humana?"}
    D -->|No| E["Documento procesado"]
    D -->|Sí| F["Cola de auditoría<br/>GET /api/reviews/pending"]
    F --> G["Panel de auditoría frontend"]
    G --> H["POST /api/documents/{id}/review"]
    H --> I{"Resultado HTTP"}
    I -->|200| J["Decisión registrada en OCI"]
    I -->|409| K["Conflicto: consultar estado actual"]
    I -->|Otros errores| L["Mostrar error y verificar estado"]
    J --> M["GET /api/documents/{id}/review-history"]
    M --> N["Actualizar interfaz e historial"]

    classDef verified fill:#e5f4e9,stroke:#38976c,color:#194f38
    classDef pending fill:#fff0d6,stroke:#d19a39,color:#765018

    class F,H,J,M verified
    class A,G,N pending
