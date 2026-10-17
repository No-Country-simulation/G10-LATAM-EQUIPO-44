# Integración de entregas Sprint 3 — 16 de octubre de 2026

Agregado por Edil: integración selectiva preparada y probada fuera de main antes
de fusionar. Se conserva la arquitectura Gemini, el consentimiento de Flutter,
la carga de mediflow/.env y los tres buckets independientes.

## Entregas y procedencia

| Rama | Commit | Integración |
| --- | --- | --- |
| feature/orquestador | df68773, Eliana | Separación de nodos/servicio, urgencia, confianza y decisión. El commit ya está contenido en la rama de Brando; no se duplica. |
| feature/s3-06-integracion | 8ea09db, Brando | Adaptador Python de orquestación, transferencia OCI verificada, pruebas y documentación. Se adapta al API vigente. |
| fix/s3-umbral-confianza-mvp | 29d3cb2, Laura | Constante compartida UMBRAL_CONFIANZA_MVP=0.70, defaults, documentación y pruebas, conservando validaciones existentes. |
| feature/s3-edil-cierre-flutter, trabajo local | Base 8ef6e09 | Seguimiento GET, conservación de ID/resultado, confirmación de reenvío incierto, validación de tamaño y visualización de confianza. |

Los commits de las ramas originales se registran como antecesores únicamente
después de adaptar y verificar sus aportes. La estrategia de merge conserva el
árbol integrado y probado; no reinstala los archivos antiguos de rutas, arranque,
configuración o proveedor. Las copias originales están en
entregas-originales/16-octubre y sus versiones exactas permanecen en Git.
En las copias de texto se normalizan espacios finales y saltos de línea para
pasar la comprobación de formato; los originales exactos siguen en sus commits.

## Por qué no se aceptaron todos los archivos literalmente

- routes.py de Brando quitaba los GET, analyze, persistencia JSON y errores
  controlados. Se conserva el API existente y se suma la copia verificada.
- app/main.py de esa rama quitaba la carga canónica de configuración y CORS.
  Se conserva el arranque existente.
- config.py y llm_client.py introducían configuración paralela y Cohere; quedan
  como referencias, no como módulos activos. Gemini sigue siendo el proveedor.
- Se conserva httpx y los extractores actuales; no hace falta agregar PyMuPDF
  para una propuesta de proveedor que no está activa.
- El LangGraph original de Eliana no declaraba dependencia. Se conserva el
  adaptador Python con invoke de la revisión posterior de Brando; no se afirma
  que el runtime esté ejecutando LangGraph.
- No se agrega el endpoint manual de movimiento de objetos sin autorización.

## Flujo final del código integrado

1. POST valida archivo, guarda original y JSON recibido en recibidos.
2. analyze=false termina en recepción: no ejecuta IA, reglas ni transferencia.
3. analyze=true conserva el consentimiento y llama al cliente Gemini existente.
4. La extracción validada pasa al orquestador y a los módulos de Nicolás/Laura.
5. Una revisión ya solicitada nunca se desactiva. La urgencia puede coexistir
   con auditoría y nunca se rebaja una prioridad Urgente previa.
6. La prioridad se escribe en clasificacion.nivel_prioridad; status sigue en
   la raíz. No se agregan campos internos a decision_enrutamiento.
7. El original se copia a procesados o auditoria_humana, con verificación de
   tamaño, SHA-256 y versión ETag. La copia no borra recibidos.
8. Solo después se guarda JSON final y devuelve 201 con la ubicación de la
   copia verificada. GET recupera el mismo resultado.
9. Fallos de IA, copia o JSON final conservan la recepción y retornan errores
   controlados con X-Document-ID cuando ya se conoce el documento.

El texto para las reglas procede exclusivamente del TXT/PDF extraíble. No se
serializa el JSON como si fuera texto fuente. Imágenes y PDF sin texto conservan
análisis multimodal Gemini; las reglas solo ven sus campos estructurados y no
se afirma cobertura OCR ni descarte de riesgo.

## Criterios y límites del MVP

El umbral 0.70 es operativo de la demo, no una garantía clínica calibrada. Se
conservan los cuatro criterios genéricos aportados por la rama: tipo conocido,
nombre de paciente, nombre de profesional y diagnóstico o estudio. No son una
tabla definitiva por tipo; una revisión puede ser conservadora o innecesaria.
Un tipo desconocido obliga a auditoría aunque los otros tres criterios sumen
0.75. La dosis ILLEGIBLE se trata según el módulo existente, sin convertir
automáticamente una dosis ausente en ilegible.

No hay aprobación humana persistida ni autorización por documento. La web de
auditoría sigue siendo prototipo. No hay reprocesamiento idempotente: seleccionar
otra vez el mismo archivo puede crear otro ID. No se declara listo para exponer
datos clínicos reales públicamente.

## Preservación y verificación

Se copiaron y verificaron por SHA-256 los trece archivos locales antes de tocar
Git, incluidos los no seguidos. Respaldo:
C:/Users/leno/AppData/Local/Temp/MediFlow-antes-integracion-16-oct-s5vyl2j1.
Doce quedaron idénticos; triage_api_service.dart solo incorpora el mensaje de
copia verificada y su formato. No se alteran stashes, worktrees o credenciales.

Backend/data_ai: 252 pruebas y 21 subcasos aprobados; cinco pruebas OCI reales
excluidas. Web: diez aprobadas. Flutter: 178 aprobadas y una prueba HTTP real
optativa omitida; flutter analyze sin problemas.
Las pruebas nuevas recorren POST, Gemini simulado, orquestación real, copia OCI
simulada, persistencia y GET; cubren además fallo de copia con recepción disponible.
Las pruebas de transferencia verifican ETag, hashes y rechazo de cambios concurrentes.
No se ejecutaron llamadas reales a OCI, Gemini ni otro proveedor.

Siguen pendientes aceptación sintética real con IAM de copia/lectura correctos,
respuesta Gemini exitosa, cámara física y calibración/criterios documentales.
No se publica esta integración hasta una autorización de push.
