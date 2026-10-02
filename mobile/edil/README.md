# Flutter Mobile - Edil

Carpeta destinada al proyecto base Flutter, navegación y selección local de archivos.

La documentación del Sprint 1 se conserva como referencia histórica. El flujo
actual y los cambios de conectividad se describen en [Sprint 2](#sprint-2).

## Sprint 1

Objetivo: crear la base móvil de MediFlow con navegación y selección local de
documentos clínicos. El proyecto se encuentra en `mediflow_app/` y está preparado
para Android. Cada integrante trabaja de manera independiente durante este sprint.

## Funcionalidades

- Proyecto Flutter base con Dart y null safety.
- Material 3, diseño adaptable y textos en español.
- Navegación con `Navigator` entre inicio y selección de documento.
- Selección local de un archivo con `file_picker`.
- Validación de formatos en Dart, incluso si el selector devuelve otro formato.
- Visualización de icono, nombre, extensión, tamaño, tipo y ruta si está disponible.
- Cambio de documento y eliminación de la selección.
- Cancelar o encontrar un error conserva la selección anterior.
- Funcionamiento offline y metadatos únicamente en memoria.
- El botón `Continuar` solo muestra el aviso de integración para el Sprint 2.

## Formatos soportados

- PDF (`.pdf`).
- JPG (`.jpg`).
- JPEG (`.jpeg`).
- PNG (`.png`).
- TXT (`.txt`).

Las extensiones se comparan sin distinguir mayúsculas. Esta validación comprueba
el formato declarado por el nombre; no analiza el contenido clínico del archivo.

## No incluido en Sprint 1

- Backend.
- API REST.
- `POST /api/triage`.
- OCI.
- Inteligencia Artificial.
- Clasificación.
- Extracción clínica.
- Autenticación.
- Persistencia de la selección o base de datos.
- Subida o procesamiento de documentos.

## Ejecución

Requisitos: Flutter 3.41.1 o compatible con Dart 3.11, Android SDK con sus licencias
aceptadas, Oracle JDK 21 completo instalado (con `bin/jlink`) y un dispositivo o
emulador Android. El archivo `android/gradle/gradle-daemon-jvm.properties` solicita
Oracle JDK 21 para que Gradle 8.14 no seleccione Java 25 de Android Studio ni el
runtime reducido de la extensión Java de VS Code. No contiene rutas de equipo.
La compilación incremental de Kotlin está desactivada en este proyecto para evitar
errores de caché en Windows cuando Pub y el repositorio están en discos distintos.

Desde la raíz del repositorio:

```powershell
cd mobile/edil/mediflow_app
flutter pub get
flutter devices
flutter run
```

Si no hay un Android conectado, inicia uno desde Android Studio o ejecuta:

```powershell
flutter emulators
flutter emulators --launch <id-del-emulador>
flutter run -d <id-del-dispositivo>
```

Comprobaciones y compilación:

```powershell
flutter analyze
flutter test
flutter build apk --debug
flutter build apk --release
```

Los APK se generan en `build/app/outputs/flutter-apk/`. La firma de release utiliza
la clave local de depuración del proyecto base: sirve para pruebas del sprint,
no para publicar en una tienda.

La instalación inicial de dependencias y herramientas puede necesitar internet.
Una vez instalada, la app funciona sin conexión. Las variantes debug/profile
conservan el permiso de internet de Flutter para las herramientas de depuración;
la variante release no solicita ese permiso ni utiliza servicios de red.

## Selección local y estado

`MainActivity.kt` añade `Intent.EXTRA_LOCAL_ONLY` al selector de Android para
solicitar exclusivamente archivos disponibles en el dispositivo. No se necesitan
permisos amplios de almacenamiento: se utiliza el selector del sistema.

El modelo no se guarda al cerrar la pantalla o reiniciar la app. Quitar un archivo
solo elimina la selección; no borra el documento original. `file_picker` puede
crear una copia temporal en la caché privada de Android, por lo que la ruta mostrada
puede corresponder a esa copia. No se registra ni se transmite el contenido.

## Estructura

```text
mediflow_app/
├── android/                         # Proyecto Android y selector solo local
├── lib/
│   ├── main.dart                    # Punto de entrada
│   ├── app.dart                     # Tema Material 3 e idioma español
│   ├── screens/
│   │   ├── home_screen.dart         # Inicio y navegación
│   │   └── document_selection_screen.dart # Estado y acciones de selección
│   ├── widgets/
│   │   └── selected_file_card.dart  # Información e icono del documento
│   ├── models/
│   │   └── selected_document.dart   # Modelo, tipos y tamaño legible
│   └── services/
│       └── file_picker_service.dart # Selector, validación y metadatos
├── test/
│   ├── file_picker_service_test.dart # Formatos, metadatos, cancelación y errores
│   ├── widget_test.dart             # Navegación, acciones y diseño adaptable
│   └── helpers/
│       └── stub_platform_file.dart  # Archivo simulado sin leer contenido
├── analysis_options.yaml            # Reglas flutter_lints
├── pubspec.yaml                     # Dependencias y configuración
├── pubspec.lock                     # Versiones resueltas reproducibles
└── README.md                        # Resumen y enlace a esta documentación
```

Dependencias directas: `flutter`, `flutter_localizations` (ambas del SDK) y
`file_picker: 13.1.0`. Dependencias de desarrollo: `flutter_test` (SDK) y
`flutter_lints: ^6.0.0`. No se añadieron clientes HTTP ni librerías de routing.

## Pruebas manuales

Utiliza archivos sintéticos, sin datos clínicos reales, guardados en Descargas.

1. Inicia la aplicación y comprueba el título MediFlow y la pantalla principal.
2. Pulsa `Seleccionar documento`; comprueba el estado sin archivo.
3. Abre `Buscar archivo` y cancela; verifica que no aparece un error.
4. Selecciona un PDF y comprueba nombre, extensión, tamaño, tipo, icono y ruta.
5. Repite con JPG, JPEG, PNG y TXT mediante `Cambiar archivo`.
6. Cancela después de haber seleccionado un archivo; debe conservarse el anterior.
7. Comprueba que el selector filtra otros formatos. La validación defensiva de un
   formato inválido devuelto por el selector se comprueba en las pruebas Dart.
8. Pulsa `Continuar`; solo debe aparecer el mensaje del Sprint 2.
9. Pulsa `Quitar archivo`; debe volver a `Ningún archivo seleccionado`.
10. Vuelve a inicio con la flecha o el botón Atrás de Android.
11. Activa el modo avión, desactiva Wi-Fi y repite el flujo con archivos locales.
12. Gira el dispositivo y aumenta el tamaño de texto; comprueba que puedes
    desplazarte para acceder a todos los botones.

Las pruebas automatizadas no sustituyen la comprobación del selector nativo en un
dispositivo. No se usa un archivo clínico real en los tests.

## Sprint 2

Objetivo: conectar la selección local de documentos con `POST /api/triage`
del backend Python/FastAPI, manteniendo la interfaz y formatos del Sprint 1.

### Funcionalidades agregadas

- Cliente HTTP sencillo con `http: ^1.6.0` y tipos MIME con `http_parser: ^4.1.2`.
- Envío `multipart/form-data` con un único archivo bajo el campo `file`.
- Estado `Procesando documento...` con indicador de progreso.
- Bloqueo de envío, cambio y eliminación durante la petición; no hay reintentos automáticos.
- Resultado básico: confirmación, `status`, `documento_id` y `message` si existen.
- Conservación del objeto JSON completo en `TriageResult.rawData`, solo en memoria.
- Errores de conexión, TLS, timeout, archivo no disponible, JSON inválido y HTTP.
- Timeout de 30 segundos para preparación, envío y lectura completa de respuesta.
- Botón `Reintentar` tras un fallo; conserva el archivo sin reabrir el selector.
- URL del backend, nombre del campo y timeout centralizados en `ApiConfig`.

### Flujo actual

`Seleccionar archivo → Procesar documento → Procesando → Resultado o error → Reintentar`

Seleccionar un documento no lo envía. El envío se inicia únicamente al pulsar
`Procesar documento`. Cambiar o quitar el archivo borra el resultado anterior.
Cancelar el selector conserva archivo y resultado. Tras un éxito se oculta el
botón de envío para evitar repetir la misma petición accidentalmente.

Cuando existe una ruta local, el envío utiliza el archivo mediante streaming.
Si el selector no ofrece ruta, se conservan sus bytes en memoria como respaldo.
No se procesa PDF, imagen ni texto dentro de Flutter. No se muestran campos
clínicos definitivos, ni se añaden autenticación o persistencia.

Al salir de la pantalla o vencer el timeout se cierra el transporte HTTP.
Esto no garantiza cancelar un procesamiento ya iniciado en el servidor. Un
reintento podría crear otro documento: la idempotencia debe acordarse con Backend.

### Ejecución con backend

Desde la raíz del repositorio, con el emulador Android abierto y el backend
FastAPI escuchando en el puerto 8000 del equipo:

```powershell
cd mobile/edil/mediflow_app
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

`10.0.2.2` es el acceso al equipo anfitrión desde Android Emulator; no es la
dirección de producción. Es el valor predeterminado **solo en debug**.
Para un teléfono físico, sustituye la URL por un host/IP accesible desde ese
teléfono. El backend debe escuchar en una interfaz accesible y permitir la
conexión de desarrollo. No uses `localhost` para apuntar al equipo desde el móvil.

`API_BASE_URL` es la base, sin `/api/triage`. Se permite un prefijo de ruta si
el despliegue lo necesita, y se normalizan las barras finales. No se aceptan
credenciales, parámetros de consulta ni fragmentos dentro de esta URL.

Para una compilación release, proporciona el endpoint HTTPS real; por ejemplo,
reemplaza el dominio de ejemplo antes de ejecutar:

```powershell
flutter build apk --release --dart-define=API_BASE_URL=https://backend.example.com
```

### Android y seguridad

El manifiesto principal incluye `android.permission.INTERNET` y deniega tráfico
HTTP sin cifrar. El recurso `src/debug/res/xml/dev_network_security_config.xml`
habilita HTTP **solo en debug** para poder probar tanto con emulador como con
teléfono físico y un host local configurable. Esa excepción no se empaqueta en
release/profile. No se desactiva la verificación de certificados TLS.

Fuera de debug, `ApiConfig` exige una URL HTTPS explícita; si falta o es inválida,
la pantalla presenta un error de configuración al intentar enviar.

La app no incluye credenciales OCI, LLM, tokens ni claves, no se conecta a esos
servicios directamente y no registra cuerpos JSON, contenido clínico ni archivos.
No sigue redirecciones HTTP automáticamente. Las simulaciones existen únicamente
en los tests: la aplicación normal siempre utiliza el cliente y endpoint reales.

### Archivos de integración

| Archivo | Responsabilidad |
| --- | --- |
| `lib/config/api_config.dart` | URL, endpoint, campo multipart y timeout |
| `lib/models/triage_result.dart` | Respuesta mínima tolerante y JSON original |
| `lib/services/triage_api_service.dart` | Multipart, códigos HTTP, timeout y cancelación local |
| `lib/models/selected_document.dart` | Metadatos originales y bytes opcionales |
| `lib/services/file_picker_service.dart` | Selección existente y respaldo cuando no hay ruta |
| `lib/screens/document_selection_screen.dart` | Estado con `setState`, resultado y reintento |
| `lib/app.dart`, `lib/screens/home_screen.dart` | Inyección para pruebas y explicación actualizada |
| `android/app/src/main/AndroidManifest.xml` | Permiso de red y restricción de HTTP |
| `android/app/src/debug/AndroidManifest.xml`, `android/app/src/debug/res/xml/dev_network_security_config.xml` | HTTP exclusivo de desarrollo |
| `test/api_config_test.dart` | Configuración y tolerancia del contrato |
| `test/triage_api_service_test.dart` | Multipart real serializado, formatos, códigos HTTP y fallos |
| `test/triage_flow_test.dart` | Progreso, bloqueo de duplicados, errores y reintentos |

Se actualizan también `pubspec.yaml`, `pubspec.lock` y las pruebas del Sprint 1.

### Pruebas del Sprint 2

```powershell
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
```

Las pruebas de HTTP usan clientes simulados sin backend externo. Comprueban el
método, URL, nombre del campo, MIME y contenido multipart; archivos por ruta y
bytes; 200/201/202 y 204 vacío; códigos de error; JSON inválido; archivos ausentes;
desconexión; timeout de cabeceras y cuerpo; reintento y bloqueo de doble envío.
Se conservan las pruebas de selección, cancelación, cambio, eliminación, iconos
y pantallas pequeñas del Sprint 1.

Verificación realizada el 26/09/2026: `flutter pub get` correcto,
`flutter analyze` sin incidencias, `flutter test` con 81 pruebas aprobadas y
`flutter build apk --debug` exitoso. Se generó y verificó el manifiesto release:
incluye permiso INTERNET y no contiene la excepción HTTP de debug. Gradle aún
emite avisos de herramientas sobre acceso nativo/deprecaciones, sin impedir
la compilación; no son errores del análisis Dart.

Con el backend real, validar manualmente:

1. Iniciar la app y seleccionar un PDF, una imagen y un TXT locales.
2. Procesar cada archivo y confirmar que Backend recibe un único campo `file`
   con nombre, tipo MIME y bytes correctos.
3. Verificar spinner y controles bloqueados durante el envío.
4. Confirmar que éxito muestra los datos mínimos disponibles del contrato real.
5. Probar respuestas 400 y 500, backend apagado y demora superior a 30 segundos.
6. Comprobar `Reintentar`, cambio/eliminación de selección y regreso a inicio.
7. Sin conexión, confirmar que la selección sigue funcionando y que enviar
   muestra un error comprensible, sin cerrar la app.

### Contrato pendiente con Drazen / Eliana

- Confirmar URL, ruta exacta `/api/triage` (sin barra final) y campo multipart `file`.
- Confirmar tipos MIME admitidos y límite de tamaño; todavía no se impone un límite
  local arbitrario. HTTP 413 tiene un mensaje específico.
- Confirmar códigos de éxito y si la respuesta siempre es un objeto JSON. Actualmente
  se aceptan 2xx con objeto JSON y 204 vacío; una lista o JSON malformado es error.
- Confirmar nombres y tipos de `status`, `documento_id` y `message`. Son opcionales;
  no se inventan campos clínicos ni se necesita un modelo clínico definitivo.
- Confirmar si 202 significa aceptación asíncrona. La app informa recepción y el
  estado devuelto; no hace polling ni afirma que el análisis clínico terminó.
- Acordar duración esperada, política de reintentos/idempotencia y futuros requisitos
  de autorización. 401/403 se muestran como error; no se implementa autenticación.

No se ha validado todavía contra el FastAPI real del equipo. La prueba con ese
servicio requiere su URL accesible y el contrato confirmado.
