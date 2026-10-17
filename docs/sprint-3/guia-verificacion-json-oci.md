# Verificación JSON en OCI — Edil y Drazen

> Actualización del 14 de octubre: la entrega S3-04A de Drazen está incorporada localmente con correcciones y pruebas. La ejecución real y evidencia OCI siguen pendientes. Ver integracion-ramas-14-octubre.md; las notas de ausencia de implementación de abajo describen el estado anterior.

Agregado por Edil: guía de S3-04.6. No es evidencia de una prueba ejecutada.

## Preparación local

Desde PowerShell:

```powershell
cd D:\Nocountru\mediflow
# Crear .env solo si no existe; nunca sobrescribir una configuración local.
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
```

Completar localmente, sin publicar secretos:

```dotenv
OCI_CONFIG_PROFILE=DEFAULT
OCI_BUCKET_RECIBIDOS=recibidos
OCI_BUCKET_PROCESADOS=procesados
OCI_BUCKET_AUDITORIA=auditoria_humana
GEMINI_API_KEY=
GEMINI_MODEL=
```

La clave OCI debe quedar fuera de Git; el perfil local debe tener permiso de escritura y lectura en el bucket acordado. El backend carga mediflow/.env. Flutter usa su URL de API, nunca credenciales OCI.

```powershell
cd D:\Nocountru\mediflow\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

En otra terminal, para Windows:

```powershell
cd D:\Nocountru\mediflow\frontend_mobile\mediflow_app
flutter run -d windows --dart-define=API_BASE_URL=http://localhost:8000
```

## Prueba coordinada cuando Drazen entregue S3-04A

1. Identificar el commit exacto y los comandos/endpoint reales de persistencia. Hoy no hay ese endpoint: no inventar su URL ni usar test_oci.py como prueba equivalente.
2. Elegir con Drazen el bucket y nombre de objeto único de prueba; usar exclusivamente JSON sintético sin pacientes reales.
3. Validar el JSON contra TriageResponse y anotar documento_id antes de escribir.
4. Ejecutar la ruta de escritura de S3-04A y registrar HTTP/código de salida, bucket, objeto, fecha UTC y commit. No registrar claves, perfiles completos ni documentos reales.
5. Recuperar el objeto mediante la ruta real de lectura de S3-04A; comparar el JSON deserializado con el original. Una subida sin lectura posterior no basta.
6. Comprobar estado, documento_id, clasificación, medicamentos_recetados, decisión y almacenamiento. Si el backend devuelve metadatos añadidos, comparar con el contrato documentado y no solo cadenas de texto.
7. Verificar un error controlado de lectura de nombre inexistente y la política de fallo parcial sin borrar objetos del equipo. Coordinar con Drazen el caso de fallo de escritura; no retirar permisos de producción para simularlo.
8. Guardar evidencia anonimizada en docs/sprint-3/evidencias con nombre, commit, resultado y huellas SHA-256 cuando proceda. No guardar secretos ni respuestas con información clínica real.
9. Si se limpia la prueba, borrar únicamente el objeto único acordado, con permiso. No ejecutar limpieza global de buckets.

Resultado esperado: la implementación real escribe y recupera el mismo análisis JSON, validado, sin simular OCI y sin exponer credenciales. Ante fallos debe conservar una respuesta controlada y no afirmar persistencia exitosa.

## Estado actual

Procedimiento listo. Ejecución y evidencia bloqueadas por S3-04A de Drazen y por verificación de cuenta/permisos. No hay resultado real aprobado todavía.
