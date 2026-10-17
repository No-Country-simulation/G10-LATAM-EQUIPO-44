> Agregado por Edil: integración del 16 de octubre. Se conserva la entrega original como referencia. El flujo activo usa Gemini con consentimiento, GET y JSON de recepción; verifica la copia y conserva el original. Cohere, la configuración paralela y las rutas manuales de movimiento describen la propuesta de la rama, no el API actual. Ver docs/sprint-3/integracion-ramas-16-octubre.md.

# S3-06 — Copia de documentos procesados a OCI

## Responsable

Brando Josué.

## Alcance de esta entrega

Esta entrega implementa el comportamiento solicitado para conservar el documento
original en `recibidos` y generar una segunda copia en el bucket determinado por
el pipeline:

```text
subida → recibidos
          ├── copia conservada en recibidos
          └── copia verificada en procesados o auditoria_humana
```

El endpoint manual `/api/oci/move` conserva su semántica anterior: copia,
verifica y elimina el origen. La conservación del origen aplica al flujo
automático de `/api/triage`.

## Cambios realizados y ubicación

### 1. Integración del flujo automático

Archivo: [`mediflow/backend/app/api/routes.py`](../../mediflow/backend/app/api/routes.py)

- En `post_triage`, después de obtener la decisión del orquestador, se
  selecciona el destino:
  - `procesado` → `OCI_BUCKET_PROCESADOS`.
  - `auditoria_humana` → `OCI_BUCKET_AUDITORIA`.
- La llamada automática usa `manager.copiar_archivo(...)` en lugar de
  `manager.mover_archivo(...)`.
- El resultado de la copia actualiza `almacenamiento_oci` con bucket, estado,
  SHA-256 y tamaño.
- Si OCI falla, se registra el error y la API responde `502`; el origen no se
  elimina.

Sección específica: función `post_triage`, bloque de transferencia posterior a
`procesar_con_orquestador`.

### 2. API de copia no destructiva

Archivo: [`mediflow/backend/app/core/oci_client.py`](../../mediflow/backend/app/core/oci_client.py)

- Se agregó `OCIStorageManager.copiar_archivo(nombre_archivo,
  bucket_origen, bucket_destino)`.
- Este método delega en la operación de copia verificada y conserva el objeto
  en el bucket de origen.
- `mover_archivo(...)` no fue eliminado ni cambió su contrato; continúa
  disponible para operaciones explícitas que sí deben retirar el origen.

Sección específica: métodos `mover_archivo` y `copiar_archivo` de
`OCIStorageManager`.

### 3. Copia y verificación de integridad

Archivo: [`mediflow/backend/app/core/oci_transfer.py`](../../mediflow/backend/app/core/oci_transfer.py)

- `OCIObjectMover.copy(...)` realiza la copia sin borrar el origen.
- Antes de copiar verifica que exista el objeto fuente y que el destino no
  contenga ya el mismo objeto.
- La copia espera a estar visible en OCI.
- Luego compara:
  - SHA-256 del origen y del destino.
  - Tamaño (`content-length`) del origen y del destino.
- Si la copia o la verificación falla, se lanza un error y el objeto de
  `recibidos` permanece intacto.
- `OCIObjectMover.move(...)` reutiliza `copy(...)` y solo después de verificar
  ejecuta `delete_object` para conservar el comportamiento de movimiento
  explícito.

Secciones específicas:

- `OCIObjectMover.move(...)`.
- `OCIObjectMover.copy(...)`.
- Métodos privados de lectura, espera y verificación del mismo archivo.

### 4. Prueba automatizada

Archivo: [`mediflow/backend/tests/test_oci_transfer.py`](../../mediflow/backend/tests/test_oci_transfer.py)

Se agregó `test_copy_verifies_content_and_retains_source`, que comprueba que:

- la copia se solicita una vez;
- el tamaño del origen y destino coincide;
- `delete_object` nunca se llama durante la copia no destructiva.

Las pruebas de transferencia ejecutadas quedaron en:

```text
10 passed
```

## Cómo ejecutar el backend

Desde la raíz del repositorio:

```bash
cd mediflow/backend
/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/.venv/bin/python \
  -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

La documentación interactiva queda disponible en:

```text
http://127.0.0.1:8000/docs
```

Las credenciales de OCI deben existir previamente en el entorno local. No se
deben subir `.env`, `~/.oci/config` ni llaves privadas al repositorio.

## Cómo ejecutar la prueba automatizada

Desde la raíz del repositorio:

```bash
cd mediflow/backend
PYTHONPATH=.:.. \
/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/mediflow/.venv/bin/python \
  -m pytest -q tests/test_oci_transfer.py
```

## Cómo ejecutar la prueba manual con FastAPI

Con el backend activo, subir un archivo no sensible:

```bash
curl -X POST \
  http://127.0.0.1:8000/api/triage \
  -H 'accept: application/json' \
  -F 'file=@archivo.pdf;type=application/pdf'
```

La respuesta debe indicar el bucket final en `almacenamiento_oci.bucket`:

- `procesados` para un documento procesado automáticamente.
- `auditoria_humana` para un documento ambiguo o que requiera revisión.

## Verificación esperada en OCI

Usando la consola de OCI o las herramientas locales autorizadas, comprobar
que el mismo valor de `almacenamiento_oci.ruta_objeto` exista en ambos buckets:

```text
recibidos/<ruta_objeto>
procesados/<ruta_objeto>
```

o:

```text
recibidos/<ruta_objeto>
auditoria_humana/<ruta_objeto>
```

El tamaño y el SHA-256 de ambas copias deben coincidir. Si la copia falla, el
archivo debe permanecer únicamente en `recibidos` y la API debe responder con
error `502`.

## Punto de control

- Rama: `feature/s3-06-integracion`.
- Commit de esta parte: `3fdcb4e` — `feat: conservar copia de recibidos en triage`.
