# S3-02.1 — diagnóstico y propuesta de criterios por tipo documental

> **Actualización S3-02.1 / S3-02.4, 17-10-2026:** las secciones 1–7 se
> conservan como diagnóstico histórico. La sección 8 documenta la política
> provisional del MVP implementada por encargo del usuario; prevalece sobre
> las referencias anteriores a reglas todavía no activadas.

Agregado por Edil, 17 de octubre de 2026. **BORRADOR PARA VALIDACIÓN DEL EQUIPO.**
Esta propuesta no activa reglas, no cambia la fórmula, no agrega campos al
contrato y no establece requisitos clínicos o legales. Obligatorio y crítico
se usan aquí como categorías candidatas de la política funcional del MVP.

## 1. Implementación vigente

Fuentes: `data_ai/score_confianza.py`, `backend/app/core/orquestador.py`,
`backend/app/models/schemas.py`, `data_ai/prompts/master_prompt.txt` y sus pruebas.

La fórmula existente es:

```text
completitud = criterios cumplidos / criterios evaluados
score_operativo = 0 si alerta_critica; en otro caso min(score_clasificacion, completitud)
ambiguo = alerta_critica o score_operativo < UMBRAL_CONFIANZA_MVP
UMBRAL_CONFIANZA_MVP = 0.70
```

`0.70` exacto no es ambiguo por umbral. No es una probabilidad de acierto clínico;
necesita calibración cuando cambien los criterios y su denominador. No se propone
otro umbral ni ponderaciones. El evaluador actual rechaza una lista vacía.

Los cuatro criterios usados por todos los documentos son:

1. Tipo considerado conocido por una lista de exclusión.
2. `datos_extraidos.paciente.nombre` no vacío.
3. `datos_extraidos.medico_solicitante.nombre` no vacío.
4. `diagnostico_principal` O `estudio_realizado` no vacío.

La única alerta objetiva actualmente conectada a la fórmula es alguna dosis
exactamente `ILLEGIBLE`. Una dosis `null` no es lo mismo y no dispara esa alerta.
Las señales del detector de urgencia se calculan por separado y el orquestador
combina las decisiones; no bajan por sí mismas el score a cero.
No se usa `requiere_auditoria_humana` como entrada circular del score.

El score operativo y `es_ambiguo` son internos. La API y Flutter siguen usando
`score_confianza_clasificacion`, que se refiere al tipo documental.

### Hallazgos reproducidos localmente, sin nube

Con confianza de clasificación `0.95` y datos ficticios:

| Entrada | Completitud | Score operativo | Revisión por confianza |
| --- | --- | --- | --- |
| Receta sin medicamentos ni diagnóstico/estudio, pero con paciente y profesional | 0.75 | 0.75 | No |
| Tipo arbitrario fuera del catálogo, con los otros datos completos | 1.00 | 0.95 | No |
| Informe con paciente ausente, profesional y estudio presentes | 0.75 | 0.75 | No |
| Certificado con paciente/profesional, sin diagnóstico/estudio | 0.75 | 0.75 | No; penaliza una ausencia que puede ser legítima |
| Tipo explícito `Desconocido`, con los otros tres criterios completos | 0.75 | 0.75 | Sí, por la protección adicional del orquestador |

El problema del tipo arbitrario es que `_known_document_type` excluye unos
sentinelas, pero no comprueba pertenencia a un catálogo. Las pruebas actuales
cubren esos sentinelas; no cubren toda etiqueta ajena al dominio.

La proporción tampoco impide por sí sola que falte un dato esencial: tres
criterios de cuatro dan `0.75`, por encima del umbral existente. Hay que acordar
qué ausencias deben bloquear la aceptación, sin cambiar la fórmula.

## 2. Tipos realmente indicados al clasificador

El prompt enumera seis tipos:

- Receta Médica.
- Informe de Laboratorio.
- Informe de Estudio por Imágenes.
- Orden / Solicitud de Procedimiento.
- Epicrisis / Informe de Alta.
- Certificado Médico.

`Informe médico` genérico no es un séptimo tipo declarado. No se creará un
perfil para esa etiqueta sin acuerdo. Pydantic y el JSON Schema aceptan hoy
`tipo_documento: str`, sin enum; el prompt no garantiza pertenencia al catálogo.
El archivo `backend/app/core/contrato.json` es un ejemplo de respuesta, no una
declaración de campos condicionales por tipo.

Propuesta técnica: catálogo configurable de nombres canónicos y aliases
explícitos (incluidos los usados por el dataset), normalizando tildes, mayúsculas
y espacios. No inferir el tipo por nombre de archivo ni aceptar cualquier cadena.
Tipos no registrados o ambiguos no deben recibir automáticamente un perfil
confiable ni permitir aceptación por un score alto.

## 3. Matriz candidata: no aprobada ni activa

En todos los perfiles se propone comprobar tipo registrado y paciente identificado.
La obligatoriedad del paciente y del profesional es una decisión funcional a
validar por el equipo, no una exigencia añadida a Pydantic. La semántica de
`medico_solicitante` debe revisarse: no distingue emisor, firmante y solicitante.

| Tipo | Candidatos obligatorios comprobables en JSON | Opcionales o condicionales | Criticidad propuesta y condiciones no verificables |
| --- | --- | --- | --- |
| Receta Médica | Tipo, paciente y al menos un `medicamentos_recetados[].medicamento` no vacío. Profesional sujeto al acuerdo sobre su rol. | Edad, matrícula, especialidad, diagnóstico y CIE-10 si constan. Estudio no obligatorio por ser receta. | Mantener `dosis == ILLEGIBLE` como crítico ya implementado. Equipo debe aprobar si toda dosis ausente bloquea, y cuándo una prescripción puede no requerirla. No equiparar ausencia con ilegibilidad. |
| Informe de Laboratorio | Tipo, paciente y `estudio_realizado` no vacío como identificación del examen. | Edad, profesional/matrícula cuando consten; diagnóstico y CIE-10 no universales; medicación normalmente fuera del perfil, salvo que el documento la incluya. | Resultados analíticos, unidades, rangos y fecha no tienen campos propios. No declarar informe completo por tener solo nombre de estudio. Equipo debe definir requisitos y tratamiento de lo no verificable. |
| Informe de Estudio por Imágenes | Tipo, paciente y `estudio_realizado` no vacío. | Profesional/matrícula, edad, especialidad, diagnóstico y CIE-10 si constan. Medicación no exigida universalmente. | No exigir diagnóstico positivo: un informe normal puede ser válido. Hallazgos/conclusión no tienen campos separados; diagnóstico no equivale a todos los hallazgos ni a validar el informe. |
| Orden / Solicitud de Procedimiento | Tipo y paciente; identificación del procedimiento es un candidato esencial, pero no está representada inequívocamente. | Profesional y matrícula sujetos al rol acordado; diagnóstico/CIE-10 si constan; medicación solo cuando corresponda. | No reinterpretar `estudio_realizado` como procedimiento solicitado sin acuerdo: realizado y solicitado son conceptos distintos. Indicación, motivo y dispositivo/flujo no están estructurados en el contrato. |
| Epicrisis / Informe de Alta | Tipo y paciente. Diagnóstico principal es candidato a requisito específico, pendiente de validación; no se inventa si falta. | Estudios, profesional/matrícula, especialidad, edad, CIE-10 y prescripciones cuando consten. | Resumen de evolución, situación al alta, destino, seguimiento y validación/firma no tienen campos propios. Una lista vacía de medicamentos no demuestra una omisión. Equipo debe definir el mínimo funcional antes de activar el perfil. |
| Certificado Médico | Tipo y paciente; profesional emisor es candidato, pendiente de resolver el rol de `medico_solicitante`. | Edad, matrícula y especialidad según el proceso. Diagnóstico, estudio, medicamentos y CIE-10 no se exigirían universalmente. | No castigar automáticamente un certificado sin diagnóstico. Motivo del certificado, fechas/período y firma no están representados: no afirmar que se verificaron. Criticidad y obligatoriedad pendientes del equipo. |

Ningún campo opcional pasa a obligatorio porque aparezca en el ejemplo JSON.
La presencia de una clave requerida por el esquema y la presencia de un valor
útil no son equivalentes: muchos valores aceptan `null` o listas vacías.

## 4. Estados internos propuestos para cada criterio

| Estado | Significado | Tratamiento candidato, pendiente de validar |
| --- | --- | --- |
| Presente | Valor estructuralmente usable en la extracción. No prueba fidelidad al original. | `True` si el criterio forma parte del perfil aprobado. Cero numérico válido no se considera ausencia. |
| Ausente | Campo aplicable sin valor útil en el JSON: clave ausente, `null`, texto vacío o lista vacía cuando se exige al menos un elemento. | `False` para un criterio exigido; no demuestra que el original carecía del dato. |
| No aplicable | El perfil aprobado determina que ese criterio no corresponde a ese tipo/caso. | Excluir del denominador. Nunca deducirlo solo porque llegó `null`. |
| No verificable | El requisito no puede comprobarse con los campos/evidencias disponibles, o el valor está explícitamente ilegible. | No contarlo como cumplido. Propuesta conservadora: `False` si es exigido y bloqueo de aceptación si se aprueba como crítico. No inventar campos ni contenido. |

Los opcionales se registran, pero no se propone penalizar su ausencia ni usarlos
para inflar completitud. No aplicable y no verificable no son sinónimos.
Una dosis `ILLEGIBLE` conserva la protección actual aunque el tipo normalmente
no exija medicamentos. Si hay una lista de medicamentos exigida, comprobar cada
elemento; una lista vacía no debe aprobarse por el comportamiento de `all([])`.

## 5. Diseño técnico propuesto para implementación posterior

1. Configuración versionada de perfiles/aliases, rutas de campos, condiciones de
   aplicabilidad y criticidad. Separada de `score_confianza.py`.
2. Evaluador de presencia interno con los cuatro estados y trazabilidad del
   perfil usado, sin registrar valores clínicos ni incluirlos en la respuesta API.
3. Convertir únicamente criterios aplicables/exigidos aprobados a booleanos y
   reutilizar `evaluar_confianza`/`evaluar_confianza_con_dosis`, sin ponderaciones,
   nueva fórmula, nuevo umbral ni nuevos campos públicos.
4. Ausencias críticas aprobadas y tipo no registrado impiden aceptación por
   score. No convertir una alerta clínica del detector en una ausencia documental.
   Conservar urgencia y revisión previa del pipeline.
5. Si no hay criterios evaluables, devolver una condición interna controlada
   para revisión; no fabricar completitud `1.0` ni llamar al evaluador con `[]`.
6. Mantener el modo MVP actual como referencia de compatibilidad. Los perfiles
   nuevos deben poder evaluarse primero en modo comparación, sin cambiar destinos.
   Tipos sin perfil aprobado o con contenido esencial no representable no se
   declaran plenamente validados por seguir pasando los cuatro criterios MVP.

Este diseño es una propuesta, no código activado. La política de bloqueo para
campos críticos ausentes/no verificables debe aprobarse antes de conectarla al
enrutamiento. No cambia por sí sola las salidas reales ni resuelve las cuatro
discrepancias de urgencia registradas en S3-01.4.

## 6. Decisiones necesarias antes de activar perfiles

- Laura + Eliana: qué campos candidatos son realmente obligatorios y críticos;
  política ante valores ausentes/no verificables y composición del denominador.
- Nicolás + Eliana: aliases reales, clasificación desconocida y diferencia entre
  dato ausente en fuente y no extraído. No deducir presencia documental de un null.
- Equipo/producto: requisitos de certificados, rol de profesional, datos mínimos
  de orden/alta y revisión cuando el contrato no puede expresar el contenido esencial.
- Calibración posterior del umbral existente `0.70` sobre cada perfil y tipos
  completos/incompletos. No fijar otro umbral sin resultados y decisión acordada.

Las reglas generales todavía necesarias son validación estructural, tipo
registrado, consistencia del pipeline y protección `ILLEGIBLE`; los cuatro
criterios MVP no pueden sustituirse completamente hasta aprobar el alcance por
tipo y resolver las limitaciones de representación señaladas.

## 7. Verificación realizada y pruebas a añadir después de la aprobación

Ejecutado sin OCI/Gemini:

```powershell
Set-Location 'D:\Nocountru\mediflow\backend'
& .\.venv\Scripts\python.exe -m pytest ..\data_ai\test_score_confianza.py ..\data_ai\test\test_mvp_threshold_integration.py tests/test_orquestador_integration.py -q
```

**56 pruebas existentes aprobadas.** Las cinco reproducciones de la sección 1
se ejecutaron contra las funciones actuales, con datos ficticios, sin editar código.
No se agregaron pruebas de una matriz aún no aprobada como si fuera política oficial.

Pruebas posteriores propuestas: cada tipo completo/incompleto; receta vacía y
dosis ilegible/ausente; certificado sin diagnóstico; campo no aplicable fuera
del denominador; obligatorio no verificable; lista vacía; tipo ajeno o ambiguo
con score `0.99`; ausencia de todos los criterios; frontera `0.70`; conservación
de alerta urgente y revisión previa; invariancia del JSON público; equivalencia
del modo legado con las pruebas actuales y rechazo de configuración incoherente.

En esta fase solo se añade este documento. Se conservan los cambios locales
anteriores, la fórmula, API, Flutter, web y main. Sin commit ni push.


## 8. Implementación provisional de Laura — S3-02.1 y S3-02.4

Se implementa una política funcional conservadora del MVP, no una validación
clínica o legal de la matriz candidata. La fórmula y `0.70` no cambian:
`confidence_profiles.py` convierte los criterios exigidos/aplicables a booleanos
y reutiliza `evaluar_confianza_con_dosis` de `score_confianza.py` sin modificarlo.
Las ausencias esenciales bloquean además la aceptación aunque el cociente supere
el umbral; no se convierten artificialmente en alertas clínicas ni llevan por sí
solas el score a cero. La dosis exactamente `ILLEGIBLE` sí conserva su alerta
crítica existente. Una dosis null sigue sin equivaler a ilegibilidad; no se
establece una nueva exigencia universal de dosis ni se infieren dosis faltantes.

### Configuración y estados internos

`data_ai/rules/confidence_profiles_mvp.json` declara versión, seis tipos,
aliases explícitos y criterios con ruta, obligatoriedad, aplicabilidad y
verificabilidad. Se normalizan tildes, mayúsculas y espacios. Se registran los
aliases del dataset `Informe de imagenología` y `Orden / procedimiento`.
`Informe médico` genérico y cualquier etiqueta no registrada requieren revisión.
Un alias vacío o duplicado y criterios duplicados/incoherentes se rechazan.
No se seleccionan perfiles por archivo, ID ni texto del documento.

- `PRESENTE`: texto útil estructurado; solo este estado aporta un cumplido.
- `AUSENTE`: criterio aplicable sin texto útil. Null no declara no aplicabilidad.
- `NO_APLICABLE`: exclusión explícita del perfil; fuera del denominador.
- `NO_VERIFICABLE`: requisito sin representación contractual o valor
  explícitamente `ILLEGIBLE`; cuenta como no cumplido si es exigido y aplicable.

Los opcionales se observan sin inflar ni penalizar la completitud. El criterio
de pertenencia al catálogo siempre se evalúa: no existe un denominador vacío
ni una completitud fabricada de 1 por falta de criterios. Sin perfil el resultado
controlado tiene completitud 0 y exige revisión. La trazabilidad de estados,
bloqueos, versión y perfil es interna; no se añade al JSON público ni se
registran valores clínicos.

### Decisiones provisionales por tipo

| Tipo | Esenciales comprobables del MVP | Esencial no representado: NO_VERIFICABLE |
| --- | --- | --- |
| Todos | Tipo registrado y nombre de paciente útil | Según tipo |
| Receta | Profesional y medicamentos: lista no vacía y nombre útil en cada elemento | Ninguno adicional aprobado; dosis ausente sigue pendiente de definición funcional |
| Laboratorio | Estudio realizado | Resultados, unidades, rangos y fecha, agrupados como una brecha de representación |
| Imágenes | Estudio realizado | Hallazgos/conclusión |
| Orden/solicitud | Paciente y tipo | Procedimiento solicitado/indicación; estudio realizado no se reinterpreta como solicitado |
| Epicrisis/alta | Paciente y tipo | Evolución, alta y seguimiento, agrupados como brecha de representación |
| Certificado | Profesional | Motivo, período y firma, agrupados como brecha de representación |

Cada brecha agrupada es un criterio provisional fallido, no una ponderación
clínica. **En el flujo general esos cinco perfiles siempre requieren revisión
humana mientras el contrato no permita comprobar su contenido esencial.**
No se busca esa evidencia en campos desconocidos, ni se supone verificada a
partir del texto libre, diagnóstico, nombre de examen o score alto.

El profesional se usa únicamente como presencia estructural en receta y
certificado; `medico_solicitante` no acredita emisor ni firmante. Diagnóstico
se declara no aplicable al mínimo funcional actual: no se exige universalmente,
incluida epicrisis, cuya candidatura específica sigue pendiente de acuerdo.
Un certificado sin diagnóstico no se penaliza por esa ausencia; pasa a revisión
por la brecha de motivo/período/firma. No se añaden criterios clínicos nuevos.

### Compatibilidad explícita con la demo de urgencias

El servidor con `TRIAGE_RULES_PROFILE=synthetic_demo_v1` conserva el cálculo
anterior de cuatro criterios como referencia de compatibilidad. Se añaden los
bloqueos de tipo registrado y esenciales comprobables de los nuevos perfiles.
Solo las brechas declaradas `verifiable=false` no activan el bloqueo adicional
en esa demo. No se contabilizan como cumplidas en la evaluación por perfiles;
el score de compatibilidad sigue separado. Un esencial comprobable ilegible,
paciente ausente, receta vacía o tipo ajeno sigue bloqueado también allí.

Esta excepción explícita existe para conservar los nueve resultados sintéticos
ya validados; **no valida contenido esencial ausente del contrato y no debe
usarse para documentos reales ni como aprobación del perfil general**. No se
modifica `synthetic_demo_rules.py`, catálogo de urgencia, dataset, expectativas,
prompt ni `.env`. Prioridad urgente y revisión se siguen combinando por separado:
ningún perfil quita revisión previa, baja confianza, dosis ILLEGIBLE ni alerta
del detector. La excepción de compatibilidad requiere validación de producto
antes de ampliar su uso.

### Verificación y límites

Suite final acotada: **164 pruebas y 21 subcasos aprobados**, dos avisos de
deprecación de dependencias. Incluye evaluador original, frontera 0.70,
integración del umbral, orquestador, nuevos perfiles, urgencia general/demo,
evidencia de fuente, triage pipeline y pipeline completo con dobles locales.
`test_confidence_profiles.py` agrega 35 casos: receta vacía, elementos incompletos,
paciente ausente en seis tipos, certificados sin diagnóstico, desconocidos,
estados, no verificables aun con score >= 0.70, aliases, configuración ambigua,
opcionales, invariancia de entrada y conservación de protecciones/urgencia.
Las expectativas generales del test de demo se actualizan a revisión conservadora;
las expectativas de synthetic_demo_v1 permanecen iguales.

La evidencia de los nueve casos reales se entrega por separado al terminar su
ejecución autorizada. Las pruebas sintéticas no calibran el umbral por tipo ni
validan fidelidad clínica, OCR/transcripción, firma, fechas, roles profesionales,
o legalidad del documento. Faltan aprobación funcional de estos mínimos,
definición de dosis ausentes, requisitos de epicrisis y calibración por tipo.
No hay cambios en contrato, Flutter ni web. No se hace commit, push ni merge;
se preservan las modificaciones locales anteriores.

Resultado final de la regresión real autorizada: **9/9 casos aprobados** con
Gemini y OCI, sin mocks ni reintentos automáticos. Prioridad, destino, revisión
y estado coinciden en los nueve; JSON final y GET igual al POST verificados.
Casos MF_001, MF_004, MF_005, MF_006, MF_007, MF_008, MF_009, MF_011 y MF_012.
Perfil explícito del servidor y runner: synthetic_demo_v1. Evidencia entregada:
laura-s3-demo-regression.json. Sin cambios de etiquetas ni expectativas del CSV.
