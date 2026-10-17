# Cierre de Edil — Sprint 3 — 16 de octubre de 2026

## Actualización vigente — 17 de octubre: repetición aprobada

Agregado por Edil: después de la corrección OCI realizada por el usuario se
repitieron las pruebas, sin cambiar código de aplicación, credenciales, modelo
ni políticas IAM desde esta sesión. El bloqueo de permisos del 16 de octubre
no se reprodujo. Los resultados anteriores se conservan abajo como historial.

- **OCI real: 5 aprobadas**: subida/descarga, escritura/lectura JSON en los tres
  buckets y copia verificada que conserva el original. Solo objetos sintéticos
  únicos; estas cinco pruebas limpiaron sus propios objetos.
- **Flutter HTTP real: 2 aprobadas**: recepción/GET y análisis con una solicitud
  Gemini → orquestación → copia OCI → JSON final → GET por el mismo ID.
- El documento analizado terminó `procesado`, prioridad `Rutina`, en `procesados`.
  Una comprobación directa confirmó que el JSON guardado coincide con GET y
  que la copia final tiene los mismos bytes y SHA-256 que el original retenido.
  El JSON previo `recibido` también se conserva.
- No hubo reintentos automáticos ni documentos de pacientes reales. Los dos
  documentos sintéticos HTTP quedan como evidencia; no se hace limpieza global.

**S3-08 y S3-04B quedan técnicamente cerrados para el alcance de Edil**, con
aceptación real de esta muestra sintética y evidencia disponible para revisión
con Drazen. No se inventa su conformidad personal. Urgencia y revisión humana
mantienen cobertura automatizada con respuestas simuladas; esta repetición real
fue un caso de rutina, no una certificación clínica ni de todos los escenarios.
Teléfono físico, cámara e instalable permanecen en Sprint 4.

Evidencia de la repetición:
[edil-revalidacion-17-octubre.json](evidencias/edil-revalidacion-17-octubre.json).
Logs locales:
`C:/Users/leno/AppData/Local/Temp/MediFlow-edil-retest-17oct-5f6a8590755e4614862ed2fd11324c28`.
La suite local anterior de 178 pruebas y analyze sin problemas sigue siendo
válida para el mismo archivo de prueba, cuyo SHA-256 se registra en ambas
evidencias. No se volvió a ejecutar esa suite sin cambios de código.

## Informe original del 16 de octubre

Agregado por Edil: este es el informe vigente de S3-08 y S3-04B. Distingue
implementación, pruebas automatizadas y aceptación con servicios reales.
La referencia de código integrado es `47701cb991c9e720587863f1f1b69120482ea963`.
La comprobación de cierre se prepara en `cierre/edil-sprint-3-2026-10-16`,
sin cambiar `main`, hacer commit ni publicar cambios.

## Entrega S3-08: aplicación Flutter

| Subtarea | Entrega implementada | Verificación |
| --- | --- | --- |
| S3-08.1 Revisar contrato | Reutiliza `TriageResponse`, POST `/api/triage` y GET `/api/documents/{id}` actuales. | Modelos y transporte rechazan respuestas sin identidad o contradictorias. No se inventan endpoints ni campos. |
| S3-08.2 Adaptar modelo | `triage_result.dart` lee estado, ID, tipo, prioridad, destino, justificación, confianza de clasificación y revisión humana. | `triage_result_s3_test.dart` y `triage_confidence_display_test.dart`. |
| S3-08.3 Adaptar servicio | `triage_api_service.dart` envía multipart y consulta el mismo ID. No vuelve a subir para actualizar el estado. | `triage_api_service_test.dart`, `triage_document_service_test.dart` y prueba HTTP real optativa. |
| S3-08.4 Pantalla de éxito | Distingue recepción, análisis completado y auditoría. Un fallo GET conserva el último resultado confirmado. | `triage_result_s3_test.dart` y `triage_document_recovery_test.dart`. |
| S3-08.5 Alerta urgente | Muestra la prioridad provisional devuelta por backend; puede coexistir con auditoría humana. | Casos procesado/auditoría con prioridad Rutina/Urgente; Flutter no aplica reglas clínicas. |
| S3-08.6 Respuestas y errores | Maneja JSON inválido, HTTP, timeout y red; conserva `X-Document-ID`. Si hay ID, ofrece GET; si no hay ID y la recepción es incierta, exige confirmar el riesgo antes de otro POST. | Pruebas de ID distinto/inseguro, cuerpo interrumpido, 408, reenvío y conservación de resultados. |
| S3-08.7 Flujo completo | Selección → consentimiento → envío → resultado/consulta posterior. Se mantienen cámara, navegación y validación de tamaño/formato. | Flujo de pantallas con transporte simulado y comprobación HTTP real descrita más abajo; sus alcances son distintos. |
| S3-08.8 Pruebas | Suite de modelos, servicios, pantallas, cámara simulada, diseño y accesibilidad. | Resultados de la ejecución de cierre registrados abajo. |

Cambiar o quitar el archivo reinicia consentimiento y seguimiento. Una captura
confirmada no se envía sola. Se mantiene el consentimiento Gemini por documento.
La confianza mostrada mide clasificación del tipo documental, no calidad de
extracción ni certeza clínica. No se agregan `score_operativo` o `es_ambiguo`
al JSON público ni se deduce urgencia a partir del porcentaje.

## Entrega S3-04B: apoyo a persistencia OCI

| Subtarea | Resultado | Alcance |
| --- | --- | --- |
| S3-04.5 Escritura y lectura JSON reales | Tres pruebas reales aprobadas el 16 de octubre. | Métodos de S3-04A de Drazen, contrato Pydantic, escritura/lectura exacta y recuperación por ID en `recibidos`, `procesados` y `auditoria_humana`. Solo objetos sintéticos únicos, limpiados al terminar. |
| S3-04.6 Configuración y procedimiento | Guía actualizada y comandos reproducibles. | [guia-verificacion-json-oci.md](guia-verificacion-json-oci.md); `.env` canónico, perfil OCI, tres buckets y pruebas optativas separadas para recepción y análisis. |

La evidencia queda disponible para revisión conjunta con Drazen; no se afirma
que haya participado en esta sesión. Edil valida el uso de la persistencia,
sin atribuirse la implementación original de S3-04A ni la copia de Brando.

## Corrección de la documentación anterior

- La auditoría del 15 de octubre revisó `8ef6e09`; la recuperación GET de Flutter
  todavía no estaba en ese commit. Sí está integrada desde `47701cb`.
- Persistencia JSON, detector y score ya están conectados al backend actual.
  No se mantienen como bloqueos de implementación en la entrega de Edil.
- Los informes del 12 y 15 de octubre se conservan como historial, con avisos
  de cuál es el documento vigente. No se borran aportes de otros participantes.

## Ajuste de la prueba real de Flutter

Antes se hacía la consulta con `http.get` directo dentro del test. Ahora se usa
`TriageApiService.getDocument`, igual que la pantalla, conservando el código
anterior comentado y explicando el cambio con `Agregado por Edil`.

Se agrega una segunda prueba optativa con un TXT completamente ficticio y un
solo POST con `analyze=true`. Necesita un flag adicional; las pruebas habituales
no llaman a Gemini ni OCI. Comprueba respuesta analizada, confianza válida y
el mismo JSON por GET. Ante fallo conserva el código e intenta consultar el ID
reconocido; no repite POST ni convierte una recepción en análisis aprobado.
La evidencia guarda solo metadatos técnicos, sin documentos o respuestas clínicas.

## Resultados de esta ejecución

- `flutter analyze --no-pub`: **sin problemas**, código de salida 0.
- `flutter test --no-pub`: **178 aprobadas y 2 omitidas**, código de salida 0.
  Las omitidas son las dos pruebas HTTP reales, ejecutadas aparte.
- JSON OCI real: **3 aprobadas**, una prueba de archivo fuera de este alcance
  excluida. Tres avisos de dependencias, sin fallos de la prueba.
- Flutter HTTP real: **1 aprobada y 1 fallida**, código de salida 1.
  Recepción sin IA → GET con el mismo servicio de la app aprobó. El análisis
  llegó al paso de copia OCI y devolvió HTTP **503**: no se pudo verificar la copia.
- Recuperación después del fallo real: el servicio Flutter conservó el ID y
  recuperó `recibido` por GET. No hubo reenvío. Una comprobación directa adicional
  confirmó que ambos JSON coinciden con el GET y que los dos originales existen.
- Diagnóstico sin otra llamada a Gemini: al intentar únicamente la copia del
  TXT sintético, OCI devolvió `ServiceError`, HTTP **400**, código
  **`InsufficientServicePermissions`**, envuelto en `ObjectTransferError`.
  No se borró el original ni se modificaron políticas IAM.

Los timestamps de las llamadas son del 17 de octubre a las 03:55 UTC, todavía
16 de octubre a las 23:55 en Bolivia. Solo hubo una solicitud de análisis Gemini
y ninguna repetición de POST para el documento fallido. Que la ejecución alcance
la copia demuestra que la extracción y orquestación anteriores retornaron sin
error en esta muestra; no permite certificar un resultado final persistido ni
su exactitud clínica, porque la API no llegó a devolverlo.

Evidencia local de esta sesión:
`C:/Users/leno/AppData/Local/Temp/MediFlow-cierre-edil-s3-5a31b50e15b04e42857cfe0ffa76e4b5`.
Logs locales adicionales: `MediFlow-cierre-edil-flutter-test-16oct.txt` y
`MediFlow-cierre-edil-flutter-analyze-16oct.txt` en la misma carpeta temporal
del usuario. El segundo está identificado como transcripción de la salida
observada del analizador. Los logs no se incorporan automáticamente a Git.
Resumen técnico sin secretos:
[evidencias/edil-cierre-16-octubre.json](evidencias/edil-cierre-16-octubre.json).

## Veredicto del 16 de octubre — histórico, superado por la repetición del 17

**S3-08: implementación Flutter y verificación local completadas.** La recepción
real, consulta por ID y recuperación de un fallo real están verificadas. La
aceptación de un análisis completo sigue bloqueada por permisos del servicio
OCI, no se marca como aprobada ni se sustituye por un mock.

**S3-04B: comprobación técnica y documentación completadas.** Escritura y lectura
JSON verificadas de nuevo contra los tres buckets con los métodos de Drazen.
La evidencia está lista para su revisión conjunta; no se inventa su conformidad.

Para cerrar la aceptación integral, un administrador OCI debe autorizar al
servicio regional Object Storage a copiar entre los buckets usados por el
pipeline. Tener acceso de usuario para subir y leer no sustituye ese permiso
del servicio. La consola de copia permite revisar qué política falta, según la
[documentación oficial de permisos de copia](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/copyingobjects.htm).
No se pide compartir claves privadas ni cambiar de cuenta. Corregir IAM y
verificar la copia corresponde al responsable OCI/Brando con el administrador;
después se repite la aceptación sintética autorizada. No es necesario agregar
otra regla clínica o un campo nuevo en Flutter para resolver este error.

No se declara cierre total de extremo a extremo mientras esta prueba falle.
Los originales y JSON de estos dos IDs sintéticos permanecen en OCI como
evidencia; las tres pruebas JSON independientes limpiaron sus propios objetos.

La instancia temporal `127.0.0.1:8137` se detuvo al terminar; se verificó el
proceso antes de cerrarlo y no se tocaron otros servidores. Revisión final de
los siete archivos de cierre sin patrones de claves privadas o tokens detectados;
ningún `.env`, `.pem` o `.key` está seguido por Git. `git diff --check` sin errores.
Solo se modifican la prueba Flutter y documentación de Edil; backend, web,
`main`, configuración local, stashes y worktrees anteriores se conservan.

## Límites y siguiente sprint

- Cámara/orientación en teléfono físico, binario instalable y video demo son
  verificaciones de Sprint 4. Una prueba de widgets no acredita hardware real.
- El backend no ofrece reprocesamiento idempotente. Seleccionar otra vez el
  mismo archivo puede generar otro ID; Flutter informa el riesgo, no lo oculta.
- El ID se conserva en memoria mientras la pantalla sigue abierta. No se
  incorpora un historial clínico local ni una recuperación entre sesiones.
- Criterios por tipo, calibración clínica y decisiones de negocio pertenecen a
  Nicolás, Laura y Eliana. La app presenta el contrato recibido sin sustituirlos.
- La aprobación humana persistida depende de la API y del panel web de Sprint 4;
  no se simula como una funcionalidad terminada de Flutter.
- No se certifica exactitud clínica ni disponibilidad permanente del proveedor.
  No se cambia modelo, clave ni configuración local para hacer pasar la prueba.
