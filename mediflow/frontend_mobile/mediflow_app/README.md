# mediflow_app

Aplicación Android y Windows de MediFlow, desarrollada con Flutter, Dart y Material 3.
Conserva la navegación y selección local de PDF, JPG, JPEG, PNG y TXT del Sprint 1.
En Sprint 2 incorpora envío multipart a `POST /api/triage`, progreso, resultado
básico, timeout y reintento manual. El procesamiento se realiza en el backend.

El servidor debe estar iniciado desde `mediflow/backend`. En el emulador,
`10.0.2.2` representa la PC anfitriona. En un teléfono físico usa la IP LAN de
la PC con `--dart-define=API_BASE_URL=http://IP_DE_LA_PC:8000` y permite el
puerto en la red local. Inicia Uvicorn con `--host 0.0.0.0` para ese caso.

Con Android Emulator y FastAPI disponible en el host:

```powershell
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

El HTTP local está habilitado solo en debug. Release requiere configurar una URL
HTTPS. No hay un modo mock en producción ni credenciales OCI/LLM en la aplicación.

Sprint 2: la respuesta `201` con `status=recibido` confirma la recepción; no
indica que el análisis clínico haya terminado. Se muestran estado e identificador.
El detalle clínico completo pertenece al Sprint 3. El envío real escribe en OCI.

Pruebas locales sin OCI:

```powershell
flutter analyze
flutter test
```

## Windows

Requiere Visual Studio con las herramientas de desarrollo de escritorio C++.
Desde esta carpeta:

```powershell
flutter run -d windows
```

En debug, Windows usa `http://127.0.0.1:8000` para el backend local. Android
conserva `http://10.0.2.2:8000`. Se puede cambiar con `--dart-define=API_BASE_URL=URL`.
La selección de archivos funciona sin backend; el envío requiere que la API esté activa.

Para compilar distribución:

```powershell
flutter build windows --release --dart-define=API_BASE_URL=https://TU_SERVIDOR
```

## Integración IA de Sprint 2 — Agregado por Edil

Motivo: completar el envío a la IA sin transmitir automáticamente documentos
a un proveedor externo. La casilla de autorización Gemini está apagada por
defecto y se reinicia al cambiar o quitar el archivo.
Sin autorización, analyze=false mantiene recepción y almacenamiento OCI.
Con autorización expresa para el documento seleccionado, analyze=true solicita
al backend análisis con Google Gemini. Puede generar costes y exige permiso
para compartir ese contenido. Las pruebas usan exclusivamente datos sintéticos.
La UI distingue recibido, procesado y auditoria_humana y muestra tipo/prioridad.
Timeout cliente: 90 segundos para permitir OCI más Gemini; reintento siempre manual.
El formulario multipart y el selector originales se conservan.


## Sprint 3 — Agregado por Edil
La respuesta se valida antes de mostrarla como éxito. Un JSON vacío o un estado contradictorio se trata como error.
Los resultados muestran tipo, prioridad, destino y motivo devueltos por el backend.
La alerta visual aparece solo si el análisis devuelve Urgente; puede coexistir con revisión humana. La app no decide la urgencia ni envía una notificación por su cuenta.
Para análisis sigue siendo necesario el consentimiento por archivo para Gemini.
Ver docs/sprint-3/edil-s3-08-y-s3-04b.md y guia-verificacion-json-oci.md para dependencias y validación real pendiente.


## Cámara Android — Agregado por Edil
Tomar foto abre la cámara del dispositivo. Revisar foto permite ampliar, cancelar o repetir; Usar esta foto vuelve al documento sin enviarlo.
Al confirmar una captura nueva, Gemini vuelve a quedar desautorizado hasta marcar el consentimiento por archivo.
Se comprueba JPG/PNG y un máximo de 10 MiB; una imagen que no se visualiza no se puede confirmar.
Android puede recuperar una captura pendiente después de reiniciar la actividad y vuelve a pedir revisión. Windows mantiene selección de archivos, sin webcam.
Después de agregar este plugin, detén Flutter y vuelve a ejecutar flutter run; hot reload no instala plugins nativos nuevos.
Ver docs/sprint-3/camara-documentos.md para uso y limitaciones. La cámara física, orientación y extracción clínica requieren prueba real sintética.


## Design System — Agregado por Edil
Tema Medical Clean centralizado en lib/design_system con AppColors, AppTypography, AppSpacing y AppTheme.
AppButton, AppCard, AppHeader y AppStatusPanel comparten estilo y controles Material 3; no hay navegación inferior.
Roboto está empaquetada localmente con licencia. Inicio, selección, archivo, revisión de foto, progreso y resultado comparten el lenguaje visual.
Éxito se distingue de auditoría y error mediante texto, iconos y colores. La prioridad propuesta por el servidor no se presenta como decisión clínica definitiva.
Ver docs/sprint-3/design-system.md para tokens, verificación y alcance.

## Correcciones de cierre de Flutter Sprint 3 — Agregado por Edil

El selector rechaza documentos vacíos o mayores de 10 MiB antes de enviarlos.
El servicio HTTP vuelve a comprobar el tamaño real al preparar el multipart,
porque el archivo local puede cambiar después de seleccionarlo.

Si falla el análisis y el backend entrega X-Document-ID, la app conserva el ID
y muestra Consultar documento. Usa GET /api/documents/{id}: no vuelve a subir
el archivo, no ejecuta Gemini y no reinicia el análisis. Un resultado recibido
confirma almacenamiento/recepción; no representa extracción terminada.
Actualizar estado permite consultar cambios posteriores sin otro POST.
Si la consulta falla, se conserva el último resultado confirmado y se avisa
que no pudo actualizarse; no se presenta ese resultado como recién consultado.

Tras un timeout o fallo de red sin ID, Reintentar pide confirmación y explica
el posible duplicado. No hay reintentos automáticos. Cambiar o quitar archivo
reinicia el seguimiento y el consentimiento. Volver a seleccionar el mismo
archivo puede crear otro envío: el backend aún no tiene idempotencia.
El ID se mantiene solo en memoria durante esta pantalla; no se guarda contenido
clínico ni se añade almacenamiento persistente de identificadores.

Los cambios no agregan campos JSON ni cambian endpoints o reglas de triaje.
No se calcula score operativo ni urgencia desde Flutter. La consulta depende
del backend existente; sin resultado JSON persistido, puede devolver 404 y la
app conserva el ID para consultar con el equipo.

Ver docs/sprint-3/cierre-edil-flutter-15-octubre.md para pruebas y aceptación pendiente.

## Diagnóstico frente a main 8ef6e09 — Agregado por Edil

La auditoría del 15 de octubre revisó main: en ese commit el servicio Flutter
tenía sendDocument (POST), sin getDocument ni botones de consulta. La recuperación
se implementó después en los cambios locales de feature/s3-edil-cierre-flutter.
Mientras esos cambios no se incorporen mediante un commit autorizado, main no
contiene esta función. No confundir una implementación local con código publicado.

Se reutilizan getDocument, Consultar documento y Actualizar estado existentes en
esta rama. Las consultas son manuales, con el mismo ID confirmado por el POST o
la cabecera X-Document-ID, y nunca vuelven a enviar el archivo ni ejecutan IA.
Sin ID, una recepción incierta no puede recuperarse inequívocamente desde Flutter:
no hay consulta por nombre de archivo ni se inventa un endpoint para localizarla.
El ID permanece solo en memoria mientras la pantalla sigue abierta.

La tarjeta presenta score_confianza_clasificacion del JSON actual como Confianza
de clasificación. No aplica umbrales, colores de aprobación ni decisiones a partir
de ese número. No muestra la confianza de recepción como si fuera un análisis.
Urgencia y revisión humana pueden coexistir y siguen dependiendo de la respuesta
validada del backend, no del porcentaje mostrado.

Dependencias pendientes del contrato definitivo: significado y calibración de la
confianza; reglas de completitud por tipo; invocación del detector y del score en
el pipeline; política de revisión y eventual reprocesamiento/idempotencia. No se
añaden score_operativo, es_ambiguo ni campos nuevos a las peticiones o respuestas.

Verificación de esta revisión: flutter analyze --no-pub sin problemas;
flutter test --no-pub con 178 pruebas aprobadas y una prueba real optativa omitida.
Incluye recuperación por ID, conservación de resultado tras fallo GET,
confirmación de reenvío y 16 casos nuevos de lectura/visualización de confianza.
No se llamaron OCI/Gemini ni se verificó cámara física en esta ejecución.
