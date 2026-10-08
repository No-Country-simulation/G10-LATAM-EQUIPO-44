# Manejo de errores OCI - Brando

Este módulo es una capa de manejo de errores sobre el cliente OCI creado por
Eliana durante el Sprint 1. No modifica ese cliente: lo importa y delega en su
método `OCIStorageManager.subir_archivo(...)`.

## Archivos

- `oci_error_handler.py`: wrapper que valida entradas, llama al cliente de
  Eliana y traduce errores a excepciones propias.
- `tests/test_oci_error_handler.py`: prueba con `unittest.mock`; no requiere
  credenciales, bucket ni conexión real a OCI.

## Escenarios cubiertos

- Subida exitosa mediante `OCIStorageManager.subir_archivo`.
- Problemas de red o conectividad: `ConnectionError`, `TimeoutError` y errores
  de comunicación del SDK se convierten en `OCIConnectionError`.
- Configuración o credenciales inválidas: permisos, configuración ausente o
  inválida se convierten en `OCIConfigurationError`.
- Archivos corruptos, rutas inexistentes o entradas inválidas: errores de
  archivo, rutas, tipos y valores se convierten en `OCIInputError`.

## Ejecución paso a paso

Desde la raíz del repositorio:

```bash
cd mediflow/backend
python -m pytest tests/test_oci_error_handler.py tests/test_oci_client.py -v
```

Ejecuta los comandos con el Python del entorno que tenga las dependencias.
Pytest muestra `passed` cuando todas las pruebas pasan y devuelve código 0.

Las pruebas simulan las excepciones del cliente de Eliana mediante
`unittest.mock`, por lo que no realizan una subida real a OCI.

## Cliente oficial y configuración actual

El cliente oficial es `app/core/oci_client.py`. El manejador y las pruebas
importan desde `app.core`; no requieren carpetas individuales antiguas.
Se utiliza un bucket `mediflow-documents` con prefijos `recibidos/`,
`procesados/` y `auditoria_humana/`, no tres buckets distintos.

El SDK resuelve `~/.oci/config` y el perfil `DEFAULT`. Se pueden exportar
`OCI_CONFIG_PROFILE`, `OCI_CONFIG_FILE`, `OCI_BUCKET_NAME` y `OCI_PREFIX_*`.
No se carga `.env` automáticamente: exporta las variables en tu terminal.
No copies los marcadores de credenciales de `.env.example` como valores reales.
La región de autenticación proviene del perfil local.

## Prueba de integración real (PowerShell)

Requiere SDK OCI, pytest y credenciales locales ya configuradas. Desde
`mediflow/backend`, instala dependencias si hacen falta:

```powershell
python -m pip install -r ../requirements.txt
```

La ejecución normal es segura: la prueba real se omite sin autorización.

```powershell
python -m pytest tests -v
```

Para ejecutar expresamente la prueba contra tu OCI:

```powershell
$env:OCI_CONFIG_PROFILE = 'DEFAULT'
$env:OCI_BUCKET_NAME = 'mediflow-documents'
$env:OCI_PREFIX_RECIBIDOS = 'recibidos/'
$env:RUN_OCI_INTEGRATION = '1'
try {
    python -m pytest tests/test_oci_integration.py -v -s
} finally {
    Remove-Item Env:RUN_OCI_INTEGRATION -ErrorAction SilentlyContinue
}
```

Se crea `recibidos/sprint1-integration-<uuid>.txt`, se descarga el mismo
objeto a una ruta temporal y se compara su contenido byte por byte.
El resultado esperado es `1 passed` y mensajes `OK upload/download` y
`OK: objeto de prueba eliminado`. Fallos de subida, descarga, comparación
o limpieza hacen fallar pytest. Solo se elimina el objeto único de esta prueba.
Se requieren permisos de crear, leer y eliminar objetos en el bucket.
