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
