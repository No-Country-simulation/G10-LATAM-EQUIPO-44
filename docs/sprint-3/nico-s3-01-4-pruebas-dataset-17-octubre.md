# S3-01.4 — Nicolás — pruebas reales del dataset

> Agregado por Edil: la corrección posterior del mismo día aprobó **9/9 casos**
> en un perfil explícito de demo sintética, manteniendo el modo general sin
> cambios. Ver [corrección, trazas y límites](correccion-urgencia-demo-17-octubre.md).
> Los resultados 0/4 urgentes de este documento se conservan como evidencia
> de la ejecución anterior, no como el resultado vigente del perfil de demo.

Agregado por Edil, 17 de octubre de 2026: ejecución y registro de la tarea de
pruebas normales/urgentes. No se atribuye a Edil la implementación original
del detector ni se modifican sus reglas para aprobar esta evaluación.

## Resultado y alcance

**Ejecución y registro de S3-01.4 completados. Conformidad de urgencia no aprobada.**

- Nueve documentos NOR/URG: cinco PDF, dos JPG y dos TXT, incluidos todos los
  formatos normales/urgentes disponibles para la demo. El usuario confirmó
  expresamente que los nueve son sintéticos y autorizó enviarlos a Gemini.
- Pipeline real: HTTP POST `/api/triage` con `analyze=true`, Gemini, orquestador,
  detector/score activos, copia OCI, persistencia JSON y GET por el mismo ID.
- Tras corregir el transporte del PDF MF_001: **9/9 completaron técnicamente**
  y el JSON recuperado coincidió con el devuelto por POST.
- **5/5 normales coincidieron** en prioridad, destino, revisión y estado.
- **0/4 urgentes coincidieron**: el CSV exige `Urgente` y `Cola_Emergencia_Medica`,
  pero los cuatro devolvieron `Rutina` y `Cola_Historia_Clinica`, sin revisión.
- No se cambiaron etiquetas del CSV, prompt, contrato, umbral, detector ni reglas.
  No se usaron mocks o respuestas prefabricadas para estos resultados reales.

Esto satisface la ejecución y el registro solicitados; **no permite declarar
terminada con éxito la detección urgente del módulo**. Son discrepancias con
las etiquetas experimentales del dataset, no diagnósticos ni métricas clínicas
validadas. El buen resultado técnico de Flutter/OCI no acredita calidad de IA.

## Resultados por documento

En las nueve respuestas finales: HTTP 201, estado `procesado`, revisión humana
`false`, backup `exito` y GET 200 con el mismo JSON. Esos valores técnicos no
compensan una prioridad o un destino incorrectos respecto del caso esperado.

| Caso | Formato | Escenario | Prioridad/destino esperados | Prioridad/destino observados | Coincide |
| --- | --- | --- | --- | --- | --- |
| MF_001 | PDF | Normal | Rutina / Farmacia | Rutina / Farmacia | Sí, tras corregir transporte PDF |
| MF_004 | TXT | Urgente | Urgente / Emergencia médica | Rutina / Historia clínica | No |
| MF_005 | JPG | Normal | Rutina / Historia clínica | Rutina / Historia clínica | Sí |
| MF_006 | PDF | Normal | Rutina / Historia clínica | Rutina / Historia clínica | Sí |
| MF_007 | TXT | Normal | Rutina / Historia clínica | Rutina / Historia clínica | Sí |
| MF_008 | JPG | Urgente | Urgente / Emergencia médica | Rutina / Historia clínica | No |
| MF_009 | PDF | Urgente | Urgente / Emergencia médica | Rutina / Historia clínica | No |
| MF_011 | PDF | Urgente | Urgente / Emergencia médica | Rutina / Historia clínica | No |
| MF_012 | PDF | Normal | Rutina / Historia clínica | Rutina / Historia clínica | Sí |

Los nombres oficiales de las colas, IDs OCI, hashes de entrada, latencias y
comparaciones individuales están en las evidencias JSON, sin texto extraído,
nombres de pacientes, diagnósticos, claves ni respuestas clínicas completas.

## Hallazgos para Nicolás y Eliana

1. **MF_004:** el criterio numérico experimental del dataset no está conectado
   como regla operativa del catálogo activo. El detector devolvió cero
   coincidencias aun con texto fuente extraído del TXT.
2. **MF_008:** Gemini procesó la imagen nativa, pero el detector posterior solo
   recibió campos estructurados de diagnóstico/CIE-10, no texto OCR completo.
   El diagnóstico estaba presente; no coincidió con términos del catálogo.
   No se puede afirmar cobertura del texto completo de imágenes.
3. **MF_009 y MF_011:** el texto de los PDF sí llegó al detector. Los términos
   literales del catálogo no reconocieron las redacciones de estas muestras;
   cero coincidencias, prioridad documental `routine` y sin recomendación de
   revisión. La existencia de una frase parecida en una regla no demuestra
   cobertura de variantes, palabras intermedias o contexto del documento.
4. El prompt activo no adjunta automáticamente reglas experimentales a todos
   los documentos. La mera existencia de `triage_rules_v1.json` no significa
   que sus reglas se ejecuten. Acordar con Nicolás/Eliana cómo se aplica el
   contexto experimental de demo sin convertirlo en criterio clínico general.
5. Los cuatro urgentes devolvieron confianza de clasificación 1.0. Ese valor
   mide el tipo documental; **no demuestra que la prioridad esté bien asignada**.
   Cambiar el umbral de Laura no resuelve por sí solo estas cuatro discrepancias.

El diagnóstico se obtuvo consultando únicamente los cuatro IDs de prueba y
ejecutando el detector local con la misma cobertura de entrada del pipeline.
No consumió nuevas llamadas Gemini ni modificó los documentos.

Acción pendiente: acordar/corregir cobertura y política de enrutamiento con
Nicolás y Eliana, añadir regresiones para las cuatro discrepancias y repetir
solo los casos afectados. No elevar prioridades por nombre de archivo, ID,
fecha supuesta ni etiquetas incluidas a escondidas en el documento.

## MF_001: corrección de transporte, sin alterar su contenido documental

El primer intento terminó HTTP 422 antes de generar el análisis: el PDF local
tenía CRLF y referencias `xref` desfasadas. Se comprobó que:

- `core.autocrlf=true`; el blob original de Git usa LF y es válido con el mismo
  lector estricto. El contenido local solo difería por conversión LF → CRLF.
- Se respaldó y verificó la copia local por SHA-256 antes de tocarla.
- Se recuperaron exactamente los bytes del blob de `HEAD`; no se reconstruyó
  el documento, no se flexibilizó el lector PDF y no se cambió contenido médico.
- Se agregó `*.pdf -text` en `.gitattributes`, con explicación Agregado por Edil,
  para impedir que Git convierta saltos de línea de PDF en Windows.
- Se repitió manualmente **solo MF_001**, que completó el pipeline y coincidió.
  La evidencia fallida se conserva; no se oculta dentro del resultado final.

Hubo diez intentos POST en total: nueve iniciales y una repetición dirigida del
PDF corregido. No hubo reintentos automáticos ni reenvío de los otros ocho.
Los objetos sintéticos y JSON se conservan en OCI para trazabilidad; no se
realizaron borrados de objetos del equipo.

## Reproducción

Inventario local, sin servicios externos:

```powershell
Set-Location 'D:\Nocountru\mediflow\backend'
& .\.venv\Scripts\python.exe ..\data_ai\validate_dataset_pipeline.py --check-only
```

Iniciar en otra terminal una instancia de prueba aislada:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8141 --no-access-log --log-level warning
```

Solo con documentos sintéticos confirmados y autorización de uso/cuota:

```powershell
$nicoReport = Join-Path $env:TEMP ('MediFlow-nico-dataset-' + [guid]::NewGuid().ToString('N') + '.json')
& .\.venv\Scripts\python.exe ..\data_ai\validate_dataset_pipeline.py --allow-cloud --confirm-synthetic --base-url http://127.0.0.1:8141 --report $nicoReport
```

Para repetir un único caso corregido, agregar `--case MF_001` o el ID acordado
y usar otro archivo de evidencia. El script no sobrescribe informes existentes.
Código 0 significa que todos los casos ejecutados coinciden; código 1 informa
discrepancias/fallos. Sin ambos flags se desactiva la ejecución externa.

## Evidencias y pruebas locales

Backend y data_ai, después del evaluador y su selección por caso:
**261 pruebas aprobadas y 21 subcasos**, cinco pruebas OCI optativas excluidas.
Dos avisos de deprecación de dependencias, sin errores de la suite local.
Las nueve pruebas nuevas del evaluador comprueban inventario, flags optativos,
selección individual y rechazo de resultados/almacenamientos inconsistentes.

- [Primera ejecución completa](evidencias/nico-s3-01-4-dataset-17-octubre.json).
- [Transporte PDF y respaldo de MF_001](evidencias/nico-mf001-pdf-transporte-17-octubre.json).
- [Repetición de MF_001](evidencias/nico-mf001-repeticion-17-octubre.json).
- [Diagnóstico de los cuatro urgentes](evidencias/nico-diagnostico-dataset-urgente-17-octubre.json).
- [Consolidado final sin ocultar intentos previos](evidencias/nico-s3-01-4-consolidado-17-octubre.json).

Se conserva el código ajeno. Los cambios de implementación se limitan al
evaluador optativo, sus pruebas y la protección de formato PDF; no se modifican
backend, frontend web, Flutter, prompt, detector, contrato o datos esperados.
Los cambios previos de cierre de Edil también se conservan, sin mezclarlos con
un commit automático. No se hace commit ni push ni se mueve `main`.
