# Manejo de errores OCI - Brando

Implementación propia y autocontenida para simular una subida a Oracle Cloud
Infrastructure (OCI). No usa el código de otro integrante, no necesita acceso
a OCI y no requiere credenciales reales.

## Archivos

- `oci_simulator.py`: adaptador `OCIUploadAdapter`, excepciones específicas y
	`StubOCIClient`.
- `test_oci.py`: script de prueba de integración con `unittest`.

## Escenarios cubiertos

- Subida exitosa y registro del objeto subido por el stub.
- `OCIConnectionError` para desconexiones y timeouts.
- `OCIConfigurationError` para cliente, namespace, credenciales o permisos
	inválidos.
- `OCIInputError` para archivos inexistentes, rutas ilegibles, bucket vacío o
	nombre de objeto vacío.

El adaptador concentra los bloques `try/except` y expone excepciones propias,
para que una API pueda decidir cómo responder sin depender de excepciones del
SDK. El patrón queda listo para integrar el cliente OCI real desde Sprint 2:
se reemplaza `StubOCIClient` por un cliente con el método `put_object` y se
mantiene `OCIUploadAdapter`.

## Ejecución paso a paso

1. Abrir una terminal en la raíz del repositorio.
2. Activar el entorno virtual, si existe:

	 ```bash
	 source venv/bin/activate
	 ```

3. Ejecutar el script:

	 ```bash
	 python mediflow/backend/brando/test_oci.py
	 ```

	 En este entorno también puede usarse `./venv/bin/python` si `python` no
	 está disponible en el `PATH`.

4. Confirmar cinco líneas `ok`, el resumen `Ran 5 tests` y
	 `Resultado general: OK`.
