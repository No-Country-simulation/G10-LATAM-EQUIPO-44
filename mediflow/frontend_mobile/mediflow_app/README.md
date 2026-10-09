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
