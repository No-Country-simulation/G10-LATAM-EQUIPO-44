# Cierre técnico Sprint 3 — Drazen y Brando

17 de octubre de 2026. Alcance: S3-03, S3-04A y S3-06; API, persistencia y OCI.

## Estado de las subtareas

| Responsable / tarea | Verificación | Estado |
| --- | --- | --- |
| Drazen S3-03.1: GET listado | HTTP 200 real y presencia única del resultado actual de ambas muestras | Aprobado |
| Drazen S3-03.2: GET individual | HTTP 200, JSON completo igual al final persistido e ID coincidente | Aprobado |
| Drazen S3-03.3: filtros | Estado y prioridad reales; no reaparece la recepción anterior al filtrar recibido | Aprobado |
| Drazen S3-03.4: validación y errores GET | ID inexistente 404 e inválido 400 reales; corrupción y errores de almacenamiento en pruebas locales | Aprobado en el alcance probado |
| Drazen S3-04A: JSON de recepción | POST real sin IA, HTTP 201, original y JSON recibido comprobados en recibidos | Aprobado |
| Drazen S3-04A: JSON final | Escritura y lectura directa en procesados y auditoria_humana; igualdad con modelo y GET | Aprobado |
| Drazen S3-04A: fallos de escritura/lectura | Pruebas locales con dobles, sin ocultar éxito parcial ni simular fallos en la cuenta real | Aprobado localmente |
| Brando S3-06: copia entre buckets | CopyObject nativo real, HTTP 202 y work request COMPLETED en ambos destinos | Aprobado |
| Brando S3-06: integridad y conservación | 76 bytes, SHA-256 iguales, ETag del origen sin cambios; original retenido | Aprobado |
| Brando S3-06: error de permisos | No se reprodujo InsufficientServicePermissions; registro seguro de fallo síncrono/asíncrono probado localmente | Sin bloqueo observado |

No se atribuye participación presencial a los responsables. No se modifica el
estado de un tablero externo ni se hacen commits, push o merge.

## Mecanismo activo y garantías

`POST /api/triage` guarda el original y JSON inicial en recibidos. Con análisis
solicitado, el resultado validado pasa por `_copy_original_to_result_bucket`
y luego `_persist_triage_result`. La copia reutiliza
`OCIStorageManager.copiar_archivo` → `OCIObjectMover.copy` → SDK `copy_object`.
No es un GET seguido de PUT del lado de la aplicación, ni una réplica automática.
Los GET leen JSON persistidos, no ejecutan IA ni vuelven a evaluar reglas.

La copia fija el ETag del origen, prohíbe sobrescribir un destino existente,
espera la operación asíncrona, compara tamaños y SHA-256 mediante GET condicionados
a las versiones observadas. El destino es otro objeto: **no se exige igualdad
de ETag entre origen y destino**. Esa semántica está documentada por
[Oracle CopyObject](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/copyingobjects.htm).
El hash compara bytes descargados, no interpreta el ETag como checksum.
La prueba conservó el ETag del origen antes y después y obtuvo ETags diferentes
en cada copia. No se ejecutaron `move`, `mover_archivo` ni `delete_object`.

El contrato conserva únicamente bucket/ruta/status de backup; los hashes,
tamaños y ETags pertenecen a evidencia técnica interna, no a campos API nuevos.
Ante fallo de copia o persistencia, el endpoint devuelve 503 y X-Document-ID;
no confirma procesamiento final exitoso. Puede haber copia ya creada si falla
una etapa posterior: no es una transacción atómica entre buckets y JSON.

## Dos verificaciones reales y datos retenidos

| Propiedad | Procesado | Revisión humana |
| --- | --- | --- |
| ID | DOC-CLIN-37B1501AC59C40A48C45C1956BB41A56 | DOC-CLIN-1A73E28DC0264C6F9FDC94B3EF171129 |
| Recepción HTTP | 201 | 201 |
| Bucket final | procesados | auditoria_humana |
| Estado | procesado | auditoria_humana |
| Prioridad | Rutina | Rutina |
| Destino | Cola_Farmacia | Cola_Revision_Humana |
| Original y copia | 76 bytes, iguales | 76 bytes, iguales |
| Work request | COMPLETED | COMPLETED |
| GET por ID / listado | 200 / 200 | 200 / 200 |
| ID inexistente | 404 | 404 |

SHA-256 común de los archivos de prueba:
`2a95e50f4720626d45d69c8b1844c0f8f4e8568207d28ae2bd2a44d53cedbc68`.
Los JSON finales tienen sus propios tamaños, ETags y hashes, registrados en
las evidencias. Se verificaron por lectura directa y GET, incluyendo igualdad
completa con el modelo guardado. El listado entrega cada ID una sola vez;
el JSON recibido sigue conservado pero no suplanta al final.

Se conservaron **ocho objetos sintéticos propios**: original TXT y JSON inicial
en recibidos, copia TXT y JSON final en cada destino, cuatro por caso.
No se limpiaron objetos del equipo ni se sobrescribieron evidencias previas.
El verificador no tiene operación de borrado.

### Qué fue real y qué fue controlado

- Reales: HTTP local contra uvicorn, POST de recepción, SDK OCI, CopyObject,
  work requests, HEAD y GET condicionados, persistencia JSON, GET individuales,
  listado, filtros, 404 y 400. Sin mocks de OCI ni fallback de copia.
- Controlado: la entrada estructurada que representa el análisis es una fixture
  local de software, identificada expresamente como tal. Se pasa al orquestador
  existente y a las etapas reales de copia/persistencia. La segunda fixture
  solicita revisión previa; no se cambian reglas ni se inventan criterios clínicos.
- No ejecutado en esta intervención: Gemini, nueva extracción clínica ni un
  POST analyze=true completo. Las pruebas previas de IA no se presentan como
  ejecuciones nuevas. Esta verificación cierra almacenamiento/API, no evalúa IA.

## Configuración y permisos OCI

Región probada: `sa-santiago-1`. Buckets independientes:
`OCI_BUCKET_RECIBIDOS=recibidos`, `OCI_BUCKET_PROCESADOS=procesados`,
`OCI_BUCKET_AUDITORIA=auditoria_humana`. No son carpetas de un bucket único.
El backend carga `mediflow/.env`; las variables exportadas prevalecen.
No se cambiaron `.env`, perfiles, claves ni IAM.

Hay dos niveles de autorización: el principal que invoca el SDK y el servicio
regional `objectstorage-<región>` que ejecuta la copia. El primero necesita
lectura/inspección y los permisos de creación/sobrescritura exigidos por
CopyObject; además lectura de work requests. El servicio requiere autorización
regional sobre los recursos involucrados. Un administrador debe revisar el
alcance de compartimentos y buckets en la
[guía oficial de copia](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/copyingobjects.htm) y la
[matriz IAM](https://docs.oracle.com/en-us/iaas/Content/Identity/policyreference/objectstoragepolicyreference.htm), sin ampliar permisos a toda la tenancy por defecto.
Estas son necesidades de las operaciones, no un listado de políticas efectivas
obtenido de la cuenta.

**No hay permisos externos faltantes observados en estas dos pruebas.** No se
consultaron ni modificaron políticas IAM. El fallo histórico
`InsufficientServicePermissions` no se repitió; no se elimina su evidencia ni se
afirma qué sentencia concreta cambió para resolverlo. No se puede certificar
por este ensayo autorización para otras regiones, claves de cifrado o buckets.

Si vuelve a fallar, registrar operación `copy_object`, HTTP/código del SDK y
work request, consultar sus errores si termina FAILED y revisar la autorización
del servicio regional y del invocador. HTTP 202 por sí solo no significa copia
exitosa. El nuevo verificador propaga el fallo y sale con código 1; no cambia a
otra técnica de copia ni guarda el mensaje crudo que pudiera contener datos.

## Reproducción

En `D:\Nocountru\mediflow\backend`, iniciar una instancia local:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8144 --no-access-log
```

En otra terminal, con autorización para crear muestras en OCI:

```powershell
$dbReport = Join-Path $env:TEMP ('MediFlow-oci-' + [guid]::NewGuid().ToString('N') + '.json')
& .\.venv\Scripts\python.exe scripts/verify_sprint3_oci.py --allow-oci-writes --confirm-synthetic --base-url http://127.0.0.1:8144 --report $dbReport
```

Para otra muestra de auditoría añadir `--review` y usar **otro** informe.
Cada ejecución crea un ID nuevo y conserva sus objetos. Ambos indicadores
de autorización son obligatorios. El verificador rechaza URLs no locales,
credenciales embebidas y sobrescritura de informes. El puerto es de prueba;
no se añade ni modifica una ruta pública. Detener la instancia temporal al acabar.

### Perfil de demostración de IA

Para demostrar el dataset ya validado, configurar explícitamente la instancia
que sí vaya a analizar documentos:

```powershell
$env:TRIAGE_RULES_PROFILE = 'synthetic_demo_v1'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8143 --no-access-log
```

El perfil se configura en el servidor, no mediante nombres de archivo ni
parámetros públicos de los GET. El runner de la demo debe declarar el mismo
perfil. El POST de demostración con IA necesita `analyze=true` y sus servicios
autorizados. Esto es distinto del verificador de almacenamiento, que no llama
Gemini y usa la política general existente para sus fixtures.
No activar la excepción sintética para documentos reales. Volver al perfil
habitual deteniendo la instancia y retirando esa variable en la terminal de demo.

## Pruebas locales

Desde backend:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_oci_client.py tests/test_oci_transfer.py tests/test_oci_error_handler.py tests/test_documents_api.py tests/test_triage_api.py tests/test_s3_integration_regressions.py tests/test_s3_complete_pipeline.py tests/test_sprint3_oci_verifier.py -q -p no:cacheprovider
```

**90 aprobadas**, dos avisos de deprecación de dependencias, cero fallos.
Son 80 pruebas existentes y 10 nuevas del verificador; los dobles de OCI/Gemini
se usan solo en esa suite local. Cubren errores de API/persistencia, integridad,
ETags, no borrado, validación, conservación de recepción y registro seguro del
código de permisos tanto síncrono como asíncrono. Los casos de fallo no se
provocaron alterando IAM en la cuenta real.

## Evidencias y archivos

- [Copia procesados y recuperación reales](evidencias/drazen-brando-s3-oci-real.json).
- [Copia auditoría y recuperación reales](evidencias/drazen-brando-s3-auditoria-real.json).
- [GET y filtros reales adicionales](evidencias/drazen-brando-s3-api-real.json).

Archivos nuevos: `mediflow/backend/scripts/verify_sprint3_oci.py`,
`mediflow/backend/tests/test_sprint3_oci_verifier.py`, este informe y las tres
evidencias anteriores. Guías actualizadas: `mediflow/backend/conexion-oci.md`,
`docs/sprint-3/api_documentos_flor.md`,
`docs/sprint-3/guia-verificacion-json-oci.md` y
`docs/sprint-3/S3-06-brando-josue-traslado-oci.md`.

No se modificaron endpoints, transferencia funcional, contrato, reglas de
Nicolás/Laura, Flutter ni frontend web. Se conservaron cambios locales anteriores.
El ensayo prueba los objetos/configuración ejercitados; no demuestra una
transacción atómica, reintentos idempotentes del pipeline, recuperación automática
de fallos parciales, carga, versionado concurrente en producción ni IAM de otras
configuraciones. Esas garantías requieren verificación específica si se solicitan.
