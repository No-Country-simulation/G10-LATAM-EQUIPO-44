# Mínimos documentales implementados — 24/10/2026

Agregado por Edil. El usuario autorizó implementar la ruta B de la propuesta sin
esperar socialización. Esta implementación local parte de `1754017`; no incluye
commit ni push y no modifica main. Se conserva la propuesta inicial como registro.

## Alcance y decisiones aplicadas

El procesamiento automático es documental: clasificación, extracción,
estructuración, persistencia y destino lógico. La presencia de campos no
certifica exactitud clínica, autenticidad de firma ni habilitación profesional.
No se agregan reglas clínicas ni umbrales nuevos.

| Tipo | Mínimos para ser candidato a procesado en general |
| --- | --- |
| Todos | Tipo del catálogo y nombre de paciente útil |
| Receta Médica | Emisor explícito y al menos un medicamento; todos los elementos deben tener nombre útil |
| Informe de Laboratorio | Estudio identificado y lista no vacía; todos los resultados tienen examen y valor literales |
| Informe de Estudio por Imágenes | Estudio identificado y hallazgos o conclusión utilizables |
| Orden / Solicitud de Procedimiento | Procedimiento solicitado explícito |
| Epicrisis / Informe de Alta | Resumen de evolución y contenido de alta/cierre |
| Certificado Médico | Emisor explícito y contenido certificante |

La fórmula y el umbral `0.70` se conservan. Completar los mínimos no quita una
revisión previa, una alerta del detector ni una dosis `ILLEGIBLE`. Urgente y
auditoría pueden coexistir. El backend conserva la decisión de revisión solicitada
por Gemini y no la reemplaza para conseguir un resultado automático.

Decisiones de mínimo alcance para resolver los puntos abiertos de la propuesta:

- El emisor debe estar representado como tal; el solicitante no lo sustituye.
- Dosis null conserva el tratamiento anterior. No se inventa una dosis ni se
  presenta como validada; `ILLEGIBLE` mantiene su alerta crítica.
- Unidades y rangos de laboratorio son opcionales y solo se extraen de la fuente.
  No se asume que son correctos ni se convierte un valor. La estructura admite
  valores textuales como `"0"`, `"Negativo"` y `"No reactivo"`.
- Hallazgos o conclusión pueden satisfacer el mínimo de imágenes. Si cualquiera
  de esas alternativas está marcada `ILLEGIBLE`, se mantiene revisión aunque la
  otra sea legible. Un diagnóstico aislado no completa estos campos.
- Indicación de solicitud, diagnóstico de alta, destino/seguimiento, período del
  certificado, matrícula y firma no se hacen obligatorios universalmente. No se
  afirma haberlos verificado cuando faltan. El motivo/indicación de una orden
  se conserva cuando está escrito; no se copia de un estudio realizado.
- `null`, `None`, `N/A`, `No aplica`, `No disponible` y otros marcadores exactos
  de ausencia no cuentan como evidencia. No convierten un esencial en no aplicable.

## Contrato aditivo y extracción

Pydantic añade doce propiedades opcionales a `datos_extraidos`:

```text
profesional_emisor
resultados_laboratorio
hallazgos
conclusion
procedimiento_solicitado
indicacion_solicitud
resumen_evolucion
indicacion_alta
destino_alta
seguimiento
contenido_certificacion
periodo_certificado
```

`profesional_emisor` contiene nombre/matrícula o null. Cada resultado de
laboratorio contiene examen y valor textuales, más unidad y rango_referencia
opcionales. El período del certificado conserva texto literal; no calcula fechas.

La generación Gemini solicita todos los campos, con null/[] cuando no hay dato.
La validación sigue aceptando respuestas anteriores que omiten únicamente las
propiedades aditivas. Las claves originales siguen siendo obligatorias; los
campos nuevos presentes se validan y las claves desconocidas se rechazan en la
salida LLM. No se copian roles, hallazgos ni solicitudes desde otros campos.

El esquema de intercambio de Nicolás pasa a v1.3. Es un esquema espejo; el
cliente Gemini sigue usando su proyección `clasificacion`, `datos_extraidos` y
`decision_enrutamiento`. No hay nuevos endpoints ni cambios al registro de
revisión de seis campos. La API no incorpora un campo público de versión.

Ejemplos ficticios de los seis tipos:
[`contrato.campos-minimos-v1.example.json`](../../mediflow/backend/app/core/contrato.campos-minimos-v1.example.json).
Ilustran respuestas del contrato; no acreditan operaciones OCI reales. El
ejemplo original de Eliana se conserva.

## Perfiles y urgencia

El perfil general usa `s4-minimos-documentales-v1`. Los esenciales ahora tienen
rutas verificables; si faltan son `AUSENTE` y si son ilegibles son
`NO_VERIFICABLE`. Las listas vacías y los elementos incompletos bloquean el
procesamiento. Los opcionales no inflan el denominador ni la completitud.

Se conserva el contenido anterior en
`confidence_profiles_legacy_demo_v1.json`, usado explícitamente solo en
`synthetic_demo_v1`. Así se mantiene la compatibilidad técnica de la demo
sintética sin fabricar campos en el dataset. El perfil general no usa esa
excepción. No se alteraron archivos del dataset ni sus etiquetas.

El adaptador de urgencia ahora examina también los nuevos textos documentales y
resultados utilizando el catálogo existente. Esto evita ignorar una señal ya
cubierta que aparezca solo en una conclusión o solicitud. No analiza nombres de
profesionales como señales clínicas ni serializa todo el JSON como texto fuente.

## Compatibilidad y límites

- JSON históricos: se leen con null/[] sin reescribir OCI ni recalcular su estado.
  Un estado histórico procesado no acredita los criterios nuevos. Un análisis
  nuevo sí debe cumplirlos.
- Flutter y web: conservan datos originales y aceptan propiedades adicionales.
  Se agregaron pruebas de compatibilidad, sin cambiar su lógica. Los campos
  nuevos están disponibles en la API y en el JSON original del panel; no se
  añadieron secciones nuevas a las vistas resumidas.
- Se conservan cuentas propias, `cargado_por`, decisiones, copia verificada y
  recuperación por ID. Los errores de proveedor siguen conservando recibido.
- El score operativo continúa siendo interno y no una medida de exactitud clínica.
- La aceptación real de Gemini/OCI y del despliegue sigue pendiente para el otro
  equipo. Las pruebas de esta implementación usan únicamente datos sintéticos.

Al cambiar de versión se debe reiniciar el backend para cargar Pydantic, prompt
y evaluador coordinadamente. No basta con cambiar solamente el archivo de perfiles.

## Verificación final local

| Grupo | Resultado |
| --- | --- |
| Backend, data_ai y presentación | 711 pruebas y 29 subcasos aprobados; seis externas excluidas |
| Web | 195 pruebas aprobadas; cero fallos |
| Flutter | 187 pruebas aprobadas; dos opt-in omitidas |
| Flutter analyze | Sin problemas |

Se comprueban seis tipos completos/incompletos, emisor distinto del solicitante,
listas vacías y resultados incompletos, placeholders, alternativas ilegibles,
conservación de urgencia/revisión, compatibilidad de respuestas históricas y
POST → pipeline real → persistencia simulada → GET. Las muestras antiguas de
recetas se actualizaron con un emisor ficticio explícito sin cambiar sus asserts
ni expectativas. No se ejecutaron Gemini/OCI reales ni se modificó `.env`.

El informe estructurado y las rutas de logs están en
[`evidencias/minimos-documentales-24-octubre.json`](evidencias/minimos-documentales-24-octubre.json).
No se hicieron commit, push ni cambios en main; los archivos permanecen en la
rama local `docs/readme-campos-minimos-s4`.
