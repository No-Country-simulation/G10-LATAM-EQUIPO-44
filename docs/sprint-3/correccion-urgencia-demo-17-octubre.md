# S3-01.4 — corrección y validación de urgencia de la demo sintética

Agregado por Edil, 17 de octubre de 2026. Se conserva la ejecución fallida
anterior y sus etiquetas; esta es una corrección posterior, no un reemplazo de
evidencias. El usuario aprobó expresamente un perfil separado para la demo
sintética, sin activar reglas clínicas experimentales en el flujo general.

## Resultado actual

**Perfil `synthetic_demo_v1`: 9/9 casos coinciden con el dataset**, incluidos
5/5 normales y 4/4 urgentes. HTTP 201, resultado JSON final y GET 200 iguales
en los nueve casos. Los cinco normales conservan prioridad y destino esperados.

**Modo `general`: se conserva el comportamiento previo.** No se proclama que
el módulo clínico general esté validado ni que los cuatro criterios de demo
sean reglas asistenciales. El perfil es una configuración explícita del servidor;
no se selecciona por archivo, ID, etiqueta URG/NOR ni instrucciones del documento.
No se cambió `mediflow/.env`; se configuró solo la instancia temporal de prueba.

## Causa raíz e inspección de la salida extraída

Se recuperaron en memoria los cuatro JSON reales anteriores desde OCI. Solo se
registró presencia de campos y coincidencias: no nombres de pacientes, contenido
clínico completo, justificaciones, claves ni mensajes crudos del proveedor.

| Caso | Extracción anterior | Detector general aislado antes | Causa específica |
| --- | --- | --- | --- |
| MF_004 | Examen presente; diagnóstico ausente. Texto TXT disponible. | Sin coincidencias; `routine`. | El catálogo activo no ejecutaba la condición numérica experimental ya definida para este dataset. |
| MF_008 | Diagnóstico resumido de 41 caracteres; detalles de imagen perdidos. | Solo campos estructurados, sin coincidencias. | El resumen no conservaba sitio/contornos suficientes para comprobar la condición radiológica del dataset. No había texto de imagen disponible para el detector. |
| MF_009 | Diagnóstico presente y texto PDF disponible. | Sin coincidencias; `routine`. | La expresión del documento incluye palabras intermedias que no coinciden con el término literal del catálogo. |
| MF_011 | Diagnóstico presente y texto PDF disponible. | Sin coincidencias; `routine`. | La separación y redacción de pie diabético/úlcera/Wagner no coincidían con la frase literal. |

El detector **sí estaba conectado**: `triage_pipeline` llama al servicio del
orquestador, que invoca `evaluate_analysis` y `detect_urgency`. No era una llamada
omitida ni una prioridad urgente borrada: no se había generado ninguna señal.

`triage_rules_v1.json` ya contenía las cuatro condiciones experimentales, pero
su existencia no implicaba ejecución. El prompt general tampoco las adjuntaba,
deliberadamente, porque no son criterios clínicos generales. Además, el catálogo
general asocia coincidencias a revisión humana; el dataset espera derivación
directa para estos casos completos. No se anuló esa revisión para forzar resultados.

## Corrección aplicada

### 1. Perfil explícito y reglas existentes

`data_ai/synthetic_demo_rules.py` interpreta únicamente los cuatro IDs URG
existentes en la política `1.2-dataset-sintetico`. Valida compatibilidad de esa
política y reconoce variantes de redacción sobre el texto, no etiquetas de casos.

- La condición de glucemia se limita al valor exacto del dataset, con sus
  unidades y contexto; no se creó un umbral `>=250` ni otro criterio clínico.
- La condición radiológica exige las evidencias descriptivas y de sospecha;
  no eleva cualquier mención aislada de neoplasia ni inventa un diagnóstico.
- Las condiciones de lesión por presión y Wagner admiten las palabras
  intermedias de los documentos sin ampliar los estadios/grados definidos.
- Se comprueban negación e historia local; una negación sobre otro hallazgo
  no elimina toda la evidencia positiva del documento.

El evaluador devuelve solo IDs de reglas y señal de prioridad. **No devuelve
`requiere_auditoria_humana=false` ni puede cancelar una revisión.** El catálogo
general de Nicolás, el umbral y la fórmula de Laura permanecen intactos.

### 2. Evidencia de imagen sin ampliar el contrato público

En el perfil de demo, el cliente Gemini obtiene el análisis y una transcripción
literal interna de JPG/PNG/PDF sin texto en **la misma generación**, con un
envoltorio de esquema interno. TXT/PDF con texto reutilizan la extracción local.

La transcripción se valida y se pasa separada al orquestador. No se fabrica
serializando el JSON ni se infiere del nombre del archivo. No se agrega al API,
al JSON persistido ni a logs. Si falta o es inválida, se devuelve un error
controlado; no se inventa texto para que una regla coincida.

Es transcripción de Gemini, **no OCR independiente ni evidencia infalible**.
La salida estructurada pública y las rutas HTTP siguen siendo las existentes.
El modo general conserva el método anterior sin solicitar esa transcripción.

### 3. Prioridad y revisión independientes

El orquestador combina la nueva señal de demo mediante OR con la urgencia
previa. Conserva por separado revisión previa, baja confianza, dosis `ILLEGIBLE`
y alertas del detector general. Si cualquiera exige auditoría, el resultado
permanece urgente y va a revisión; no se fuerza la cola de emergencia sobre ella.
No se usa el score de clasificación como certeza clínica ni como regla de urgencia.

## Pruebas ejecutadas

- **300 pruebas locales aprobadas y 21 subcasos**, cinco pruebas OCI reales
  omitidas en esa suite. Dos avisos de deprecación, sin fallos.
- Las 39 pruebas nuevas cubren las cuatro condiciones, su paso por el
  orquestador, el modo general sin cambios, negaciones, antecedentes, valores/
  unidades distintos, palabras incompletas, dosis ilegible, revisión previa,
  baja confianza, alertas clínicas y evidencia multimodal separada del contrato.
- **Nueve casos reales de extremo a extremo aprobados**, sin mocks: Gemini,
  reglas, OCI, JSON y GET. Una solicitud de análisis por caso, sin reintentos
  automáticos. No se modificaron claves, modelo o políticas IAM.

| Caso | Formato | Antes | Después, perfil demo | Destino final |
| --- | --- | --- | --- | --- |
| MF_001 | PDF | Rutina, tras corregir transporte PDF | Rutina | Cola_Farmacia |
| MF_004 | TXT | Rutina | Urgente | Cola_Emergencia_Medica |
| MF_005 | JPG | Rutina | Rutina | Cola_Historia_Clinica |
| MF_006 | PDF | Rutina | Rutina | Cola_Historia_Clinica |
| MF_007 | TXT | Rutina | Rutina | Cola_Historia_Clinica |
| MF_008 | JPG | Rutina | Urgente | Cola_Emergencia_Medica |
| MF_009 | PDF | Rutina | Urgente | Cola_Emergencia_Medica |
| MF_011 | PDF | Rutina | Urgente | Cola_Emergencia_Medica |
| MF_012 | PDF | Rutina | Rutina | Cola_Historia_Clinica |

En estas nueve muestras completas, estado `procesado` y revisión humana `false`,
según el CSV sin modificar. Las protecciones que fuerzan auditoría se verifican
con las regresiones locales; no se afirma que se haya probado hardware Flutter.

La instancia real utilizó instrumentación temporal que ejecuta el evaluador
aislado y **reenvía siempre al servicio real**, sin reemplazar su respuesta.
La traza registra la entrada estructural, reglas coincidentes, ambigüedad y
prioridades antes/después, sin texto clínico. Permite distinguir extracción,
coincidencia de reglas, confianza y enrutamiento.

## Configuración reproducible

En una terminal exclusiva de demo, con servicios y cuota autorizados:

```powershell
Set-Location 'D:\Nocountru\mediflow\backend'
$env:TRIAGE_RULES_PROFILE = 'synthetic_demo_v1'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8143 --no-access-log
```

En otra terminal:

```powershell
Set-Location 'D:\Nocountru\mediflow\backend'
$env:TRIAGE_RULES_PROFILE = 'synthetic_demo_v1'
$nicoReport = Join-Path $env:TEMP ('MediFlow-nico-corregido-' + [guid]::NewGuid().ToString('N') + '.json')
& .\.venv\Scripts\python.exe ..\data_ai\validate_dataset_pipeline.py --allow-cloud --confirm-synthetic --base-url http://127.0.0.1:8143 --report $nicoReport
```

El perfil declarado por el runner es metadato del operador, no una selección
enviada por HTTP. Configurar también el servidor. Para volver al modo general,
detener la instancia y usar `TRIAGE_RULES_PROFILE=general` o quitar esa variable.
`.env.example` conserva `general` como predeterminado; no se activa demo en `.env`.

## Evidencias, archivos y límites

- [Inspección anterior y detector aislado](evidencias/nico-correccion-diagnostico-antes-17-octubre.json).
- [Ejecución real de los nueve casos corregidos](evidencias/nico-s3-01-4-corregido-demo-17-octubre.json).
- [Traza por etapa y verificación directa de persistencia/copias](evidencias/nico-traza-persistencia-corregida-17-octubre.json).

Archivos funcionales: `backend/app/services/gemini_client.py`,
`backend/app/services/triage_pipeline.py`, `backend/app/core/orquestador.py`,
`data_ai/synthetic_demo_rules.py` y configuración de ejemplo. Pruebas nuevas:
`backend/tests/test_document_source_evidence.py` y
`backend/tests/test_synthetic_demo_urgency.py`. El runner únicamente añade
perfil declarado y hashes de los módulos nuevos a su evidencia.

No se modifica la fórmula, el catálogo general, las etiquetas del dataset,
contrato, Flutter o web. Las reglas de demo no están validadas clínicamente;
falta esa validación antes de cualquier uso general. Una muestra favorable
no demuestra sensibilidad, seguridad clínica ni inmunidad a errores de
transcripción, contexto o instrucciones maliciosas dentro del documento.
Se conservan los objetos sintéticos para trazabilidad, sin borrar otros objetos.
No se hace commit ni push ni se cambia `main`.
