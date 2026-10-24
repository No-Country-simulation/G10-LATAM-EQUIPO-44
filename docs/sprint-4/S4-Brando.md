# S4 — Persistencia de revisiones humanas en OCI

**Generado:** 2026-10-19  
**Estado:** implementación local validada y evidencia OCI real documentada.  
**Nota:** las líneas de este documento fueron obtenidas del estado actual del
código mediante `grep -n`; si el código cambia, deben regenerarse.

## 1. Diseño, claves y contrato

La clase [`OCIStorageManager`](/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/core/oci_client.py:223)
persiste revisiones en el bucket `auditoria_humana`. El registro tiene
exactamente seis campos:

```json
{
  "documento_id": "DOC-123",
  "review_id": "REV-001",
  "review_status": "aprobado",
  "reviewer_id": "auditor-01",
  "observacion": null,
  "reviewed_at": "2026-10-19T18:00:00Z"
}
```

`review_status` es `aprobado` o `rechazado`; una revisión rechazada requiere
una observación. `reviewed_at` debe ser UTC ISO 8601 con `Z`.

Las claves son:

- Fuente de verdad: `reviews/{documento_id}/_final.json`.
- Espejo por revisión: `reviews/{documento_id}/{review_id}.json`.

Las cinco firmas implementadas son:

| Firma | Línea | Función |
|---|---:|---|
| `save_review_record(record: Mapping[str, Any]) -> ReviewRecord` | 252 | Validar y escribir la decisión final y el espejo. |
| `get_review_record(documento_id: str, review_id: str) -> ReviewRecord` | 311 | Leer una revisión concreta. |
| `list_reviews_for_document(documento_id: str) -> list[ReviewRecord]` | 331 | Leer la decisión final y sumar espejos distintos, ordenados por fecha. |
| `get_latest_review_status(documento_id: str) -> str` | 380 | Obtener `pendiente`, `aprobado` o `rechazado`. |
| `list_pending_reviews() -> list[dict]` | 406 | Listar triajes en auditoría sin decisión final. |

Ejemplos JSON de entrada/salida para las cinco funciones:

```json
{
  "save_review_record": {
    "input": {
      "documento_id": "DOC-123",
      "review_id": "REV-001",
      "review_status": "aprobado",
      "reviewer_id": "auditor-01",
      "observacion": null,
      "reviewed_at": "2026-10-19T18:00:00Z"
    },
    "output": {
      "documento_id": "DOC-123",
      "review_id": "REV-001",
      "review_status": "aprobado",
      "reviewer_id": "auditor-01",
      "observacion": null,
      "reviewed_at": "2026-10-19T18:00:00Z"
    }
  },
  "get_review_record": {
    "input": {
      "documento_id": "DOC-123",
      "review_id": "REV-001"
    },
    "output": {
      "documento_id": "DOC-123",
      "review_id": "REV-001",
      "review_status": "aprobado",
      "reviewer_id": "auditor-01",
      "observacion": null,
      "reviewed_at": "2026-10-19T18:00:00Z"
    }
  },
  "list_reviews_for_document": {
    "input": {"documento_id": "DOC-123"},
    "output": [
      {
        "documento_id": "DOC-123",
        "review_id": "REV-001",
        "review_status": "aprobado",
        "reviewer_id": "auditor-01",
        "observacion": null,
        "reviewed_at": "2026-10-19T18:00:00Z"
      }
    ]
  },
  "get_latest_review_status": {
    "input": {"documento_id": "DOC-123"},
    "output": "aprobado"
  },
  "list_pending_reviews": {
    "input": {},
    "output": [
      {
        "documento_id": "DOC-124",
        "status": "auditoria_humana",
        "clasificacion": {"nivel_prioridad": "Urgente"},
        "datos_extraidos": {}
      }
    ]
  }
}
```

`save_review_record` serializa una sola vez con `sort_keys=True` y
`ensure_ascii=False`, calcula el MD5 binario en Base64 y usa los mismos bytes
para ambos objetos. La escritura de `_final.json` usa `if_none_match="*"`.
Después de cada `put_object`, el objeto se relee y se compara byte a byte.
El espejo no se borra si falla su confirmación.

## 2. Excepciones y mapeo HTTP

Las excepciones públicas están en
[`error_handler.py`](/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/core/error_handler.py:32).
[`map_oci_error`](/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/core/error_handler.py:64)
no expone mensajes del SDK:

| Situación | Excepción de aplicación | HTTP recomendado |
|---|---|---:|
| Registro inválido o campos extra | `ReviewValidationError` | 422 |
| `_final.json` ya existe; 412 solo en la escritura condicional | `DuplicateReviewError` | 409 |
| Revisión inexistente; 404 en lectura | `ReviewNotFoundError` | 404 |
| Timeout de requests, urllib3 u OCI | `OCITimeoutError` | 504 |
| Error de credenciales 401 | `OCICredentialsError` | 502 |
| Permisos 403 | `OCIPermissionDeniedError` | 502 |
| Error OCI 502, 503, 5xx o respuesta incompleta | `OCIPersistenceError` u `OCIIncompleteResponseError` | 502 |

Un 412 fuera de la escritura condicional de `_final.json` no se reinterpreta
como duplicado. En particular, los errores del espejo pasan por el mapeo
normal.

## 3. Decisión final y listado de documentos

`GET /api/documents?status=auditoria_humana` seguirá listando los documentos
que están en ese bucket aunque ya tengan una decisión final. El listado de
triaje no cambia su semántica histórica ni elimina documentos decididos.

El panel que necesite únicamente pendientes debe usar
`GET /api/reviews/pending`, que delega en `list_pending_reviews()`.

## 4. Filtro de objetos con `/`

[`listar_resultados_triage`](/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/core/oci_client.py:664)
solo procesa JSON en la raíz:

```python
if "/" not in nombre and nombre.endswith(".json"):
```

Así no lee ni parsea objetos como
`reviews/DOC-123/_final.json` o `reviews/DOC-123/REV-001.json`.
La regresión está cubierta por:

- `test_listar_resultados_triage_preserves_root_json_results`,
  `test_oci_client.py:776`.
- `test_listar_resultados_triage_ignores_review_objects_before_reading`,
  `test_oci_client.py:811`.
- `test_listar_resultados_triage_preserves_pagination`,
  `test_oci_client.py:865`.

La paginación sigue usando `next_start_with` en
[`listar_objetos`](/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/app/core/oci_client.py:565).

## 5. `_final.json` como fuente de verdad

`list_reviews_for_document` lee siempre `_final.json` antes de listar espejos.
Si `_final.json` responde 404, devuelve `[]`. Si existe, valida ese registro
y luego agrega únicamente espejos cuyo `review_id` aún no esté presente.
Esto evita duplicados cuando están presentes el final y su espejo, y permite
recuperar la decisión aunque el espejo falte.

La mitigación de un fallo del espejo es conservar `_final.json`; no se ejecuta
un borrado compensatorio. Los casos están cubiertos por:

- `test_list_reviews_for_document_returns_final_when_only_final_is_listed`,
  `test_oci_client.py:512`.
- `test_list_reviews_for_document_does_not_duplicate_final_and_mirror`,
  `test_oci_client.py:487`.
- `test_list_reviews_for_document_returns_empty_without_final_or_mirrors`,
  `test_oci_client.py:535`.
- `test_save_review_record_keeps_final_when_mirror_fails`,
  `test_oci_client.py:341`.

## 6. Limitaciones conocidas

- `reviewer_id` proviene del cliente; la capa no resuelve por sí sola la
  identidad del usuario autenticado.
- `list_pending_reviews` ejecuta un `head_object` por documento para comprobar
  si existe `_final.json`.
- Las rutas HTTP de revisión deben ser cableadas por la capa API; las
  funciones de persistencia están en `OCIStorageManager`.
- `list_pending_reviews` devuelve el JSON de triaje completo sin modificarlo.
  `nivel_prioridad` está en `clasificacion.nivel_prioridad`.

## 7. Archivos involucrados

Además de los archivos de implementación y documentación originales, se
incorporaron:

- [`tests/test_oci_client.py`](/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/tests/test_oci_client.py).
- [`tests/test_error_handler.py`](/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/tests/test_error_handler.py).

También existe la prueba opt-in de integración en
[`tests/test_oci_transfer_integration.py`](/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/backend/tests/test_oci_transfer_integration.py).

## 8. Línea base y resultados

- Línea base declarada antes de estas etapas: **294 tests**.
- Resultado de la etapa 1: 315 passed, 5 skipped.
- Resultado de la etapa 2: 318 passed, 5 skipped.
- Resultado de la etapa 3: 327 passed, 5 skipped.
- Resultado de la etapa 4: 335 passed, 5 skipped.
- Resultado posterior a la etapa 5 y corrección de fuente de verdad:
  **342 passed, 6 skipped, 8 subtests passed**.

El último resultado se obtuvo sin ejecutar OCI real.

## 9. Evidencia local y evidencia OCI real

### Evidencia local — mocks

Los tests locales usan `MagicMock`/`SimpleNamespace`; no realizan llamadas a
OCI. Cubren escritura, MD5, relectura byte a byte, 412, 401, 403, timeout,
5xx, respuesta incompleta, fallo del espejo, lectura, paginación, estados,
pendientes y preservación del JSON de triaje.

Comando exacto:

```bash
cd mediflow/backend
/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/.venv/bin/python \
  -m pytest -q -p no:cacheprovider
```

Resultado local:

```text
342 passed, 6 skipped, 2 warnings, 8 subtests passed in 1.85s
```

### Evidencia OCI real

Esta sección es evidencia **REAL contra OCI**, separada de la evidencia local
con mocks.

**Fecha UTC:** `2026-10-20T00:53:05Z`

#### Corrida 1 — guardado, lectura y duplicado

```text
RUN_S4_REVIEW_INTEGRATION=1
1 passed
DuplicateReviewError por HTTP 412 real de OCI
```

La corrida guardó y leyó la revisión sintética, y el segundo guardado fue
rechazado por la precondición de `_final.json`.

Claves creadas:

```text
reviews/DOC-S4-TEST-20261020T005305Z/_final.json
reviews/DOC-S4-TEST-20261020T005305Z/REV-cb3559f05588.json
```

Útil para Eliana: evidencia de persistencia y duplicado para su matriz
PASS/FAIL.  
Útil para Drazen: confirma el formato real del registro devuelto por las
funciones de lectura.

#### Corrida 2 — persistencia entre procesos

La corrida 2 se ejecutó en otro proceso y fue de solo lectura:

```text
get_latest_review_status => "aprobado"
list_reviews_for_document => {
  documento_id: DOC-S4-TEST-20261020T005305Z,
  review_id: REV-cb3559f05588,
  review_status: aprobado,
  reviewer_id: s4-integration-test,
  observacion: null,
  reviewed_at: 2026-10-20T00:53:05Z
}
```

Esto demuestra que la decisión persistió entre ejecuciones independientes.

Útil para Eliana: evidencia de persistencia real para su matriz PASS/FAIL.  
Útil para Drazen: confirma el formato real del registro de seis campos que
devuelven las funciones.

Las capturas de pantalla de las corridas 1 y 2 se entregaron al equipo por
canal privado para no publicar datos de la consola de OCI en el historial de
Git.

**Estado de limpieza:** verificada. Las dos claves de prueba fueron borradas
manualmente desde la consola de OCI:

```text
reviews/DOC-S4-TEST-20261020T005305Z/_final.json
reviews/DOC-S4-TEST-20261020T005305Z/REV-cb3559f05588.json
```

La verificación posterior, realizada en otro proceso a las
`2026-10-20T01:23:45Z`, devolvió:

```text
get_latest_review_status => "pendiente"
list_reviews_for_document => []
```

## 10. Permisos y configuración

La identidad usada por la prueba necesita, como mínimo, estos permisos sobre
el bucket `auditoria_humana`:

- `OBJECT_CREATE`
- `OBJECT_READ`
- `OBJECT_INSPECT`
- `OBJECT_DELETE` — usado para la limpieza manual verificada.

Las variables de configuración pueden contener referencias no secretas:

```text
OCI_CONFIG_FILE=/ruta/local/oci/config
OCI_CONFIG_PROFILE=DEFAULT
OCI_NAMESPACE=...
OCI_REGION=...
OCI_BUCKET_AUDITORIA=auditoria_humana
```

No se deben documentar ni imprimir OCIDs, fingerprints, rutas de claves
privadas, tokens ni valores de credenciales. La configuración de OCI debe
permanecer fuera del repositorio.

## 11. Bloqueos y reproducción

### Bloqueo: OCI real no autorizado

La prueba se omite si `RUN_S4_REVIEW_INTEGRATION` no es `1`:

```bash
cd mediflow/backend
/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/.venv/bin/python \
  -m pytest -q -p no:cacheprovider \
  tests/test_oci_transfer_integration.py -k real_review_record
```

No se debe activar hasta contar con credenciales y autorización. Para
permitir la limpieza explícita:

```bash
RUN_S4_REVIEW_INTEGRATION=1 S4_CONFIRM_CLEANUP=1 \
/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/.venv/bin/python \
  -m pytest -q -p no:cacheprovider \
  tests/test_oci_transfer_integration.py -k real_review_record
```

### Bloqueo: dependencia ausente o entorno incorrecto

Usar siempre el intérprete del `.venv` y ejecutar desde `mediflow/backend`.
Los tests con mocks no requieren OCI real ni credenciales externas.

## Guía para Drazen (API HTTP)

Las siguientes filas describen el contrato que debe exponer la capa HTTP.
Las rutas de revisión son la integración pendiente de Drazen; las funciones
internas y sus líneas sí existen en `OCIStorageManager`.

| Endpoint de Drazen | Función mía que debe llamar | Archivo | Símbolo (clase.método) | Líneas | Qué recibe | Qué devuelve | Excepciones y HTTP |
|---|---|---|---|---:|---|---|---|
| `POST /api/documents/{id}/review` | `save_review_record`; opcionalmente `get_latest_review_status` para `expected_review_status` | `app/core/oci_client.py` | `OCIStorageManager.save_review_record`, `OCIStorageManager.get_latest_review_status` | 252, 380 | Los seis campos del registro; el `id` de ruta debe coincidir con `documento_id` | Registro validado; 201 o 200 según contrato API | `ReviewValidationError` 422; `DuplicateReviewError` 409; timeout 504; permisos/OCI 502 |
| `GET /api/documents/{id}/review-history` | `list_reviews_for_document` | `app/core/oci_client.py` | `OCIStorageManager.list_reviews_for_document` | 331 | `documento_id` de ruta | Lista ordenada de objetos `ReviewRecord`; usar `.to_dict()` para serializar a JSON | `ReviewValidationError` 422; inexistencia/fallo de lectura según contrato, 404 o 502; timeout 504 |
| `GET /api/reviews/pending` | `list_pending_reviews` | `app/core/oci_client.py` | `OCIStorageManager.list_pending_reviews` | 406 | Sin cuerpo; filtros HTTP opcionales no cambian el contrato | Lista de JSON de triaje completos | timeout 504; permisos/OCI 502 |

Ejemplo de código para la traducción HTTP:

```python
from fastapi import HTTPException, status

from app.core.error_handler import (
    DuplicateReviewError,
    OCIIncompleteResponseError,
    OCIPermissionDeniedError,
    OCIPersistenceError,
    OCITimeoutError,
    ReviewNotFoundError,
    ReviewValidationError,
)


def review_exception_to_http(error: Exception) -> HTTPException:
    if isinstance(error, ReviewValidationError):
        return HTTPException(status_code=422, detail="La revisión no cumple el contrato.")
    if isinstance(error, DuplicateReviewError):
        return HTTPException(status_code=409, detail="La revisión ya existe.")
    if isinstance(error, ReviewNotFoundError):
        return HTTPException(status_code=404, detail="La revisión no existe.")
    if isinstance(error, OCITimeoutError):
        return HTTPException(status_code=504, detail="OCI agotó el tiempo de espera.")
    if isinstance(
        error,
        (OCIPermissionDeniedError, OCIIncompleteResponseError, OCIPersistenceError),
    ):
        return HTTPException(status_code=502, detail="OCI no pudo completar la operación.")
    return HTTPException(status_code=500, detail="Error interno.")
```

Ejemplo de llamada para cada endpoint:

```python
# POST /api/documents/DOC-123/review
payload = {
    "documento_id": "DOC-123",
    "review_id": "REV-001",
    "review_status": "aprobado",
    "reviewer_id": "auditor-01",
    "observacion": None,
    "reviewed_at": "2026-10-19T18:00:00Z",
}
try:
    record = manager.save_review_record(payload)
except Exception as error:
    raise review_exception_to_http(error)

# GET /api/documents/DOC-123/review-history
try:
    history = manager.list_reviews_for_document("DOC-123")
    history_json = [record.to_dict() for record in history]
except Exception as error:
    raise review_exception_to_http(error)

# GET /api/reviews/pending
try:
    pending = manager.list_pending_reviews()
except Exception as error:
    raise review_exception_to_http(error)
```

### Lo que Drazen debe hacer de su lado

- Traducir `decision` del contrato HTTP a `review_status` (`aprobado` o
  `rechazado`).
- No pasar `decision` ni `expected_review_status` dentro de `record`:
  `ReviewRecord.from_mapping` los rechaza como campos extra.
- Validar que el documento exista y esté en `auditoria_humana` antes de llamar
  a `save_review_record`.
- Generar `review_id`.
- Generar `reviewed_at` en UTC con sufijo `Z`.
- Decidir qué campos expone de `list_pending_reviews`; la función devuelve el
  JSON de triaje completo sin modificar. El nivel de prioridad está en
  `clasificacion.nivel_prioridad`.
- Si implementa `expected_review_status`, comprobarlo con
  `get_latest_review_status` antes de escribir y tratar `pendiente` como el
  estado inicial.

## Guía para Eliana (contrato y pruebas)

Todos los tests con mocks tienen dependencia externa **ninguna**: no llaman a
OCI real. Los grupos pueden ejecutarse con `pytest -k`.

| Escenario de su matriz | Dónde está cubierto en mis tests | Archivo | Nombre del test | Cómo ejecutarlo | Qué comportamiento esperar |
|---|---|---|---|---|---|
| Aprobado | Escritura correcta | `tests/test_oci_client.py` | `test_save_review_record_writes_and_verifies_identical_bytes` (línea 222) | `pytest -k writes_and_verifies_identical_bytes` | Ambos objetos reciben bytes idénticos y MD5 correcto. |
| Rechazado | Validación de registro rechazado | `tests/test_oci_transfer.py` | `test_rejected_review_requires_observation` (línea 80) | `pytest -k rejected_review_requires_observation` | Sin observación, `ReviewValidationError`. |
| Intento duplicado (409) | Precondición 412 del SDK | `tests/test_oci_client.py` | `test_save_review_record_412_does_not_write_mirror` (línea 260) | `pytest -k 412_does_not_write_mirror` | `DuplicateReviewError`; no se escribe espejo. |
| Timeout/403/5xx/respuesta incompleta/MD5 | Mapeo y confirmación | `tests/test_oci_client.py` | `test_save_review_record_maps_sdk_errors`, `test_save_review_record_rejects_incomplete_final_response`, `test_save_review_record_rejects_wrong_md5` (líneas 273, 291, 304) | `pytest -k 'save_review_record_maps or save_review_record_rejects'` | Excepciones públicas sin detalles del SDK. |
| Fallo del espejo | Conservación de fuente | `tests/test_oci_client.py` | `test_save_review_record_keeps_final_when_mirror_fails` (línea 341) | `pytest -k keeps_final_when_mirror_fails` | `_final.json` queda intacto; no se borra. |
| Urgente + revisión | Inmutabilidad del triaje | `tests/test_oci_client.py` | `test_save_review_record_does_not_modify_urgent_triage_object` (línea 381) | `pytest -k does_not_modify_urgent_triage_object` | No se escribe ni borra la clave de triaje. |
| Regresión del listado | Filtro de `/` | `tests/test_oci_client.py` | `test_listar_resultados_triage_ignores_review_objects_before_reading` (línea 811) | `pytest -k ignores_review_objects_before_reading` | No se leen objetos bajo `reviews/`. Código: `oci_client.py:693`. |
| Paginación | Varias páginas de revisiones | `tests/test_oci_client.py` | `test_list_reviews_for_document_reads_multiple_pages` (línea 703) | `pytest -k reads_multiple_pages` | Se usa `next_start_with`; se combinan y ordenan registros. |
| Estados pendiente/aprobado/rechazado | Estado final | `tests/test_oci_client.py` | `test_get_latest_review_status_returns_three_states` (línea 605) | `pytest -k returns_three_states` | 404 devuelve `pendiente`; final válido devuelve su estado. |

Comandos completos de grupos:

```bash
cd mediflow/backend
PYTHON=/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/.venv/bin/python

$PYTHON -m pytest -q -p no:cacheprovider tests/test_oci_client.py -k 'review'
$PYTHON -m pytest -q -p no:cacheprovider tests/test_error_handler.py -k 'map_oci_error'
$PYTHON -m pytest -q -p no:cacheprovider tests/test_oci_transfer.py -k 'review'
```

Prueba OCI real, aún no ejecutada:

```bash
cd mediflow/backend
RUN_S4_REVIEW_INTEGRATION=1 S4_CONFIRM_CLEANUP=1 \
/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/.venv/bin/python \
-m pytest -q -p no:cacheprovider \
tests/test_oci_transfer_integration.py -k real_review_record
```

Sin `S4_CONFIRM_CLEANUP=1`, la prueba reporta las claves exactas pero no las
borra. No se imprime namespace, OCIDs ni valores de configuración.

### Regeneración de líneas

Comando utilizado para obtener las líneas del estado documentado:

```bash
grep -nE 'class OCIStorageManager|def (save_review_record|get_review_record|list_reviews_for_document|get_latest_review_status|list_pending_reviews|listar_resultados_triage)|def map_oci_error|class (ReviewRecord|ReviewValidationError|DuplicateReviewError|ReviewNotFoundError|OCICredentialsError|OCIPermissionDeniedError|OCITimeoutError|OCIIncompleteResponseError|OCIPersistenceError)' \
  mediflow/backend/app/core/oci_client.py \
  mediflow/backend/app/core/error_handler.py

grep -nE '^def test_|^    def test_|^def _cleanup_s4|^class OCIStorageManagerTest' \
  mediflow/backend/tests/test_oci_client.py \
  mediflow/backend/tests/test_error_handler.py \
  mediflow/backend/tests/test_oci_transfer_integration.py
```

Fecha de generación: **2026-10-19**.
