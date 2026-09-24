# Flutter Mobile - Edil

Carpeta destinada al proyecto base Flutter, navegación y selección local de archivos.

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
