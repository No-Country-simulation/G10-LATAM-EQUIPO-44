# mediflow_app

Aplicación Android de MediFlow, desarrollada con Flutter, Dart y Material 3.
Conserva la navegación y selección local de PDF, JPG, JPEG, PNG y TXT del Sprint 1.
En Sprint 2 incorpora envío multipart a `POST /api/triage`, progreso, resultado
básico, timeout y reintento manual. El procesamiento se realiza en el backend.

Consulta [la documentación de Edil](../README.md) para requisitos, ejecución,
estructura y pruebas.

Con Android Emulator y FastAPI disponible en el host:

```powershell
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

El HTTP local está habilitado solo en debug. Release requiere configurar una URL
HTTPS. No hay un modo mock en producción ni credenciales OCI/LLM en la aplicación.
