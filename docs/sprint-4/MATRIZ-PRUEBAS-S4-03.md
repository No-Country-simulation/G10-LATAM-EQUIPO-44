# MATRIZ DE PRUEBAS S4-03 — INTEGRACIÓN Y CONTRATOS JSON

## 1. Objetivo

Validar la integración entre los endpoints HTTP de auditoría humana,
los contratos JSON y la persistencia real en OCI.

## 2. Resultados de pruebas

| ID | Prueba | Resultado | Evidencia |
|---|---|---|---|
| S4-03-01 | Validación de TriageResponse | PASS | Pydantic valida documento sintético |
| S4-03-02 | Guardar documento en OCI | PASS | guardar_resultado_triage sin errores |
| S4-03-03 | Recuperar documento desde OCI | PASS | Identificador y estado correctos |
| S4-03-04 | GET /api/reviews/pending | PASS | HTTP 200 |
| S4-03-05 | POST /api/documents/{id}/review | PASS | HTTP 200, aprobado |
| S4-03-06 | Persistencia de decisión final | PASS | Estado OCI aprobado |
| S4-03-07 | Existencia de _final.json | PASS | OCI head_object exitoso |
| S4-03-08 | Existencia de copia por review_id | PASS | OCI head_object exitoso |
| S4-03-09 | GET /api/documents/{id}/review-history | PASS | HTTP 200, una revisión |
| S4-03-10 | Protección contra segunda aprobación | PASS | HTTP 409 |
| S4-03-11 | Historial sin duplicados | PASS | Una revisión registrada |
| S4-03-12 | Limpieza de objetos sintéticos | PASS | 3/3 objetos ausentes, HTTP 404 |
| S4-03-13 | Pruebas HTTP automatizadas | PASS | 20 passed |
| S4-03-14 | Suite completa de pruebas | PASS | 315 passed, 6 skipped |
| S4-03-15 | Rechazo mediante HTTP y OCI real | PASS | E2E: rechazo HTTP 200, persistencia OCI, historial, exclusión de pendientes, HTTP 409 y limpieza 3/3 |
| S4-03-16 | Exclusión de revisados de pendientes | PASS | E2E OCI real: visible antes, excluido después de aprobar; limpieza 3/3 verificada |
| S4-03-17 | Integración con frontend | PENDIENTE | No ejecutada en esta sesión |

## 3. Identificadores de la prueba E2E

- Documento: DOC-S4-E2E-1796FA11CDE14DCF
- Revisión: REV-20261021T234111Z-ef731fdb
- Auditor sintético: auditor_s4_e2e
- Decisión: aprobado
- Bucket: auditoria_humana

## 4. Persistencia OCI

Se verificó la existencia de:

- DOC-S4-E2E-1796FA11CDE14DCF.json
- reviews/DOC-S4-E2E-1796FA11CDE14DCF/_final.json
- reviews/DOC-S4-E2E-1796FA11CDE14DCF/REV-20261021T234111Z-ef731fdb.json

Los tres objetos fueron eliminados posteriormente.
La ausencia se confirmó mediante respuestas HTTP 404.

## 5. Prueba E2E de exclusión de pendientes

**Resultado: PASS — S4-03-16**

- Documento sintético: DOC-S4-COLA-0280057D51FF
- Revisión: REV-20261022T002445Z-704b0b11
- Auditor sintético: auditor_s4_e2e
- Decisión: aprobado
- Bucket OCI: auditoria_humana

Verificaciones realizadas:

1. Documento sintético creado correctamente en OCI.
2. GET /api/reviews/pending: HTTP 200; documento presente.
3. POST /api/documents/{document_id}/review: HTTP 200; aprobación registrada.
4. GET /api/reviews/pending: HTTP 200; documento aprobado ausente.
5. GET /api/documents/{document_id}/review-history: HTTP 200.
6. Limpieza confirmada mediante head_object: 3/3 objetos ausentes (HTTP 404).

Objetos sintéticos eliminados:

- DOC-S4-COLA-0280057D51FF.json
- reviews/DOC-S4-COLA-0280057D51FF/_final.json
- reviews/DOC-S4-COLA-0280057D51FF/REV-20261022T002445Z-704b0b11.json

La prueba confirma que una aprobación final excluye el documento
de la cola de pendientes. La limpieza de OCI quedó verificada.

## 6. Prueba E2E de rechazo

**Resultado: PASS — S4-03-15**

- Documento sintético: DOC-S4-RECHAZO-A9A199EF5815
- Revisión: REV-20261022T003230Z-8bc2f746
- Auditor sintético: auditor_s4_e2e
- Decisión: rechazado
- Bucket OCI: auditoria_humana

Verificaciones realizadas:

1. Documento sintético creado correctamente en OCI.
2. GET /api/reviews/pending: HTTP 200; documento presente.
3. POST /api/documents/{document_id}/review: HTTP 200; rechazo registrado.
4. Persistencia OCI: decisión rechazado recuperada correctamente.
5. GET /api/reviews/pending: HTTP 200; documento rechazado ausente.
6. GET /api/documents/{document_id}/review-history: HTTP 200; una revisión.
7. Segunda decisión bloqueada: HTTP 409.

Objetos sintéticos eliminados y ausencia confirmada mediante head_object (HTTP 404):

- DOC-S4-RECHAZO-A9A199EF5815.json
- reviews/DOC-S4-RECHAZO-A9A199EF5815/_final.json
- reviews/DOC-S4-RECHAZO-A9A199EF5815/REV-20261022T003230Z-8bc2f746.json

Limpieza verificada: 3/3 objetos ausentes.

## 7. Verificación del frontend web

**Resultado: PASS — suite existente (40/40 pruebas).**

Comando ejecutado desde mediflow/backend:

`node --test ../frontend_web/tests/*.test.js`

Resultados:

- Pruebas ejecutadas: 40.
- Aprobadas: 40.
- Fallidas: 0.
- Omitidas: 0.
- Duración total: 355,53 ms.

La suite verifica consultas HTTP de documentos, detalle individual,
validación de contratos JSON, manejo de errores, respuestas tardías
y funcionamiento del historial general.

Incluye una prueba HTTP con servidor local, pero no constituye una
prueba E2E del frontend contra FastAPI y OCI.

### S4-03-17 — Integración de auditoría humana

**Resultado: PENDIENTE.**

Hallazgos de inspección del código:

- El historial general utiliza la API real por defecto.
- El modo demostración del historial se activa con `?demo=1`.
- La pantalla de auditoría utiliza documentos de ejemplo.
- Las decisiones de aprobación y rechazo se registran en memoria.
- No se identificó conexión de la pantalla de auditoría con los
  endpoints de pendientes, revisión e historial de revisiones.

Pendiente de coordinación personas asignadas a frontend:

1. Consultar `GET /api/reviews/pending`.
2. Enviar aprobaciones y rechazos mediante
   `POST /api/documents/{document_id}/review`.
3. Consultar `GET /api/documents/{document_id}/review-history`.
4. Confirmar visualmente una decisión solo después del éxito HTTP.
5. Manejar HTTP 409 y errores sin retirar indebidamente el documento.
6. Ejecutar pruebas de integración frontend–FastAPI–OCI.

## 8. Conclusión

**PASS:** escenarios E2E de aprobación y rechazo con OCI real,
consulta de historial, bloqueo de decisiones duplicadas mediante
HTTP 409 y exclusión de documentos revisados de la cola de pendientes.

**PASS:** suite automatizada existente del frontend web (40/40).

**PENDIENTE:** S4-03-17, integración funcional de la pantalla de
auditoría humana con los endpoints reales y validación E2E desde
frontend.

Las pruebas OCI utilizaron documentos sintéticos. Los objetos
generados fueron eliminados y su ausencia fue verificada.

No se modificó código de otros integrantes durante estas pruebas.
