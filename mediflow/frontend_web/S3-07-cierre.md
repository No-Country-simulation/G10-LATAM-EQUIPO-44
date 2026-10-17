# Flor — cierre S3-07.3 y verificación S3-07

17 de octubre de 2026. Alcance: detalle de lectura del historial web.

## Resultado

El diálogo existente consulta `GET /api/documents/{id}` con el identificador
real de la fila. El JSON mostrado proviene de esa respuesta individual; no se
usa el documento previamente recibido por el listado en modo conectado.
El listado conserva su consulta, adaptador, filtros, orden, paginación y actualización.

El cliente HTTP comparte transporte entre listado y detalle: base URL existente,
GET explícito, timeout y errores controlados. El ID se codifica como segmento de
ruta. Se valida la estructura de la respuesta individual y que su ID coincida
con el solicitado. No se muestra el cuerpo de errores del proveedor.

El diálogo se abre de inmediato, vacía el JSON anterior e indica carga mediante
texto accesible y `aria-busy`. Conserva estados de error e inexistencia (404).
Un clic repetido con el mismo documento abierto no repite la consulta. Cerrar y
reabrir durante una petición pendiente reutiliza esa petición; tras completarse,
una nueva apertura consulta de nuevo para evitar una caché desactualizada.
Respuestas tardías no sobrescriben otro documento ni actualizan un diálogo cerrado.
Para reintentar tras un fallo se cierra y abre de nuevo.

`?demo=1` mantiene explícitamente los documentos sintéticos locales y no consulta
la API ni sustituye errores reales por mocks. Su selección se conserva durante
la sesión de la página, aunque los filtros reescriban la URL.

## Archivos de esta intervención

| Archivo | Cambio |
| --- | --- |
| `D:\Nocountru\mediflow\frontend_web\src\assets\js\documents-api.js` | Añade GET individual validado y comparte el transporte existente. |
| `D:\Nocountru\mediflow\frontend_web\src\assets\js\document-detail.js` | Nuevo controlador del ciclo de lectura del diálogo existente. |
| `D:\Nocountru\mediflow\frontend_web\src\historial\app.js` | El clic de la fila solicita el ID mediante el cliente y conserva demo explícita. |
| `D:\Nocountru\mediflow\frontend_web\src\historial\index.html` | Añade estado accesible de consulta y carga el controlador. |
| `D:\Nocountru\mediflow\frontend_web\tests\document-detail.test.js` | 30 pruebas nuevas del cliente, controlador, clic del historial y HTTP local. |
| `D:\Nocountru\mediflow\frontend_web\src\README.md` | Actualiza el estado vigente y enlaza esta guía. |
| `D:\Nocountru\mediflow\frontend_web\S3-07-cierre.md` | Este informe y guía de verificación. |

## Pruebas y evidencia

Desde `D:\Nocountru\mediflow\frontend_web`:

```powershell
node --test tests/*.test.js
node --check src/historial/app.js
node --check src/assets/js/documents-api.js
node --check src/assets/js/document-detail.js
```

**40/40 pruebas aprobadas**, cero fallos u omisiones: 10 existentes y 30 nuevas.
Sintaxis correcta en los tres scripts. Se cubren GET con ID codificado, identidad
de respuesta, HTTP 404/503, red, timeout, JSON malformado, estructuras inválidas,
datos distintos al listado, carga, reintento, solicitudes duplicadas, cambios de
selección, cierres y respuestas tardías. Se ejecuta el clic delegado del historial
en un DOM de prueba, conectado y en demo, comprobando que el listado no cambie.
La prueba HTTP local usa un servidor sintético real de Node y fetch real, sin nube.

Además se verificó el backend real existente y OCI mediante lectura del documento
sintético MF_004 persistido durante la regresión anterior:

```text
GET http://127.0.0.1:8000/api/documents/DOC-CLIN-F04C1ABCB6BF4BC59B0B7E0C66F7D56F
HTTP 200
ID de respuesta coincide: sí
Respuesta pública válida: sí
Prioridad Urgente conservada: sí
```

En navegador se cargó el listado real (34 registros en esa ejecución), se filtró
el ID sintético y se abrió su diálogo. Se observó `Consultando documento...`
y después `Documento cargado.` con su JSON individual. La evidencia técnica de
GET se obtuvo también con el mismo cliente web contra el backend, registrando
solo ID, URL, método y resultado; no incluye valores clínicos.
No se enviaron documentos a Gemini ni se hicieron mutaciones en servicios.

Entregables: `flor-s3-get-individual.json`, `flor-s3-detalle.png`,
`flor-s3-verificacion.json`, `flor-s3-cambios.patch` e informe de cierre.
La captura corresponde exclusivamente al caso sintético identificado.

## Verificación manual reproducible en navegador

1. Usar documentos sintéticos ya persistidos. Iniciar el backend existente:

   ```powershell
   Set-Location D:\Nocountru\mediflow\backend
   & .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
   ```

2. En otra terminal servir el frontend:

   ```powershell
   Set-Location D:\Nocountru\mediflow\frontend_web\src
   python -m http.server 8080 --bind 127.0.0.1
   ```

3. Abrir `http://127.0.0.1:8080/historial/` sin `demo=1`. Si la API usa otra
   dirección, configurar la variable pública existente `window.MEDIFLOW_API_BASE_URL`
   antes de cargar los scripts; no requiere credenciales de nube en el navegador.
4. En herramientas del navegador abrir Network y filtrar `api/documents`.
   La carga inicial muestra `GET /api/documents?limit=500`. Buscar el ID sintético
   real y pulsarlo. Aparece un GET distinto `/api/documents/{id}`, sin `limit`.
5. Comprobar HTTP 200 y coincidencia de `documento_id`. Comparar Response con
   el JSON del diálogo. Con red lenta debe verse carga y no quedar el JSON previo.
   Pulsar dos veces rápidamente no debe duplicar el GET individual. Cerrar y
   abrir después de terminar sí genera un GET nuevo; no recarga el listado.
6. Comprobar filtros, orden, paginación y Actualizar documentos como antes.
   `?demo=1` prueba la demostración local, no constituye evidencia de conexión.
7. Ejecutar la suite para reproducir 404, respuestas inválidas, fallos y carreras
   con datos controlados. El cliente también permite verificar un 404 real con
   un ID sintético inexistente mediante `MediFlowDocumentsApi.getDocument(id)`.
   La interfaz conserva el mensaje y permite reintentar cerrando y reabriendo.

## Cierre y límites de S3-07

S3-07.3 completado: lectura individual conectada y probada. S3-07 verificado en
el alcance solicitado de historial/listado/detalle y manejo de errores. Las
pantallas restantes conservan su estado previo; no se afirma que todas estén
integradas por este cambio.

La comprobación real de otros documentos requiere backend y OCI disponibles;
una nueva ingesta/análisis requiere sus servicios y autorización habitual.
Errores 404/503, JSON inválido y concurrencia se verificaron de forma controlada;
no se provocaron fallos ni borrados en OCI para simularlos. No se hizo una matriz
de navegadores ni una prueba de producción o de autenticación multiusuario.

Aprobación/rechazo persistente y demás mutaciones de auditoría continúan en
Sprint 4. No se modificó backend, data_ai, Flutter, contrato ni configuración
de servicios. Se conservaron los cambios locales anteriores y no se hizo
commit, push ni merge. Las dos instancias locales de verificación se detienen
al finalizar.
