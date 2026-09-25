# Manejo de errores OCI - Brando

Este módulo es una capa de manejo de errores sobre el cliente OCI creado por
Eliana durante el Sprint 1. No modifica ese cliente: lo importa y delega en su
método `OCIStorageManager.subir_archivo(...)`.

## Archivos

- `oci_error_handler.py`: wrapper que valida entradas, llama al cliente de
  Eliana y traduce errores a excepciones propias.
- `test_oci.py`: prueba independiente con `unittest.mock`; no requiere
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
source venv/bin/activate
python mediflow/backend/brando/test_oci.py
```

También se puede ejecutar con `./venv/bin/python` si el entorno virtual ya
existe. El script imprime cada escenario y termina con `RESULTADO GENERAL: OK`
cuando todas las pruebas pasan.

Las pruebas simulan las excepciones del cliente de Eliana mediante
`unittest.mock`, por lo que no realizan una subida real a OCI.