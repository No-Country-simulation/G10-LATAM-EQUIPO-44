# Cierre de integración — Eliana S3-05

17 de octubre de 2026. Resultado: **cierre técnico aprobado en el alcance
de orquestación e integración solicitado**, con tres escenarios integrales reales.
No se cambió código funcional ni se reimplementaron entregas del equipo.

## Resultado por escenario

Perfil explícito del servidor y runner de nube: `synthetic_demo_v1`.

| Escenario | Muestra | Prioridad final | Estado | Destino | Revisión | Bucket final | Resultado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| NORMAL | MF_001 del dataset sintético existente | Rutina | procesado | Cola_Farmacia | false | procesados | Aprobado |
| URGENTE | MF_004 del dataset sintético existente | Urgente | procesado | Cola_Emergencia_Medica | false | procesados | Aprobado |
| AMBIGUO/AUDITORÍA | TXT fijo de software, incompleto y sin información clínica ni identificadores personales | Rutina | auditoria_humana | Cola_Revision_Humana | true | auditoria_humana | Aprobado |

Los tres POST analyze=true devolvieron **201**, sus GET por ID **200** y el
JSON recuperado fue igual al final. El listado devolvió 200 y una única versión
actual de cada ID. Las lecturas directas OCI confirmaron igualdad de los JSON.
La auditoría es un estado y una decisión de revisión; no se convierte en una
tercera prioridad clínica. Un documento urgente que requiera revisión conserva
Urgente y va a Cola_Revision_Humana; esa combinación se comprobó localmente.

IDs de las ejecuciones, sin datos clínicos en el informe:

- NORMAL: `DOC-CLIN-E42C5744B2EF4940B0C38FAA081C0C7A`.
- URGENTE: `DOC-CLIN-2E83BF2620084588B202336E5120659C`.
- AUDITORÍA: `DOC-CLIN-33ADF7A430DF45B4BD7527D256038804`.

## Orden efectivo y conservación de señales

Se revisaron exclusivamente orquestador, servicio de orquestación, pipeline,
configuración y sus fronteras ya existentes de clasificación, persistencia y API.
La secuencia observada, una vez por documento en la traza real, fue:

```text
original recibido y JSON inicial persistido
→ clasificación/extracción Gemini validada
→ evaluación de confianza
→ detección de urgencia
→ combinación de señales y decisión final
→ copia OCI verificada
→ JSON final persistido
→ recuperación GET y lectura directa OCI
```

La confianza se calcula antes de la detección de urgencia en la implementación
actual. Es correcto para este diseño: ambas funciones leen la extracción y se
calculan antes de decidir el destino. La confianza no consume ni sobrescribe
la señal de urgencia, y no hay una salida anticipada por ambigüedad que omita
el detector. Cambiar ese orden no era necesario.

La prioridad final combina por OR la urgencia previa de clasificación y la del
detector. Por separado, revisión previa OR confianza insuficiente OR alerta del
detector decide auditoría. La prioridad y la auditoría son dimensiones distintas.
El caso real MF_004 lo demuestra: clasificación Rutina, confianza sin bloqueo,
detector con señal urgente y resultado Urgente; copia, persistencia y GET
conservaron Urgente. El caso ambiguo conservó su revisión previa y el bloqueo
por confianza hasta el destino y persistencia finales.

La evaluación de confianza mantiene el motor, fórmula y umbral **0.70**.
Los perfiles provisionales de Laura siguen activos en general, con revisión
conservadora para esenciales que el contrato no representa. En demo se conserva
la compatibilidad ya documentada de Laura; no se declara clínicamente completa
una extracción solo por superar el umbral.

## Protecciones verificadas

- Baja confianza y dosis exactamente ILLEGIBLE conservan revisión humana.
- Se conserva revisión previa por bandera, estado o destino de revisión.
- Ninguna de esas protecciones rebaja una prioridad Urgente.
- Una contradicción de extracción (cola de revisión sin bandera, o dosis
  ILLEGIBLE sin revisión) se rechaza con 502 antes de orquestar/copiar; queda
  recuperable el registro recibido. No se acepta silenciosamente.
- Urgencia no equivale por sí sola a baja confianza. Si exige revisión,
  su prioridad urgente se conserva y el destino es la cola de revisión.
- El perfil general no llama a la función exclusiva de demo. Una prueba con
  centinela que falla si se invoca esa función lo confirma incluso ante la
  frase específica del dataset.
- La fuente textual se pasa internamente; no se fabrica serializando el JSON
  ni se añade al contrato. No hubo nuevas clasificaciones o copias duplicadas.

## Contrato público y persistencia

El servicio valida TriageResponse antes y después de orquestar, y valida la
salida de análisis antes de transferirla. El ID permanece invariable.
La decisión mantiene sus tres claves públicas; prioridad pertenece a
clasificacion y estado al nivel superior. No se agregaron campos operativos,
estados internos de criterios, trazas, hashes, texto de fuente ni campos de
envoltorio multimodal al JSON público.

Se verificó la igualdad completa POST → GET por ID → JSON final directo OCI,
incluyendo ID, prioridad, estado, destino, revisión y almacenamiento. El listado
deduplicó las recepciones antiguas y conservó la versión final.
Los originales y JSON iniciales siguen en recibidos; las copias y JSON finales
están en procesados o auditoria_humana. SHA-256 y tamaño coinciden entre cada
archivo enviado, original y copia. Los ETags se registran como identificadores
de versiones; no se exige que el destino tenga el mismo ETag que el origen.

## Qué fue real

Esta intervención ejecutó **tres análisis nuevos completos**, sin mocks:
HTTP local → Gemini → validación → reglas de confianza/urgencia → orquestación
→ CopyObject OCI → JSON → GET. Se usó el backend existente en una instancia
temporal del puerto 8145, con configuración local y perfil de demo exportado;
no se modificó .env ni se cambiaron claves, modelo o permisos.

Para observar el orden se envolvieron temporalmente, solo en memoria del
servidor de prueba, los métodos existentes. Cada envoltorio reenvió siempre
al método original y devolvió su resultado sin sustituirlo ni modificarlo.
La traza guarda únicamente ID, etapas, decisiones y señales booleanas;
no nombres, texto clínico, claves ni mensajes crudos de proveedor.
La instancia temporal se detuvo al concluir.

Los dos casos del dataset habían sido autorizados y validados anteriormente;
la tercera muestra es un TXT de software deliberadamente incompleto. La
entrada estructurada de estos tres casos fue generada realmente por Gemini:
no es la fixture estructurada local usada en el cierre previo de Drazen/Brando.
Se hicieron tres solicitudes POST, sin reintentos automáticos del runner.
No se volvió a ejecutar aquí el dataset completo 9/9; sus informes anteriores
se conservan y los dos casos seleccionados no sustituyen esa evidencia.

Se mantienen doce objetos sintéticos nuevos para trazabilidad: original y JSON
recibidos, copia y JSON final, cuatro por caso. No se borraron objetos ni
aparecieron fallos de permisos en estas ejecuciones.

## Pruebas locales y fallos

Resultado conjunto: **267 pruebas y 21 subcasos aprobados, cero fallos finales**.
Dos avisos de deprecación de dependencias (Starlette/httpx y google-genai),
sin fallo funcional. Son 249 pruebas existentes y 18 nuevas.

Las 18 pruebas nuevas cubren el orden desde recepción hasta persistencia/GET,
los tres escenarios, urgencia con baja confianza/dosis ilegible/revisión previa,
marcadores previos de estado/destino, invariancia del contrato, una generación
por solicitud, aislamiento de demo y rechazo temprano de contradicciones.
En la suite local se simulan transportes OCI/Gemini; se ejecutan los módulos
reales de validación, confianza, urgencia, orquestación y API.

La primera versión de las nuevas fixtures produjo cuatro fallos de expectativa:
se esperaba 201 de salidas de IA contradictorias, pero el validador existente
devolvió correctamente 502. Se corrigieron las fixtures positivas y se conservaron
esas cuatro combinaciones como pruebas negativas explícitas. Pasaron; no se
identificó un error funcional que justificara modificar el pipeline.

Comando final desde D:\Nocountru\mediflow\backend:

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/test_eliana_integration.py tests/test_orquestador_integration.py tests/test_triage_pipeline.py tests/test_s3_complete_pipeline.py tests/test_s3_integration_regressions.py tests/test_document_source_evidence.py tests/test_synthetic_demo_urgency.py tests/test_confidence_profiles.py tests/test_documents_api.py tests/test_triage_api.py tests/test_oci_client.py tests/test_oci_transfer.py tests/test_oci_error_handler.py tests/test_sprint3_oci_verifier.py ..\data_ai\test_score_confianza.py ..\data_ai\test\test_mvp_threshold_integration.py ..\data_ai\test\test_urgency_detector.py ..\data_ai\test\test_urgency_json_adapter.py ..\data_ai\test\test_urgency_scenarios.py -q -p no:cacheprovider
```

## Configuración de general y demo

`TRIAGE_RULES_PROFILE` admite únicamente general y synthetic_demo_v1; sin
variable exportada ni configuración explícita de demo el selector devuelve
general. Un valor desconocido falla de forma controlada. El perfil se fija en
el servidor; el ID, nombre o contenido del documento no pueden seleccionarlo.

Para reproducir la demostración, en una terminal exclusiva de backend:

```powershell
$env:TRIAGE_RULES_PROFILE = 'synthetic_demo_v1'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8145 --no-access-log
```

Con servicios y envío de muestras sintéticas autorizados, el runner existente
permite seleccionar MF_001 y MF_004 mediante --case, --allow-cloud y
--confirm-synthetic. Su perfil declarado debe coincidir con el del servidor.
El caso incompleto adicional se envía con analyze=true por la ruta existente.
No activar la excepción de demo para documentos reales. Las reglas de demo
son condiciones del dataset y **no están clínicamente validadas**.

## Cambios locales acumulados

Se trabajó en `cierre/edil-sprint-3-2026-10-16`; no se cambió de rama ni se
modificó main. HEAD, referencia main e índice Git se mantuvieron iguales.
No hay entradas sin resolver de Git; git diff --check pasó para los cambios
acumulados. La revisión AST de los módulos delimitados no encontró definiciones
de nivel superior duplicadas que sobrescribieran funciones/clases.

No se encontró una segunda ejecución activa del pipeline ni una regresión
reproducible en este alcance. La evaluación de compatibilidad de confianza
conservada para demo es una decisión previa de Laura, no otra orquestación.
Se compararon huellas antes/después de los 19 archivos de runtime/configuración
del alcance: todos permanecen idénticos. Flutter y web no se editaron ni se
volvieron a probar aquí; sus resultados previos no se presentan como nuevos.
Esta revisión delimitada no afirma que cada archivo del repositorio haya sido
auditado ni que se haya hecho una fusión de ramas.

## Archivos añadidos en este cierre

1. mediflow/backend/tests/test_eliana_integration.py — 18 pruebas nuevas.
2. docs/sprint-3/cierre-integracion-eliana.md — este informe.
3. docs/sprint-3/evidencias/eliana-s3-integracion-real.json — tres resultados e integridad OCI/GET.
4. docs/sprint-3/evidencias/eliana-s3-traza-real.json — orden y decisiones por etapa.
5. docs/sprint-3/evidencias/eliana-s3-verificacion.json — huellas, rama, main, índice y comprobaciones.
6. docs/sprint-3/evidencias/eliana-s3-pruebas-locales.txt — salida de pytest.

No hubo correcciones de código funcional, commits, push ni merge. Se
conservaron los cambios previos preparados, sin preparar y sin seguimiento.

## Lista definitiva de pendientes

**S3-05 técnico:** no quedan bloqueos reproducidos en los tres escenarios ni
permisos externos pendientes observados para esta configuración.

Para el cierre funcional y documental del Sprint 3 por el equipo:

- Ratificar los mínimos provisionales de Laura, los requisitos que el contrato
  no puede verificar y la excepción exclusiva de compatibilidad sintética.
  No confundir esta ratificación con un nuevo campo de API ni con cambiar 0.70.
- Mantener explícita la limitación del dataset: no demuestra validez clínica,
  calibración general, fidelidad de transcripción ni seguridad asistencial.
- Revisar y aprobar el paquete acumulado de cambios y evidencias antes de
  cualquier publicación o integración de Git. No se ejecutó esa acción.

Fuera del cierre técnico probado: aprobación/rechazo persistente de Sprint 4,
despliegue productivo, carga, autenticación multiusuario y recuperación automática
de fallos parciales. La copia y el JSON no forman una transacción atómica.
No se necesita reimplementar los GET ni los módulos del equipo para este cierre.

## Evidencias

- [Integración real](evidencias/eliana-s3-integracion-real.json).
- [Traza de orden y señales](evidencias/eliana-s3-traza-real.json).
- [Verificación técnica y fuentes conservadas](evidencias/eliana-s3-verificacion.json).
- [Salida de pruebas locales](evidencias/eliana-s3-pruebas-locales.txt).
