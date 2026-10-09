# Integracion local de Sprints 1 y 2

Fecha: 2026-10-09. Rama: integration/sprints-1-2.
Base: origin/main 6c1357d.
Trabajo preservado: develop b876dd1 y 44 archivos locales (22 modificados, 22 nuevos).

## Estado Git

Se uso un worktree independiente para no cambiar D:\Nocountru ni sus fuentes.
El merge de origin/develop se preparo con --no-ff --no-commit.
No hay commit nuevo, push, Pull Request ni modificacion de main.
MERGE_HEAD identifica b876dd1. HEAD sigue en 6c1357d hasta autorizar el commit.
La rama de integracion no tiene upstream para evitar publicar accidentalmente.
Los cambios originales y el respaldo siguen disponibles.

## Ramas y commits

develop contiene Mediaflow_flutter, correccion_conexion_OCI, feature/contratoJSON
y el endpoint fb11d20 de feature/S2-triage-oci; no se fusionaron otra vez.
Commits que entran desde develop:
b876dd1, 11c8e6e, 69225d0, 09ec426, 315161e, 6c1205b, fb11d20,
ed4c9a3, 6d2dcad, 9082a19, 6327510.
La autoría original de los módulos se conserva en ese historial.
El commit c839a90 de Drazen se reviso y se adapto selectivamente; NO se
fusiono como ancestro ni se cherry-pickeo. Su referencia queda documentada.
sprint2-s2-06 sigue en 6c1357d y no aporta implementación nueva.

## Resoluciones y versiones conservadas

- No hubo conflictos de Git al combinar main y develop.
- Las modificaciones locales de archivos existentes se aplicaron como parche
  validado con git apply --check --index sobre la base conocida de develop.
- Los archivos sin seguimiento se copiaron solo a destinos inexistentes;
  los hashes SHA256 del respaldo y de esas copias fueron verificados.
- OCI usa tres buckets independientes: recibidos, procesados, auditoria_humana.
  Se conserva OCISettings, OCI_CONFIG_PROFILE y OCI_CONFIG_FILE.
- Se mantiene exclusivamente la carga de mediflow/.env en environment.py,
  con prioridad para variables ya exportadas. No se agrega config.py duplicado.
- De c839a90 se adopta configuración tipada de ENVIRONMENT/DEBUG mediante
  pydantic-settings en environment.py y el campo environment en GET /.
- No se adopta la búsqueda múltiple de .env ni la pérdida de selección de perfil.
  Tampoco se reemplazan el cliente inyectable ni las pruebas seguras por versiones antiguas.
- DEBUG queda desactivado por defecto. DEBUG=release exportado por herramientas
  Windows se trata como False; otros valores booleanos inválidos fallan claramente.
- Se conservan validación de tamaño/extensión, UUID completo y errores sin
  detalles internos del endpoint probado.
- La eliminación de triage_status_screen.dart es heredada de develop:
  el archivo de main era vacío; no se eliminó una implementación funcional.
- Se preservan los fixtures mock web como demostración explícita de Sprint 2.
- No se copian .env personales, ~/.oci/config ni claves privadas al worktree.
- Corrección adicional mínima: errata "al los buckets" del README.
- El intento de copia masiva fue rechazado por revisión automática; no se ejecutó.
  Se sustituyó por comparación de base, validación de parche y copia sin colisiones.

## Pruebas de esta integración

- Backend: 29 passed, 1 deselected; OCI real excluido.
- Prueba OCI real: 1 test recolectado, no ejecutado.
- FastAPI: arranque real local y GET / 200; solo el servidor de prueba fue detenido.
- Dependencias Python: pip check sin requisitos rotos.
- Frontend web: 4 tests aprobados y sintaxis JavaScript válida.
- Flutter: pub get correcto, analyze sin errores, 83 tests aprobados.
- Advertencia no bloqueante de Starlette: transición de TestClient hacia httpx2.
- No se hizo una nueva compilación nativa Windows; la validación actual es
  análisis y tests. La compilación aprobada anterior no se presenta como nueva.

## Seguridad y límites

No se detectaron .env, .pem, .key, .p12 o .pfx en archivos versionables,
ni marcadores de claves privadas o tokens reconocibles en la revisión realizada.
.env.example contiene referencias y ejemplos; nunca secretos reales.
.gitignore protege .env, claves y .oci/.
Esta comprobación no certifica que el dataset sea sintético; el equipo debe
confirmar la procedencia de los documentos clínicos ya presentes en main.

## Pendientes explícitos

Nicolas: test_llm.py y master_prompt.txt están vacíos; faltan conexión LLM,
prompt maestro y preparación del documento para extracción.
Laura: falta validar respuestas del LLM con ejemplos correctos/incorrectos;
Pydantic actual no equivale a validación clínica ni cálculo de confianza.
Brando: falta endpoint -> preparación de contenido -> LLM -> validación ->
respuesta. La rama S2-06 no contiene esos cambios.
El contrato requiere acuerdo sobre medicamentos/dosis y rechazo de claves
desconocidas; no se inventa una nueva versión durante esta integración.
No existe prueba nueva HTTP -> OCI real; requiere autorización específica.
El movimiento OCI necesita validación robusta de copia antes de utilizarse
para enrutamiento automático. No se alteró esa funcionalidad en esta tarea.
Flutter mantiene respuesta básica Sprint 2; la representación clínica completa
y los GET/panel conectado pertenecen a etapas posteriores.

## Recomendación

Se puede preparar un commit de integración de las entregas disponibles con
estas observaciones. NO es una declaración de Sprint 2 completo ni MVP final.
Esperar autorización expresa antes de commit o push.

## Archivos locales preservados por grupo

### Backend y pruebas

- mediflow/backend/app/api/routes.py
- mediflow/backend/app/core/contrato.json
- mediflow/backend/app/main.py
- mediflow/backend/README.md
- mediflow/backend/tests/test_oci_error_handler.py
- mediflow/backend/tests/test_oci_integration.py
- mediflow/backend/tests/test_triage_api.py


### Configuracion OCI

- docs/sprint-1/manejo_errores_oci.md
- mediflow/.env.example
- mediflow/backend/app/core/environment.py
- mediflow/backend/app/core/oci_client.py
- mediflow/backend/tests/test_environment.py
- mediflow/backend/tests/test_oci_client.py


### Flutter y Windows

- mediflow/frontend_mobile/mediflow_app/.metadata
- mediflow/frontend_mobile/mediflow_app/lib/config/api_config.dart
- mediflow/frontend_mobile/mediflow_app/lib/screens/document_selection_screen.dart
- mediflow/frontend_mobile/mediflow_app/lib/services/triage_api_service.dart
- mediflow/frontend_mobile/mediflow_app/README.md
- mediflow/frontend_mobile/mediflow_app/test/api_config_test.dart
- mediflow/frontend_mobile/mediflow_app/test/triage_flow_test.dart
- mediflow/frontend_mobile/mediflow_app/windows/.gitignore
- mediflow/frontend_mobile/mediflow_app/windows/CMakeLists.txt
- mediflow/frontend_mobile/mediflow_app/windows/flutter/CMakeLists.txt
- mediflow/frontend_mobile/mediflow_app/windows/flutter/generated_plugin_registrant.cc
- mediflow/frontend_mobile/mediflow_app/windows/flutter/generated_plugin_registrant.h
- mediflow/frontend_mobile/mediflow_app/windows/flutter/generated_plugins.cmake
- mediflow/frontend_mobile/mediflow_app/windows/runner/CMakeLists.txt
- mediflow/frontend_mobile/mediflow_app/windows/runner/flutter_window.cpp
- mediflow/frontend_mobile/mediflow_app/windows/runner/flutter_window.h
- mediflow/frontend_mobile/mediflow_app/windows/runner/main.cpp
- mediflow/frontend_mobile/mediflow_app/windows/runner/resource.h
- mediflow/frontend_mobile/mediflow_app/windows/runner/resources/app_icon.ico
- mediflow/frontend_mobile/mediflow_app/windows/runner/runner.exe.manifest
- mediflow/frontend_mobile/mediflow_app/windows/runner/Runner.rc
- mediflow/frontend_mobile/mediflow_app/windows/runner/utils.cpp
- mediflow/frontend_mobile/mediflow_app/windows/runner/utils.h
- mediflow/frontend_mobile/mediflow_app/windows/runner/win32_window.cpp
- mediflow/frontend_mobile/mediflow_app/windows/runner/win32_window.h


### Frontend web

- mediflow/frontend_web/src/assets/js/documents-mock.js
- mediflow/frontend_web/src/historial/app.js
- mediflow/frontend_web/src/historial/index.html
- mediflow/frontend_web/src/historial/styles.css
- mediflow/frontend_web/src/README.md
- mediflow/frontend_web/tests/documents-mock.test.js

## Lista completa frente a main

- M	README.md
- A	docs/integration/sprints-1-2.md
- M	docs/sprint-1/manejo_errores_oci.md
- M	mediflow/.env.example
- A	mediflow/backend/README.md
- M	mediflow/backend/app/api/routes.py
- A	mediflow/backend/app/core/contrato.json
- A	mediflow/backend/app/core/detalleContrato.md
- A	mediflow/backend/app/core/environment.py
- M	mediflow/backend/app/core/oci_client.py
- M	mediflow/backend/app/core/oci_error_handler.py
- M	mediflow/backend/app/main.py
- M	mediflow/backend/app/models/schemas.py
- A	mediflow/backend/prueba_oci.txt
- A	mediflow/backend/pytest.ini
- A	mediflow/backend/test_oci.py
- A	mediflow/backend/tests/test_environment.py
- A	mediflow/backend/tests/test_oci_client.py
- M	mediflow/backend/tests/test_oci_error_handler.py
- M	mediflow/backend/tests/test_oci_integration.py
- A	mediflow/backend/tests/test_triage_api.py
- M	mediflow/frontend_mobile/mediflow_app/.metadata
- M	mediflow/frontend_mobile/mediflow_app/README.md
- M	mediflow/frontend_mobile/mediflow_app/android/app/src/debug/AndroidManifest.xml
- A	mediflow/frontend_mobile/mediflow_app/android/app/src/debug/res/xml/dev_network_security_config.xml
- M	mediflow/frontend_mobile/mediflow_app/android/app/src/main/AndroidManifest.xml
- A	mediflow/frontend_mobile/mediflow_app/android/gradle/wrapper/gradle-wrapper.jar
- A	mediflow/frontend_mobile/mediflow_app/android/gradlew
- A	mediflow/frontend_mobile/mediflow_app/android/gradlew.bat
- M	mediflow/frontend_mobile/mediflow_app/lib/app.dart
- A	mediflow/frontend_mobile/mediflow_app/lib/config/api_config.dart
- M	mediflow/frontend_mobile/mediflow_app/lib/models/selected_document.dart
- A	mediflow/frontend_mobile/mediflow_app/lib/models/triage_result.dart
- M	mediflow/frontend_mobile/mediflow_app/lib/screens/document_selection_screen.dart
- M	mediflow/frontend_mobile/mediflow_app/lib/screens/home_screen.dart
- D	mediflow/frontend_mobile/mediflow_app/lib/screens/triage_status_screen.dart
- M	mediflow/frontend_mobile/mediflow_app/lib/services/file_picker_service.dart
- A	mediflow/frontend_mobile/mediflow_app/lib/services/triage_api_service.dart
- M	mediflow/frontend_mobile/mediflow_app/pubspec.lock
- M	mediflow/frontend_mobile/mediflow_app/pubspec.yaml
- A	mediflow/frontend_mobile/mediflow_app/test/api_config_test.dart
- M	mediflow/frontend_mobile/mediflow_app/test/helpers/stub_platform_file.dart
- A	mediflow/frontend_mobile/mediflow_app/test/triage_api_service_test.dart
- A	mediflow/frontend_mobile/mediflow_app/test/triage_flow_test.dart
- M	mediflow/frontend_mobile/mediflow_app/test/widget_test.dart
- A	mediflow/frontend_mobile/mediflow_app/windows/.gitignore
- A	mediflow/frontend_mobile/mediflow_app/windows/CMakeLists.txt
- A	mediflow/frontend_mobile/mediflow_app/windows/flutter/CMakeLists.txt
- A	mediflow/frontend_mobile/mediflow_app/windows/flutter/generated_plugin_registrant.cc
- A	mediflow/frontend_mobile/mediflow_app/windows/flutter/generated_plugin_registrant.h
- A	mediflow/frontend_mobile/mediflow_app/windows/flutter/generated_plugins.cmake
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/CMakeLists.txt
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/Runner.rc
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/flutter_window.cpp
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/flutter_window.h
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/main.cpp
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/resource.h
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/resources/app_icon.ico
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/runner.exe.manifest
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/utils.cpp
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/utils.h
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/win32_window.cpp
- A	mediflow/frontend_mobile/mediflow_app/windows/runner/win32_window.h
- M	mediflow/frontend_web/src/README.md
- A	mediflow/frontend_web/src/assets/js/documents-mock.js
- M	mediflow/frontend_web/src/historial/app.js
- M	mediflow/frontend_web/src/historial/index.html
- M	mediflow/frontend_web/src/historial/styles.css
- A	mediflow/frontend_web/tests/documents-mock.test.js
- M	mediflow/requirements.txt
