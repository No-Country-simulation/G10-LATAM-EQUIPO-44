# Propuesta de campos mínimos por tipo documental

Agregado por Edil — 24/10/2026. Base revisada: `1754017`.
**PROPUESTA INICIAL CONSERVADA COMO REGISTRO.**

> Actualización del 24/10/2026: el usuario autorizó implementar la ruta B sin
> esperar socialización. La implementación local y las decisiones aplicadas se
> describen en [minimos-documentales-implementados.md](minimos-documentales-implementados.md).
> Las secciones siguientes documentan el diagnóstico y las alternativas previas;
> sus referencias a campos inexistentes o pendientes corresponden a la base `1754017`.

Esta propuesta permite decidir cómo ampliar el procesamiento automático de
casos estándar. No cambia contratos JSON, Pydantic, prompts, perfiles, fórmula,
umbral, destinos ni reglas de urgencia. No declara aprobados requisitos clínicos,
firmas, diagnósticos ni la validez del documento.

## 1. Punto de partida comprobado

- El catálogo configurado contiene seis tipos; no existe un perfil genérico
  llamado «Informe médico». Las denominaciones se detallan en la matriz inferior.
- `confidence_profiles_mvp.json` define el catálogo y los criterios de cada tipo;
  el evaluador añade la pertenencia al catálogo y evalúa paciente como base.
  La receta añade profesional y medicamentos; los otros cinco tipos contienen
  al menos un esencial no representado y por ello requieren revisión en `general`.
- El esquema actual representa paciente, profesional solicitante, estudio
  realizado, diagnóstico, CIE-10 y medicamentos/dosis. No representa resultados
  de laboratorio, hallazgos, procedimientos solicitados o contenido de alta.
- El evaluador comprueba presencia estructurada, no fidelidad al original.
  `null` no distingue entre dato inexistente, dato no extraído y dato ilegible.
- Una clasificación alta no elimina los bloqueos por esenciales ausentes o
  no verificables. Las señales de urgencia se evalúan por separado.

Fuentes: [Pydantic](../../mediflow/backend/app/models/schemas.py),
[perfiles vigentes](../../mediflow/data_ai/rules/confidence_profiles_mvp.json),
[evaluador](../../mediflow/data_ai/confidence_profiles.py),
[fórmula](../../mediflow/data_ai/score_confianza.py) y
[diagnóstico anterior](../../mediflow/data_ai/docs/criterios_por_tipo_propuesta_s3_02_1.md).
El diagnóstico anterior y sus decisiones provisionales se conservan.

## 2. Qué significaría «automático» en este MVP

Propuesta: procesamiento documental significa extraer, estructurar, clasificar,
persistir y asignar un destino lógico. No significa autorizar un tratamiento,
validar una receta, verificar una firma o diagnosticar a una persona.

El equipo debe aprobar ese alcance y los mínimos antes de permitir un nuevo
camino automático. La salida `procesado` indicaría finalización del alcance
documental acordado, sin presentar como verificados componentes fuera de él.
Guardar un archivo o indexar sus metadatos no equivale por sí solo a haber
extraído todo su contenido esencial.

## 3. Categorías de la matriz propuesta

| Categoría | Significado candidato |
| --- | --- |
| Aplicable | El dato corresponde al tipo y propósito declarado del procesamiento. |
| Mínimo obligatorio | Debe estar presente y utilizable para ese alcance automático. |
| Crítico documental | Si falta o no puede verificarse, bloquea ese alcance aunque el score sea alto. No es una alerta clínica. |
| Opcional | Se conserva si está en la fuente; su ausencia no altera la completitud mínima. |
| No aplicable | El perfil aprobado determina que no corresponde al caso; nunca se deduce de `null`. |
| No verificable | El contrato o la evidencia disponible no permite comprobar un requisito. Nunca cuenta como cumplido. |

Tipo registrado e identificación de paciente utilizable son candidatos comunes.
Por compatibilidad se propone usar `paciente.nombre`, disponible actualmente;
esto no identifica unívocamente al paciente. El equipo decidirá si necesita un
identificador adicional. Edad, especialidad y CIE-10 no serían mínimos universales.

En las tablas, las rutas actuales son relativas a `datos_extraidos`, salvo
`clasificacion.tipo_documento`. Los nombres nuevos son candidatos, no campos API.

## 4. Matriz de mínimos candidatos para extracción documental

**Todas las filas están PENDIENTES de aprobación funcional y contractual.**

| Tipo real del catálogo | Aplicables y mínimos candidatos | Opcionales / no exigidos universalmente | Críticos documentales candidatos | Brecha actual |
| --- | --- | --- | --- | --- |
| Receta Médica | Paciente; profesional emisor identificable; al menos un medicamento con nombre útil. Dosis y demás instrucciones cuando correspondan al contenido prescrito, según política que debe acordarse. | Edad, especialidad, diagnóstico, CIE-10. Estudio realizado no sería mínimo del perfil receta. | Paciente o medicamento sin identificar; nombre de medicamento ilegible; instrucciones esenciales ilegibles. Obligatoriedad de dosis ausente y del emisor pendiente. | Hay `medico_solicitante`, pero no diferencia emisor/firmante. Dosis existe y admite null; no distingue ausencia en fuente de fallo de extracción. |
| Informe de Laboratorio | Paciente; examen identificado; al menos un resultado atribuible a un examen, legible y extraído de la fuente. | Diagnóstico/CIE-10; edad; profesional solicitante; rangos y fecha según alcance aprobado. Unidad aplicable a resultados cuantitativos cuando la fuente la utiliza, no a todo resultado cualitativo. | Falta de examen o resultado; asociación examen-resultado ambigua; valor ilegible. Política de unidad ausente pendiente según representación. | Solo existe `estudio_realizado`; no hay estructura de resultados/valor/unidad. El nombre de examen no demuestra que se extrajeron sus resultados. |
| Informe de Estudio por Imágenes | Paciente; estudio identificado; hallazgos o conclusión documental utilizable, según el mínimo que acuerde el equipo. | Especialidad, profesional, edad, CIE-10; diagnóstico solo cuando esté documentado. | Ausencia de estudio o contenido interpretativo utilizable; conclusión ilegible cuando sea exigida por el alcance. | `diagnostico_principal` no equivale automáticamente a hallazgos/conclusión; no existen campos propios para estos. |
| Orden / Solicitud de Procedimiento | Paciente; procedimiento solicitado identificable; indicación o motivo cuando el equipo lo exija para el destino elegido. | Edad, CIE-10, diagnóstico y datos del solicitante según política aprobada. Medicamentos no serían mínimos de una orden sin prescripción. | Procedimiento solicitado ausente/ilegible; contradicción no resuelta sobre qué se solicita. | No existe `procedimiento_solicitado`. No reutilizar `estudio_realizado`: solicitado y realizado tienen significados distintos. |
| Epicrisis / Informe de Alta | Paciente; resumen de atención/evolución; información de alta o cierre del episodio. Diagnóstico principal es candidato a esencial, sujeto a aprobación. | Medicación, estudios, recomendaciones/seguimiento y fechas según lo que conste y el alcance; CIE-10 no universal. | No poder identificar episodio/contenido de alta; resumen esencial ilegible. Criticidad de diagnóstico, destino y seguimiento pendiente. | Hay diagnóstico y medicamentos, pero no representación diferenciada de evolución/alta. El diagnóstico actual no prueba que se extrajo la epicrisis. |
| Certificado Médico | Paciente; emisor identificable; finalidad o contenido de la certificación. Período solo cuando el certificado establece uno y el equipo lo requiera. | Diagnóstico, CIE-10, edad y especialidad; no exigir diagnóstico por defecto. | Falta de paciente, emisor o contenido certificante utilizable. Política de período y de evidencia de firma pendiente. | El profesional solicitante no acredita emisor. No hay finalidad/período/firma representados; tampoco se verifica autenticidad de firma. |

Los mínimos anteriores son candidatos de producto, no reglas clínicas nuevas.
«Profesional identificable» tampoco demuestra matrícula vigente ni autenticidad.
La matrícula existe en el contrato, pero hacerla obligatoria por tipo requiere
acuerdo; no se infiere una matrícula cuando la fuente no la proporciona.

## 5. Dos rutas de alcance para decidir

### Ruta A: alcance acotado con el contrato existente

Podría aprobarse un perfil de **indexación documental técnica** que utilice
únicamente datos ya representados. No sería la validación de contenido completo
descrita en la matriz anterior. Su propósito y sus límites tendrían que quedar
explícitos en la entrega y en la interpretación de `procesado`.

| Tipo | Lo que puede comprobarse ahora | Límite de la posible automatización acotada |
| --- | --- | --- |
| Receta | Tipo, paciente, nombre de profesional y lista no vacía de medicamentos. | Falta acordar rol profesional, tratamiento de dosis null y alcance de instrucciones. |
| Laboratorio | Tipo, paciente y nombre del estudio. | Puede indexar un informe; no demuestra extracción de resultados. |
| Imágenes | Tipo, paciente y nombre del estudio. | Puede indexar el informe; diagnóstico no sustituye hallazgos/conclusión. |
| Orden | Tipo y paciente. | Esos metadatos no permiten afirmar que se identificó el procedimiento solicitado; la extracción de una orden estándar requiere la ruta B o revisión. |
| Epicrisis/alta | Tipo, paciente y diagnóstico si aparece. | No acredita extracción del resumen ni del alta; el alcance completo requiere ruta B o revisión. |
| Certificado | Tipo, paciente y nombre de profesional bajo el campo actual. | No acredita emisor ni contenido de la certificación; el alcance completo requiere ruta B o revisión. |

Esta ruta no consiste en borrar los bloqueos actuales para que aumenten los
aprobados. Requeriría un perfil nuevo, aprobado y versionado para ese propósito.
Las brechas seguirían siendo `NO_VERIFICABLE`; no se convertirían en `PRESENTE`
ni en `NO_APLICABLE`. Si el equipo mantiene una brecha como esencial para el
alcance elegido, seguirá bloqueando. Reducir el alcance no puede presentarse
como haber comprobado la información excluida.

### Ruta B: extensión mínima y aditiva del contrato

**Ruta recomendada como propuesta para ampliar extracción estándar**, sujeta a
aprobación de Laura, Eliana y el equipo. Primero acordar significado y mínimos;
después nombres, tipos y migración. Los campos siguientes **NO existen en la API**.

| Bloque candidato | Representación candidata | Decisión pendiente |
| --- | --- | --- |
| Profesional | `profesional_emisor.nombre`, `.matricula`, manteniendo `medico_solicitante`. | En qué tipos es esencial y cómo diferenciar emisor, solicitante y firmante. |
| Laboratorio | `resultados_laboratorio[]` con `examen`, `valor`, `unidad`, `rango_referencia`. | Tipo de valor numérico/textual; unidad y rango aplicables; mínimo por resultado; no inventar rangos ni resultados. |
| Imágenes | `hallazgos` y `conclusion`. | Si basta uno, qué contenido se espera y cómo indicar ilegibilidad/ausencia. |
| Orden | `procedimiento_solicitado` e `indicacion_solicitud`. | Cuándo el motivo es esencial y cuál es su destino documental. |
| Alta | `resumen_evolucion` e `indicacion_alta`; posibles `destino_alta` y `seguimiento`. | Mínimo de episodio/alta y criticidad de diagnóstico, destino o seguimiento. |
| Certificado | `contenido_certificacion` y posible objeto `periodo_certificado`. | Qué certificados aplican a un período y qué datos bastan para el alcance elegido. |
| Evidencia documental | Estado de extracción por campo o criterio, fuera del score clínico. | Forma interna/pública; distinguir fuente ausente, extracción fallida y no verificable sin afirmar autenticidad. |

No se propone añadir un bloque vacío por cada tipo y considerarlo completo.
Las listas exigidas necesitan elementos útiles; los campos solo se completan
si constan en la fuente. Una evidencia de firma, si se acuerda representarla,
no significaría que el sistema verificó su autenticidad.

El versionado debe acordar cómo se anuncian cambios de esquema y política sin
renombrar campos existentes. Incorporar propiedades opcionales no basta por sí
solo: hay que confirmar que los consumidores acepten datos nuevos. No se agregan
en este documento campos de versión ni endpoints ficticios al contrato vigente.

## 6. Estados, score y bloqueos que deben conservarse

| Estado | Interpretación y tratamiento propuesto |
| --- | --- |
| `PRESENTE` | Valor estructurado utilizable para un criterio aprobado. No prueba fidelidad al original. Solo este estado suma un cumplido. |
| `AUSENTE` | Criterio aplicable sin valor útil. Si es esencial, exige revisión; null no demuestra ausencia en la fuente. |
| `NO_APLICABLE` | Exclusión explícita del perfil aprobado por tipo/caso. Fuera del denominador; no se activa por encontrar null. |
| `NO_VERIFICABLE` | Esencial no representado, ilegible o sin evidencia suficiente. No suma; bloquea si es requerido. |

La fórmula actual se conserva como referencia sin alterarla:

```text
completitud = criterios cumplidos / criterios exigidos y aplicables
score_operativo = 0 si alerta_critica; en otro caso min(score_clasificacion, completitud)
ambiguo_por_score = score_operativo < 0.70
revision = ambiguo_por_score o alerta_critica o bloqueo_esencial o revision_previa o revision_del_detector
```

La pertenencia al catálogo se evalúa y evita denominadores vacíos. El valor
`0.70` no es una probabilidad de exactitud clínica y no se cambia aquí. Si se
aprueba otra composición de criterios, debe comprobarse su comportamiento por
tipo antes de activar el perfil; no se deduce que el umbral quedó calibrado.

Una dosis exactamente `ILLEGIBLE` conserva su alerta crítica actual. Dosis
null no equivale a ilegibilidad: hacerla bloqueante o aceptarla necesita una
decisión funcional. El score de clasificación público y el score operativo
interno siguen separados. Campos críticos de completitud no se convierten en
alertas clínicas; la prioridad `Urgente` no se rebaja por una revisión humana.

## 7. Casos para aprobar la política antes de implementarla

Todos los casos son ejemplos sintéticos de comportamiento esperado propuesto.
«Candidato automático» exige, además, contrato válido, score suficiente y
ausencia de revisión previa, bloqueos o señales que requieran auditoría.

| Caso | Datos relevantes | Resultado propuesto a ratificar |
| --- | --- | --- |
| Receta estándar | Paciente, emisor y medicamentos útiles; instrucciones legibles según política acordada. | Candidato automático del alcance aprobado; no equivale a autorizar dispensación. |
| Receta incompleta | Lista de medicamentos vacía o nombre de un elemento ausente. | `AUSENTE`, revisión aunque clasificación sea alta. |
| Receta ilegible | Alguna dosis es `ILLEGIBLE`. | Conservar alerta crítica y revisión actual; no completar la dosis. |
| Laboratorio completo futuro | Examen y resultado legibles, unidad cuando corresponda al valor. | Candidato automático después de ruta B aprobada y conectada. Hoy el resultado es `NO_VERIFICABLE`. |
| Laboratorio cualitativo | Resultado textual; la fuente no usa unidad ni rango numérico. | El perfil aprobado puede declarar esos componentes `NO_APLICABLE`; no inventarlos. |
| Imágenes completo futuro | Estudio identificado y contenido de hallazgos/conclusión utilizable según mínimo aprobado. | Candidato automático tras ruta B; conservar cualquier urgencia o revisión del detector. |
| Imágenes sin conclusión requerida | Estudio presente pero falta el contenido que el perfil exige. | Revisión por esencial ausente; un diagnóstico suelto no lo sustituye. |
| Orden estándar futura | Procedimiento solicitado explícito e indicación si el perfil la exige. | Candidato automático tras ruta B. Un `estudio_realizado` no satisface este requisito. |
| Alta futura | Paciente y resumen/alta suficientes según matriz aprobada. | Candidato automático documental tras ruta B; seguimiento solo si es exigible al caso. |
| Certificado futuro | Paciente, emisor y contenido certificante útiles. | Candidato automático documental tras ruta B; diagnóstico ausente no obliga por sí solo a rechazo. |
| Tipo desconocido | `clasificacion.tipo_documento` no pertenece al catálogo o sus aliases aprobados. | Revisión, aunque score de clasificación sea alto; no activar un perfil genérico inventado. |
| Metadatos completos, esencial no representado | Nombre de paciente y estudio útiles, pero el resultado requerido no tiene campo. | Mantener `NO_VERIFICABLE`; no presentarlo como extracción completa. |

## 8. Compatibilidad y siguiente implementación, solo tras aprobación

1. Laura y el equipo acuerdan esenciales, aplicabilidad y alcance de «procesado».
   Eliana acuerda la representación contractual y compatibilidad; Nicolás valida
   qué puede extraer el LLM sin inferir contenido ausente.
2. Definir el rol de profesional, dosis null, mínimos de alta/certificado y uso de
   resultados cualitativos. Resolver explícitamente qué seguirá siendo revisión.
3. Versionar perfiles nuevos; mantener versión vigente como referencia y modo
   de comparación antes de cambiar destinos. No activar el perfil por nombre de
   archivo, etiqueta esperada, ID del dataset o instrucciones del documento.
4. Si se aprueba ruta B, actualizar de forma coordinada Pydantic, esquema de
   extracción, prompt y validación. Campos nuevos pueden admitir null al leer
   históricos, pero un histórico sin evidencia no cumple los nuevos mínimos.
5. Preservar `cargado_por`, identidad del auditor, contrato de revisión y copia
   OCI. No reescribir los JSON históricos para fabricar información nueva.
6. Verificar compatibilidad de consumidores antes de cambiar API; no modificar
   Flutter ni web por anticipado. Registrar perfil utilizado sin valores clínicos
   en logs. Mantener revisión previa, desconocidos, ilegibilidad y urgencia.
7. Ejecutar casos completos/incompletos/no aplicables/no verificables y comparar
   resultados previos. La aceptación real se hará en el equipo del despliegue;
   este documento no ejecuta OCI/Gemini ni reemplaza esas evidencias.

**Decisión solicitada al equipo:** aprobar por tipo alcance, esenciales y ruta
A o B; registrar criterios aceptados y responsables. Hasta entonces, los seis
perfiles vigentes y sus bloqueos se conservan exactamente como están.
