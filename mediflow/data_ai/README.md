# Módulo LLM de MediFlow para Sprint 2

> Agregado por Edil: corrección posterior del 17 de octubre: **9/9 casos reales
> del dataset aprobados**, incluidos 4/4 urgentes y 5/5 normales, exclusivamente
> con `TRIAGE_RULES_PROFILE=synthetic_demo_v1` aprobado para datos sintéticos.
> `general` sigue siendo el valor predeterminado y no aplica estas reglas
> experimentales. Ver [causa raíz, configuración y evidencias](../../docs/sprint-3/correccion-urgencia-demo-17-octubre.md).

> Agregado por Edil, 17 de octubre: S3-01.4 ya tiene una ejecución real de los
> nueve documentos normales/urgentes del dataset, confirmados sintéticos por
> el usuario. Tras resolver la conversión CRLF de un PDF, 9/9 completan el
> pipeline; 5/5 normales coinciden, pero 0/4 urgentes coinciden con el CSV.
> No confundir ejecución técnica con aprobación de prioridad. Ver
> [informe y evidencias S3-01.4](../../docs/sprint-3/nico-s3-01-4-pruebas-dataset-17-octubre.md).
> Ese fue el resultado previo a la corrección de demo enlazada arriba.
> Las notas de ausencia de ejecución real de abajo describen el desarrollo
> original de Sprint 2. El evaluador optativo está en `validate_dataset_pipeline.py`.

Implementación preparada para la tarea S2-01 originalmente asignada a Nicolás.
Se agregó después del commit de integración b75996e. Las pruebas son con mocks:
no constituyen evidencia de una extracción exitosa contra el proveedor real.

## Alcance e interfaz

- app/services/document_text.py extrae localmente TXT UTF-8 y PDF con texto.
- app/services/gemini_client.py implementa GeminiClinicalClient con el SDK
  oficial google-genai. Se usa la API generate_content documentada por el SDK.
- prompts/master_prompt.txt define instrucciones de clasificación/extracción.
- Agregado por Edil: el endpoint lo invoca con analyze=true, sin retirar la recepción original.
- No hace operaciones OCI, notificaciones ni movimientos entre buckets.
- PDF cifrados se rechazan. El extractor local no hace OCR; Agregado por Edil: imágenes y PDF sin texto pueden enviarse como media nativa a Gemini. Requiere un modelo compatible y prueba real pendiente.
- Límites locales: 10 MiB, 100 páginas PDF, 80 000 caracteres de entrada.
- El contenido del documento se envía como dato JSON en rol user; el prompt
  confiable se envía separadamente como system_instruction. No hay herramientas.
  Esta separación reduce exposición a instrucciones del documento, pero no
  garantiza inmunidad del modelo a inyección ni exactitud clínica.

El llamador primero ejecuta extract_document_text(bytes, filename) y luego
GeminiClinicalClient.process(text, document_id=..., storage=...).
process devuelve un TriageResponse validado. extract(text) devuelve la proyección
ClinicalExtraction de los bloques ya existentes: clasificacion, datos_extraidos
y decision_enrutamiento. No se define un contrato HTTP nuevo.

document_id y almacenamiento_oci provienen del llamador; el LLM no los genera.
notificacion_generada es null. status se deriva de requiere_auditoria_humana;
indica extracción/validación local, no un movimiento real ni aprobación clínica.
El nombre del bucket recibido se conserva, aunque el estado propuesto sea procesado.
Los metadatos OCI de la prueba manual indican no_verificado; no simulan un upload exitoso.

## Contrato y límites clínicos

Se reutilizan los esquemas existentes de app/models/schemas.py sin modificarlos.
La salida LLM debe incluir las claves de sus bloques, incluidos los campos
nullable: se rechazan campos faltantes, claves nuevas, tipos incompatibles,
JSON duplicado, NaN/Infinity y confianza fuera del rango existente.
Exigir campos explícitos evita aplicar silenciosamente defaults como Rutina
o requiere_auditoria_humana=False.

No se inventan datos ausentes en el prompt: se solicitan null y auditoría cuando
corresponde. CIE-10 se extrae solo si aparece. Esto NO es una garantía verificable
de fidelidad clínica: hay que evaluar resultados reales y disponer de revisión humana.
La confianza del modelo no es un score calibrado.
El esquema Pydantic admite prioridad como texto; para casos indeterminados el
prompt usa Rutina como valor técnico y solicita auditoría; coincide con el catálogo actualizado de Eliana.
Agregado por Edil: medicamentos/dosis se añaden como lista opcional, conservando los campos previos.
La aprobación para completar la integración permitió esta ampliación compatible; los valores ausentes permanecen null o [].

## Configuración

El cliente carga mediflow/.env con el cargador existente, sin sobrescribir la
terminal. La configuración OCI y los tres buckets se conservan.

GEMINI_API_KEY debe configurarse únicamente en el entorno o .env ignorado por Git.
GEMINI_MODEL es obligatorio: no hay modelo fijo ni selección automática.
Elige un identificador disponible para tu cuenta con las capacidades y precios
verificados. No todos los modelos ni cuentas tienen cuota gratuita.
GEMINI_TIMEOUT_SECONDS=30 (rango 1-300).
GEMINI_STRUCTURED_OUTPUT=true usa response_mime_type y response_json_schema.
Si el modelo no admite esa función, configura explícitamente false: el esquema
se añade al prompt y la validación local permanece obligatoria.
No se cambia de modelo ni se reenvía automáticamente al fallar; un intento por solicitud.
Errores de API/modelo, autenticación, cuota, timeout, red, respuesta bloqueada
o truncada se convierten en excepciones del módulo con mensajes sanitizados.
No se registran claves, documentos, contenido de respuesta ni mensajes crudos del proveedor.

## Dependencias y pruebas locales

Verificado con Python 3.14.7, google-genai 2.29.0 y pypdf 6.19.0.
Desde mediflow/backend, usa el Python de tu entorno virtual:

    python -m pip install -r ../requirements.txt
    python -m pytest tests/test_gemini_client.py tests/test_document_text.py -v
    python -m pytest tests -m "not integration" -v

Todas las pruebas Gemini usan clientes simulados y datos sintéticos. No consumen
tokens. El test de inyección verifica aislamiento y rechazo de claves no
permitidas; no representa una prueba real de resistencia del modelo.

## Prueba manual real (no ejecutada durante el desarrollo)

Requiere autorización específica y verificación de precios/cuotas.
No uses el dataset sin confirmar antes que sus datos son sintéticos.

1. En mediflow/.env, configura GEMINI_API_KEY localmente y GEMINI_MODEL con un
   identificador verificado en tu cuenta. No publiques ni muestres ese archivo.
2. Desde mediflow/backend, crea una nota sintética temporal:

    $demoFile = Join-Path $env:TEMP 'mediflow-gemini-demo.txt'
    Set-Content -LiteralPath $demoFile -Encoding UTF8 -Value 'Certificado ficticio para prueba técnica. No se indican paciente, diagnóstico ni código CIE-10.'

3. Cuando hayas autorizado la llamada, ejecuta:

    python ../data_ai/test_llm.py --allow-gemini --synthetic --file $demoFile

Esperado: GEMINI_OK y código de salida 0 si el proveedor responde y el contrato
valida. Los errores producen código no cero. La consola no muestra la extracción
clínica y no se crea ningún objeto OCI.
Sin ambos indicadores la prueba termina antes de inicializar el cliente.

## Pendiente para Brando y Laura

Agregado por Edil: el módulo ya está conectado al endpoint y sus errores se traducen a HTTP.
La recepción inicial continúa como opción predeterminada; el análisis es opt-in.
Quedan OCR, evaluación real de calidad, validación clínica y reglas de confianza/
urgencia definitivas. Este módulo no sustituye esas tareas con mocks.

## Referencias oficiales

- https://googleapis.github.io/python-genai/
- https://ai.google.dev/gemini-api/docs/structured-output
- https://ai.google.dev/gemini-api/docs/troubleshooting
- https://ai.google.dev/gemini-api/docs/pricing


## Agregado por Edil: incorporación de la entrega de Nicolás
Se conservan su esquema en schemas/mediflow_schema.json y sus reglas en rules/triage_rules_v1.json como referencia de evaluación sintética.
El cliente del backend usa el contrato Pydantic de Eliana para evitar dos definiciones activas incompatibles.
La diferencia de salida es intencional: el esquema experimental incluye status; el cliente reutilizable deja que el backend lo calcule.
El prompt conserva las instrucciones útiles de Nicolás y añade una aclaración al final para esta diferencia.
Las reglas del dataset no se inyectan automáticamente en solicitudes generales: no son políticas clínicas aprobadas.
El script original está preservado como texto en docs/integration/entregas-originales/Sprint-2-Nico/test_llm.py.txt.
No se ejecuta porque su validación contiene una clave inexistente, no limita el tiempo de espera y no exige confirmación de envío.
El script activo conserva los indicadores --allow-gemini y --synthetic, usa el mismo cliente probado del backend y no imprime el documento.
