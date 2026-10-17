# S3-06 - Traslado seguro de objetos OCI

## Implementación independiente

El módulo [`oci_transfer.py`](../../mediflow/backend/app/core/oci_transfer.py)
no depende del pipeline de orquestación. `OCIObjectMover.move(...)` recibe:

- `object_name`: clave completa del objeto, incluidos prefijos.
- `source_bucket`: bucket de origen, normalmente `settings.OCI_BUCKET_RECIBIDOS`.
- `destination_bucket`: bucket de destino, normalmente `settings.OCI_BUCKET_PROCESADOS`.

Devuelve un `TransferResult` con los buckets, la clave, tamaños y el SHA-256
calculado leyendo ambos objetos. El método:

1. Consulta el origen con `head_object`.
2. Rechaza un destino existente.
3. Ejecuta `copy_object` y espera el work request cuando OCI lo devuelve.
4. Espera a que el destino sea visible.
5. Lee ambos objetos y compara SHA-256 y tamaño. No usa ETag como MD5.
6. Elimina el origen solo después de la verificación.

Si falla cualquier paso previo a la eliminación, el origen se conserva.
`SourceObjectNotFoundError`, `DestinationObjectExistsError`,
`TransferVerificationError` y `ObjectTransferError` permiten distinguir los
casos relevantes. Un error durante la eliminación significa que la copia fue
verificada, pero el origen puede permanecer y debe revisarse.

Para integrarlo posteriormente, el pipeline solo necesita construir un
`oci.object_storage.ObjectStorageClient`, resolver `namespace` y `region`, y
llamar:

```python
mover = OCIObjectMover(client, namespace, region)
result = mover.move(object_name, bucket_recibidos, bucket_procesados)
```

No se implementan aquí clasificación, urgencia ni orquestación.

## Diagnóstico de solo lectura

El script [`oci_diagnose.py`](../../mediflow/backend/scripts/oci_diagnose.py)
consulta configuración, namespace, los objetos de `recibidos` y
`procesados`, y opcionalmente metadatos de una clave. No sube, copia, modifica
ni elimina objetos.

Desde `mediflow/backend`:

```bash
PYTHONPATH=. ../..//venv/bin/python scripts/oci_diagnose.py
PYTHONPATH=. ../..//venv/bin/python scripts/oci_diagnose.py \
  --bucket recibidos --object pruebas/archivo-oci.txt
```

La ruta habitual del entorno del repositorio es
`/home/matthew/Escritorio/G10-LATAM-EQUIPO-44/venv/bin/python`; también puede
usarse `./venv/bin/python` desde la raíz.

La autenticación usa primero las variables definidas por `app.core.config`
(`OCI_USER_OCID`, `OCI_FINGERPRINT`, `OCI_KEY_FILE`, `OCI_TENANCY_OCID` y
`OCI_REGION`) y, si no están completas, el perfil `DEFAULT` de
`~/.oci/config`. Nunca imprime valores de credenciales.

## Pruebas

Pruebas unitarias aisladas, sin cuenta OCI:

```bash
cd mediflow/backend
PYTHONPATH=. /home/matthew/Escritorio/G10-LATAM-EQUIPO-44/venv/bin/pytest -q tests/test_oci_transfer.py
```

La prueba real es opcional y no se ejecuta por defecto:

```bash
cd mediflow/backend
export OCI_RUN_INTEGRATION=1
export OCI_TEST_OBJECT_NAME=pruebas/s3-06-oci-transfer.txt
PYTHONPATH=. /home/matthew/Escritorio/G10-LATAM-EQUIPO-44/venv/bin/pytest -q tests/test_oci_transfer_integration.py
```

Antes de habilitarla, cargar manualmente en `recibidos` un archivo pequeño,
no sensible y claramente identificado, por ejemplo
`pruebas/s3-06-oci-transfer.txt`. Confirmar primero su existencia con el
diagnóstico. La prueba no crea archivos, no selecciona claves por listado y
solo mueve la clave indicada explícitamente. No usar documentos de pacientes
ni nombres de objetos preexistentes.

Para registrar el experimento:

1. Crear un archivo de texto con un identificador de prueba y calcular su
   SHA-256 local.
2. Subirlo manualmente a `recibidos/pruebas/...`.
3. Confirmar nombre y tamaño con `oci_diagnose.py`.
4. Ejecutar la prueba de integración.
5. Consultar ambos buckets y descargar el destino para recalcular el hash.
6. Confirmar que el origen ya no existe y conservar la salida del comando.

## Estado verificado y limitaciones

En este entorno se verificaron los 9 escenarios unitarios con mocks (`9
passed`) y la compilación de los nuevos módulos. No se ejecutó una operación
contra OCI real porque no se habilitaron credenciales ni un objeto de prueba.
La prueba de integración permanece pendiente de ese experimento controlado.

### Experimento real ejecutado

El 13 de octubre de 2026 se ejecutó el backend local con el perfil OCI
configurado en el entorno, usando un archivo de texto no sensible de 46 bytes.
El flujo real fue:

```text
POST /api/triage
  -> recibidos/pruebas/DOC-CLIN-2A7B3F28F8394857A1F6BEA17463D203.txt
POST /api/oci/move?object_name=...
  -> procesados/pruebas/DOC-CLIN-2A7B3F28F8394857A1F6BEA17463D203.txt
```

Resultado observado:

- Respuesta de subida: `status=recibido`, `bucket=recibidos`.
- Respuesta de traslado: `status=procesado`, `tamano=46`.
- SHA-256 local y remoto: `88bd490786150292603f2dbf2607bf88fc0329e7ad8b4679ee44fde3f6df7170`.
- El objeto apareció en `procesados` y no apareció en `recibidos`.
- Los metadatos remotos mostraron `content-length=46`.

Durante dos intentos iniciales, la subida a OCI terminó correctamente pero el
endpoint respondió 500 al construir la respuesta. Esos intentos dejaron dos
objetos de prueba en `recibidos`:
`pruebas/DOC-CLIN-6B956C3B4AF54AFEAB8A69036DF03589.txt` y
`pruebas/DOC-CLIN-CB53511EE5114B15B94CDDD6BDF5A039.txt`. No se eliminaron
automáticamente para evitar borrar objetos sin confirmación explícita.

La suite histórica contiene pruebas con imports antiguos (`conexion_oci`) y
una prueba OCI que no está aislada; no se marcaron como exitosas ni se
reutilizaron como evidencia de acceso real.

## Registro de progreso

- 2026-10-16: Estado inicial revisado; `oci_transfer.py` ya implementa copia, verificación SHA-256/tamaño y borrado seguro.
- 2026-10-16: Rama de Eliana identificada como `origin/feature/orquestador`; contiene `core/orquestador.py` y `app/services/servicio_orquestador.py`, pero ese servicio requiere módulos ausentes en la rama actual.
- 2026-10-16: Rama `feature/s3-06-traslado-oci` creada y estado previo guardado en `28cacbc`; se trajeron los dos módulos y se adaptaron al JSON existente.
- 2026-10-16: Cambio en `routes.py` aplicado: `procesado` va a `OCI_BUCKET_PROCESADOS` y `auditoria_humana` a `OCI_BUCKET_AUDITORIA`; ambos llaman a `mover_archivo()` con copia, verificación y borrado seguro.
- 2026-10-16: Pruebas unitarias OCI: `9 passed`; contrato de orquestación normal y de auditoría verificado; prueba real OCI de esta integración pendiente para no mover un objeto sin confirmación explícita.
- 2026-10-16: Diagnóstico de ramas completado en `feature/s3-06-integracion`; no existe `PLAN_S3-06.md`, se usó este documento como contexto. `origin/main` (8ef6e09) es el consolidado más reciente, pero elimina `oci_transfer.py` y cambia el extractor; no se integrará completo.
- 2026-10-16: Pendiente de confirmación: combinar solo funciones compatibles de Eliana/Laura/Nicolás con el extractor Cohere y `mover_archivo()` local; preservar OCI y evitar checkout completo de ramas.
- 2026-10-16: Se integró `origin/feature/orquestador` con sus módulos de pipeline, reglas y APIs OCI; se conservaron Cohere y `oci_transfer.py`, y `mover_archivo()` fue conectado al verificador SHA-256/tamaño.
- 2026-10-16: Se añadió `score_confianza.py` de la corrección MVP de Laura y se corrigió el catálogo de urgencia. Matriz simulada: normal→procesados, urgente→procesados, ambiguo→auditoria_humana; falla de permiso→HTTP 502 y original conservado.
