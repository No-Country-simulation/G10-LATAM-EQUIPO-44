> Cierre específico Drazen/Brando del 17-10-2026: dos muestras propias
> verificadas en OCI real, hacia procesados y auditoria_humana. Originales
> retenidos, tamaños/SHA-256 iguales, ETags condicionados, JSON y GET recuperados.
> No se reprodujo InsufficientServicePermissions; no se cambió IAM. La entrada
> estructurada fue fixture local explícita, sin llamada Gemini. Ver
> [informe vigente](cierre-drazen-brando-sprint-3-17-octubre.md); conserva la evidencia histórica siguiente.

# Verificación JSON en OCI — Edil y Drazen

> Agregado por Edil, 17 de octubre: repetición real aprobada tras la corrección
> OCI del usuario. Cinco pruebas OCI y dos Flutter HTTP aprobadas; JSON final y
> copia verificados directamente. El bloqueo de permisos descrito abajo es
> histórico y no se reprodujo. Ver
> [evidencia actual](evidencias/edil-revalidacion-17-octubre.json).

## Procedimiento vigente — 16 de octubre de 2026

Agregado por Edil: S3-04A ya está integrado en `main` desde `47701cb`.
El backend guarda el JSON de recepción antes de Gemini y el resultado final
después de verificar la copia del archivo. Los GET recuperan esos resultados.
Las notas anteriores de bloqueo por ausencia de persistencia quedan como
historial al final de esta guía; no describen el código actual.

El 16 de octubre se ejecutaron de nuevo las tres pruebas reales de escritura
y lectura JSON: **3 aprobadas**. Cada una validó el contrato, guardó un JSON
sintético, lo recuperó directamente y mediante la búsqueda por ID, comparó el
contenido y limpió únicamente su objeto de prueba. No utilizaron Gemini.
La evidencia conjunta para revisión con Drazen está en
[cierre-edil-sprint-3-16-octubre.md](cierre-edil-sprint-3-16-octubre.md).
Esto no afirma que Drazen haya participado presencialmente en esta ejecución.

### Configuración local

El backend carga `D:\Nocountru\mediflow\.env`, independientemente de la carpeta
desde la que se ejecute; las variables ya exportadas tienen prioridad.
Conservar el archivo si existe. Crear uno desde `.env.example` solo cuando
no exista y completarlo localmente, sin compartir secretos:

```dotenv
OCI_CONFIG_PROFILE=DEFAULT
OCI_BUCKET_RECIBIDOS=recibidos
OCI_BUCKET_PROCESADOS=procesados
OCI_BUCKET_AUDITORIA=auditoria_humana
GEMINI_API_KEY=
GEMINI_MODEL=
```

Son tres buckets independientes, sin prefijo `recibidos/`. La clave privada
OCI permanece fuera del repositorio, referenciada por el perfil local.
Flutter recibe únicamente la URL de la API; nunca necesita claves OCI/Gemini.
El perfil necesita crear, leer y eliminar los objetos sintéticos de estas
pruebas. El análisis completo también necesita permisos de copia entre buckets.

### Escritura y lectura JSON reales, sin consumir Gemini

Ejecutar solo con una cuenta autorizada. Desde PowerShell:

```powershell
Set-Location 'D:\Nocountru\mediflow\backend'
$env:RUN_OCI_INTEGRATION = '1'
$edilTestTemp = Join-Path $env:TEMP ('MediFlow-edil-json-' + [guid]::NewGuid().ToString('N'))
try {
    & .\.venv\Scripts\python.exe -m pytest tests/test_oci_integration.py -k json_roundtrip_three_buckets -m integration -q -p no:cacheprovider --basetemp $edilTestTemp
} finally {
    Remove-Item Env:RUN_OCI_INTEGRATION -ErrorAction SilentlyContinue
}
```

Resultado esperado: `3 passed, 1 deselected`. El test usa métodos reales de
`OCIStorageManager`; comprueba `recibido`, `procesado` y `auditoria_humana`
en sus buckets respectivos. Un error de IAM, red, escritura, lectura o limpieza
hace fallar la prueba. No ejecutar limpiezas generales del bucket.

### Flutter → API → OCI → consulta por ID

En una terminal, iniciar una instancia de prueba aislada, sin recarga automática:

```powershell
Set-Location 'D:\Nocountru\mediflow\backend'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8137 --no-access-log
```

En otra terminal:

```powershell
Set-Location 'D:\Nocountru\mediflow\frontend_mobile\mediflow_app'
$edilEvidence = Join-Path $env:TEMP ('MediFlow-edil-http-' + [guid]::NewGuid().ToString('N'))
flutter test --no-pub test/triage_live_http_test.dart --dart-define=RUN_MEDIFLOW_HTTP_INTEGRATION=true --dart-define=MEDIFLOW_LIVE_API=http://127.0.0.1:8137 "--dart-define=MEDIFLOW_EVIDENCE_DIR=$edilEvidence"
```

Resultado esperado: una prueba aprobada y la de análisis omitida. Ejecuta un
solo POST con `analyze=false`, luego `TriageApiService.getDocument` sobre el
mismo ID. Exige igualdad del JSON recibido y recuperado, estado `recibido` y
guarda metadatos en `flutter-http.json`. Ese estado no significa análisis terminado.
El archivo sintético y su JSON permanecen en OCI para revisión; no hay borrado
automático ni reenvío en esta prueba HTTP.

Para incluir **una** solicitud real a Gemini con otro documento sintético,
configurar localmente clave/modelo y, solo con autorización y cuota disponible:

```powershell
flutter test --no-pub test/triage_live_http_test.dart --dart-define=RUN_MEDIFLOW_HTTP_INTEGRATION=true --dart-define=RUN_MEDIFLOW_GEMINI_INTEGRATION=true --dart-define=MEDIFLOW_LIVE_API=http://127.0.0.1:8137 "--dart-define=MEDIFLOW_EVIDENCE_DIR=$edilEvidence"
```

Resultado esperado: dos aprobadas. La segunda exige `procesado` o
`auditoria_humana`, confianza de clasificación válida y el mismo JSON por GET.
No fuerza una prioridad ni una decisión clínica. Si falla, registra el HTTP y
consulta el ID reconocido sin otro POST; sigue siendo una prueba fallida.
`flutter-analysis.json` contiene solo metadatos técnicos, nunca texto del documento
ni la respuesta clínica completa. Detener el servidor de prueba con Ctrl+C.

La suite habitual omite ambas pruebas reales: no consume servicios externos.
La prueba de dispositivo/cámara y el binario instalable corresponden a Sprint 4.

### Bloqueo detectado el 16 de octubre — resuelto en la repetición del 17

Agregado por Edil: la recepción/GET aprobó, pero el análisis completo falló al
copiar entre buckets. Diagnóstico real del mismo TXT sintético, sin repetir
Gemini: `InsufficientServicePermissions` (OCI HTTP 400), presentado por la API
como fallo controlado HTTP 503. El ID y el JSON `recibido` siguen recuperables.

Un administrador OCI debe revisar la autorización del servicio regional
`objectstorage-<region_identifier>` para copiar en el ámbito de los buckets
del proyecto. No basta con que el usuario pueda hacer upload/download.
La consola, al abrir la acción Copy, comprueba las políticas y señala las
ausentes; ver [permisos de copia de Oracle](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/copyingobjects.htm).
No se han modificado IAM, el perfil, la clave ni el modelo durante el cierre.
Repetir la prueba completa solo después de resolver ese permiso; no usar
reenvíos repetidos como solución ni presentar este fallo como un problema Flutter.

<details>
<summary>Historial del procedimiento anterior; no usar como estado actual</summary>

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

</details>
