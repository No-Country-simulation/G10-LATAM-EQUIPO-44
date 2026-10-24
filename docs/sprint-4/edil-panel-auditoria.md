# S4-07 Fase 2 — Panel web de auditoría humana

> Actualización agregada por Edil el 23/10/2026: la rama de integración ya incorpora
> la API de Drazen, la persistencia de Brando y el contrato de Eliana. El nuevo
> `review-http-adapter.js` conecta pendientes, decisión e historial; exige auditor
> explícito y observación para rechazo. El contenido del 17/10 que sigue documenta
> la fase anterior, cuando el contrato estaba pendiente. Estado y pruebas actuales:
> [integracion-23-octubre.md](integracion-23-octubre.md).

Agregado por Edil. Fecha: 17 de octubre de 2026. Base: `b2777d30dd3c7315675b8d449f13a3f2ac2c9f4e`.

## Alcance implementado

Se reutilizaron la pantalla `auditoria/`, el shell, navegación, estilos y tokens compartidos, botones y estilos de tarjetas/modales. No se creó otro proyecto ni se incorporó un framework o dependencia nueva.

La bandeja consulta el backend mediante `GET /api/documents?limit=500&status=auditoria_humana`. Muestra ID, tipo documental, prioridad, confianza de clasificación y estado del análisis. Permite buscar por ID/tipo, filtrar por prioridad y actualizar. El límite de 500 se declara en pantalla: la respuesta no demuestra que no existan más pendientes fuera de ese límite. No hay paginación del backend implementada en este cliente.

Cada apertura de detalle usa `GET /api/documents/{id}`, con ID codificado y validación del contrato actual. Muestra motivo de auditoría, prioridad, análisis, datos disponibles, medicamentos y JSON original. Se conserva cualquier prioridad Urgente; no se recalculan niveles MTS, confianza ni decisiones de triaje en el navegador.

Se añadieron observaciones, botones Aprobar/Rechazar, confirmación explícita y presentación de historial persistido, preparados mediante una interfaz interna de revisión. **El usuario confirmó que el contrato no está aprobado.** Por ello los botones permanecen deshabilitados y el historial indica la dependencia. No se envía ningún POST de revisión, no se ejecutan las rutas propuestas y no se fabrican decisiones ni firmas en memoria.

La observación solo existe en memoria durante la revisión de la página. No se guardan texto clínico, observaciones, documentos ni resultados en localStorage/sessionStorage. Para un futuro envío habilitado, sessionStorage guarda exclusivamente IDs de envíos sin confirmar y bloquea repeticiones tras una recarga. Eso es una protección de transporte, no un registro de auditoría ni evidencia de persistencia del backend.

## Conservación de la maqueta original

- La lógica previa de `auditoria/app.js` se conserva debajo de un retorno explícito, precedido por la llamada al panel conectado. Sus datos de ejemplo, firma ficticia, edición MTS y aprobación simulada no se ejecutan.
- El contenido principal y los modales anteriores quedan en `template#auditLegacyMain` y `template#auditLegacyDialogs`, inertes y no montados. Se mantienen como referencia de la entrega original.
- El shell visible ya no afirma conexión HIS, identidad de médico, firma digital, emergencia enviada ni latencia ficticia.
- El panel conectado no carga `documents-mock.js`; ese archivo se usa únicamente como fixture en las pruebas nuevas. No existe fallback a datos de ejemplo si falla el backend.

## Archivos

| Archivo, relativo a `mediflow/frontend_web/` | Cambio |
| --- | --- |
| `src/assets/js/documents-api.js` | Filtro opcional `status` existente en backend y exportación del validador reutilizable; historial mantiene su comportamiento anterior |
| `src/assets/js/reviews-api.js` | Interfaz reutilizable de lectura/decisión, capacidades por adaptador aprobado, validación de recibos y errores controlados |
| `src/assets/js/audit-controller.js` | Estado, deduplicación, confirmación, observaciones, resultados inciertos e historial |
| `src/auditoria/audit-panel.js` | Vista conectada y eventos, representación segura de texto, carga/error/vacío y devolución de foco |
| `src/auditoria/app.js` | Entrada al panel conectado; maqueta anterior conservada sin ejecutar |
| `src/auditoria/index.html` | Shell reutilizado, bandeja, detalle y confirmación accesibles; maqueta original inerte |
| `src/auditoria/styles.css` | Capa responsive sobre estilos existentes, urgencia explícita, foco visible y diálogos adaptables |
| `tests/reviews-api.test.js` | Cliente, filtro HTTP, estados, timeout, validación, recibos y bloqueo de repetición |
| `tests/audit-controller.test.js` | Estado, carreras de respuestas, conservación de datos, confirmación y persistencia incierta |
| `tests/audit-panel.test.js` | Interacciones de la vista con DOM de prueba, filtros, diálogos, observación, errores y representación de datos |

También se añadió este informe. `preparacion-base.md` de la fase anterior se conserva sin cambios. No se modificaron backend, Flutter, data_ai, esquemas ni contratos públicos.

## Estado de las conexiones

| Operación | Estado |
| --- | --- |
| GET `/api/documents?status=auditoria_humana` | Implementado mediante cliente existente; transporte probado contra servidor HTTP local de prueba |
| GET `/api/documents/{id}` | Implementado mediante cliente existente; sin reutilizar el listado como si fuera un detalle actualizado |
| GET `/api/reviews/pending` | Propuesta, sin aprobación ni implementación verificada; no se llama |
| POST `/api/documents/{id}/review` | Propuesta, sin aprobación ni implementación verificada; no se llama |
| GET `/api/documents/{id}/review-history` | Propuesta, sin aprobación ni implementación verificada; no se llama |

Filtrar análisis por `status=auditoria_humana` no equivale necesariamente a listar revisiones humanas aún pendientes. Cuando exista una decisión persistida separada del estado del análisis, Drazen debe ofrecer la bandeja pendiente y su adaptador. La versión actual se identifica como bandeja de análisis que requieren auditoría, sin inventar un estado humano.

## Preparación para el contrato aprobado

`MediFlowReviewsApi.createClient()` acepta un `approvedAdapter` opcional. En la página se toma de `window.MediFlowApprovedReviewAdapter`, que **no se define en producción actualmente**. No hay activación por query string, ruta supuesta ni mock de producción.

El adaptador necesita `approved: true`, `contractReference` no vacío y las funciones implementadas correspondientes. Estos metadatos de frontend no son autenticación ni autorización; los permisos y el control de concurrencia deben imponerse en backend.

La siguiente tabla define una **interfaz interna de JavaScript**, no el JSON HTTP aprobado ni nuevos campos de `TriageResponse`. El adaptador futuro será responsable de mapear el contrato acordado, rutas y autenticación hacia esta vista.

| Método interno | Entrada y resultado normalizados |
| --- | --- |
| `listPending({signal})`, opcional | Array de análisis válidos según el contrato actual; sustituye la lectura filtrada cuando se apruebe una API de pendientes humanos |
| `submitReview(input, {signal})` | Entrada `{documentId, decision: 'approve' o 'reject', observation}`. Resultado con `persisted: true`, `documentId`, `decision`, `observation`, `reviewId`, `auditor`, `reviewedAt` |
| `getReviewHistory(documentId, {signal})` | Resultado `{documentId, entries: [...]}`; cada entrada aporta `documentId`, `decision`, `observation`, `reviewId`, `auditor`, `reviewedAt` del servidor |

`reviewedAt` debe representar una fecha del servidor con zona horaria. No se inventa el auditor ni se usa el reloj del navegador para anunciar una decisión persistida. No se impone todavía una longitud mínima de observación ni obligatoriedad por aprobación/rechazo: esas reglas deben acordarse con el contrato.

El adaptador debe transformar errores HTTP conocidos a `MediFlowReviewsApi.ReviewApiError` con su status. Debe respetar la señal AbortSignal y no realizar reintentos automáticos de POST. Recibos incompletos, de otro documento, otra decisión u otra observación se consideran inciertos, no éxito.

## Duplicación, errores y conservación de datos

- Una carga de bandeja o detalle ya en vuelo se reutiliza. Los resultados antiguos no sobrescriben otro documento seleccionado ni reabren un diálogo cerrado.
- Si falla una actualización, se conserva la última bandeja o el detalle anterior, con aviso de posible desactualización. No se permite decidir sobre un detalle fallido o invalidado.
- Se contemplan 400, 401, 403, 404, 409, 422, 5xx, red, timeout y JSON incompatible. No se muestran cuerpos privados de error del servidor.
- Aprobar/Rechazar requieren detalle válido, contrato habilitado y confirmación. Durante el envío se deshabilitan acciones y cierre; el segundo clic no emite otro POST.
- Solo un recibo validado confirma persistencia y retira la fila; después se actualizan bandeja e historial. Un 404/409 exige consultar el documento otra vez.
- Una respuesta perdida o fallo 5xx bloquea nuevos envíos del documento, también tras recargar la misma pestaña. Un historial vacío o una revisión anterior no prueba qué ocurrió con el POST incierto: no se desbloquea automáticamente ni se anuncia que fue registrado.
- El bloqueo del navegador no sustituye idempotencia, transacciones o concurrencia en backend; otras pestañas, navegadores o dispositivos requieren protección del servidor. La reconciliación de envíos inciertos queda pendiente del contrato aprobado.
- El estado de análisis, la prioridad y la decisión de revisión se presentan por separado. No se cambia Urgente a Rutina al mostrar o revisar un documento.

## Pruebas y verificación

Ejecución local de referencia: **116 pruebas JavaScript aprobadas**, sin fallos ni omitidas: las 40 existentes y 76 nuevas. Los mocks/adaptadores simulados se usan exclusivamente dentro de `tests/`. No se enviaron datos a Gemini/OCI ni se registraron revisiones reales.

Cinco comprobaciones `node --check` aprobaron. Registro completo de la ejecución final: `C:\Users\leno\AppData\Local\Temp\MediFlow-S4-audit-final-3entgo9a\tests.log`. Se comprobaron también IDs activos únicos, correspondencia de selectores de la vista con el HTML y existencia de los cinco scripts; el código JS original quedó conservado debajo del retorno de entrada.

Se prueban lectura HTTP mediante servidor sintético local, estados HTTP, lista vacía, datos inválidos, red y timeout; observaciones, confirmación/cancelación, doble clic, conflictos, bloqueo tras recarga, historial, preservación de Urgente, conservación de resultados y escape de contenido del servidor.

Las interacciones de vista se prueban con un DOM mínimo de test, no con un navegador real. También se revisaron semántica de diálogos, viewport y reglas responsive. **La sesión de automatización no dispone de navegador habilitado** (`cua.getState`: sin navegadores; navegador `iab` no disponible). Por ello no se afirma verificación visual de escritorio/móvil, capturas reales o prueba táctil: quedan pendientes los pasos manuales de abajo. Tampoco se afirma una prueba de extremo a extremo con OCI y API de revisión real.

Comandos desde `D:\Nocountru\mediflow\frontend_web`:

```powershell
node --test tests/*.test.js
node --check src/assets/js/documents-api.js
node --check src/assets/js/reviews-api.js
node --check src/assets/js/audit-controller.js
node --check src/auditoria/audit-panel.js
node --check src/auditoria/app.js
```

## Cómo abrir el panel

Con el backend habitual ya iniciado en `http://127.0.0.1:8000`, servir solo el directorio público del frontend:

```powershell
Set-Location -LiteralPath 'D:\Nocountru'
.\mediflow\backend\.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1 --directory mediflow/frontend_web/src
```

Abrir `http://127.0.0.1:5500/auditoria/index.html`. No abrir con `file://` ni servir la raíz del proyecto, donde existe configuración privada. Si el backend está en otra dirección, el despliegue puede definir `window.MEDIFLOW_API_BASE_URL` antes de cargar `documents-api.js`, como en el cliente existente. No poner credenciales OCI/Gemini en esa configuración.

Comprobación manual pendiente en escritorio (1280 px) y móvil (360/390 px):

1. Verificar bandeja, indicador de lectura real, vacío, búsqueda/filtro y ausencia de desplazamiento horizontal de página.
2. Abrir un documento sintético Urgente y comprobar que ID, tipo, confianza, motivo y prioridad coinciden con GET individual. Recorrer campos y JSON, foco de teclado, scroll y cierre de diálogo.
3. Detener temporalmente el backend de prueba o simular red caída desde herramientas del navegador; actualizar y comprobar conservación/aviso de datos anteriores y reintento.
4. Sin adaptador aprobado, comprobar que Aprobar/Rechazar están deshabilitados y que no hay solicitudes a rutas propuestas ni historia ficticia.
5. Tras aprobación e implementación del adaptador, Eliana debe verificar ambigüedad → pendientes → detalle → aprobar/rechazar → historial real, con 401/403/404/409/422/5xx, pérdida de respuesta e intentos concurrentes. El éxito exige evidencia del servidor y prioridad Urgente conservada.

## Dependencias y estado Git

- **Drazen:** contrato aprobado de pendientes, decisión e historial; autenticación, permisos, códigos de error y control de concurrencia/idempotencia. Después implementar el adaptador contra esas rutas reales.
- **Brando:** persistencia durable y recuperable de decisión, ID de revisión, auditor autenticado, observación y fecha; comportamiento ante duplicados y fallos parciales sin borrar/modificar análisis original ni rebajar prioridad.
- **Eliana:** pruebas con backend y almacenamiento reales, verificación de recibos/historial y evidencia de integración. No reemplazarlas por las pruebas simuladas de esta fase.
- **Edil:** conexión del adaptador tras aprobación y verificación visual/dispositivo cuando haya navegador disponible.

Se mantiene la rama actual `main` con cambios locales sin confirmar, respetando la prohibición de cambiarla sin autorización de la fase anterior. No se hizo commit, push ni merge. Antes de confirmar el trabajo debe autorizarse crear la rama individual `feature/s4-edil-auditoria-web`, revisar los archivos y conservar el informe previo de preparación.
