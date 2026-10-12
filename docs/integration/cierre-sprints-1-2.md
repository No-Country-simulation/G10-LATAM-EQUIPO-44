# Cierre técnico de integración Sprints 1 y 2

## Agregado por Edil y motivo

Se prepara la integración local manteniendo las entregas originales y su historial. La aceptación real de servicios externos sigue pendiente.
Los bloques nuevos llevan comentarios Agregado por Edil. Los archivos JSON
no reciben comentarios inválidos; sus ampliaciones se atribuyen en detalleContrato.md.

| Entrega original | Ampliación de Edil |
| --- | --- |
| Cliente OCI de Eliana | Prueba faltante de subida local; cliente original conservado |
| Contrato de Eliana | Medicamentos/dosis opcionales y catálogo compatible documentado |
| Matriz de Laura | Estados comunes y validación estricta de salida LLM |
| API de Drazen | Opción analyze y servicio pipeline; respuesta original conservada |
| Tarea LLM de Nicolás | Cliente Gemini, prompt, TXT/PDF y envío multimodal, errores y tests |
| Manejo de errores de Brando | Se conserva; se añade conexión IA/API y mapeo HTTP controlado |
| Web y wireframes de Flor | Se conservan; mocks usan contrato con medicamentos opcionales |
| Flutter de Edil | Consentimiento por archivo, análisis y resultado básico, Android/Windows |

## Flujo implementado

Archivo -> POST /api/triage -> OCI recibidos.
- Sin analyze: respuesta original recibido.
- Con analyze=true: texto o media nativa -> Gemini -> validación -> JSON.
La app exige permiso por documento para activar analyze; no viene marcado.
No se presenta un mock como llamada real. Los tests simulan los transportes.
Los errores conservan el archivo ya recibido y no exponen mensajes del proveedor.

## Límites para la entrega

No se ha probado contra Gemini ni OCI reales en esta tarea.
El código multimodal está preparado, no certificado con el modelo de la cuenta.
No hay OCR local ni extracción clínica garantizada. Revisión/calidad requieren
evidencia real y pruebas humanas con datos sintéticos.
Score calibrado, movimientos automáticos, GET y auditoría conectada pertenecen
al Sprint 3. Los tres buckets se mantienen: recibidos, procesados, auditoria_humana.
Credenciales, configuraciones personales, main y entregas originales no se borran.
No se ha realizado commit ni push de estas ampliaciones.

## Aceptación pendiente de servicios externos

1. Elegir un modelo disponible y compatible, y verificar precios/cuotas.
2. Configurar claves localmente, sin compartirlas ni subirlas al repositorio.
3. Autorizar y ejecutar una prueba con documentos exclusivamente sintéticos.
4. Verificar en OCI el objeto recibido y conservar respuesta JSON anonimizada.
5. Evaluar extracción fiel para casos normal, urgente y ambiguo.
Solo esa evidencia permite declarar el Sprint 2 verificado de punta a punta.


## Reintegración de Eliana y Nicolás — 12 de octubre de 2026

Agregado por Edil: esta actualización conserva lo útil y explica lo incompatible en lenguaje simple.

| Autor y commit | Qué conservamos | Qué ajustamos y por qué |
| --- | --- | --- |
| Eliana, 0cc8424 | Contrato y explicación de estados, prioridades y medicamentos | Adoptamos medicamentos_recetados/medicamento/dosis; dejamos de usar los nombres provisionales de Edil. El bucket de ejemplo se cambia a recibidos para respetar la arquitectura oficial. |
| Eliana, 2bf041f | Guía de conexión OCI completa | Añadimos una nota al principio: rutas reales, mediflow/.env, perfil OCI y tres buckets. Sus ejemplos antiguos quedan identificados como históricos. |
| Nicolás, rama Sprint-2-Nico hasta 21634c9 | Prompt, esquema, reglas sintéticas y lógica útil de consistencia | El cliente seguro permanece activo. Corregimos la intención de su comprobación de dosis ilegible sin buscar la clave inexistente datos_extraidos encampados. |

No hacemos un merge ciego de esas ramas: incorporamos archivos y adaptaciones compatibles. Sus commits originales no se han agregado como padres de un merge; la procedencia queda documentada aquí y en las copias originales.
El script original de Nicolás queda guardado como texto, no ejecutado. Evitamos duplicar clientes, configuración y validación del backend.
El esquema de Nicolás incluye status; el cliente reutilizable lo calcula en backend. Las pruebas comprueban los mismos campos clínicos y prioridades.
Las reglas médicas son experimentales del dataset, no criterios asistenciales aprobados; se conservan pero no se aplican automáticamente a documentos generales.
El catálogo actualizado solo admite Rutina/Urgente. Pendiente puede describir el procesamiento, pero no se devuelve como prioridad.
Los comentarios del código activo indican Agregado por Edil y el motivo. Los JSON no admiten comentarios: la explicación se deja en detalleContrato.md.

## Verificación local final

- Backend: 111 pruebas aprobadas, 1 prueba real OCI excluida. Dos avisos de deprecación de dependencias, sin fallos.
- Frontend web: 4 pruebas aprobadas; sus 4 documentos mock también validan contra el contrato Pydantic actualizado.
- Flutter analyze: sin problemas.
- Flutter test: 86 pruebas aprobadas.
- No hubo llamadas reales a Gemini, OCI ni documentos clínicos enviados en esta revisión.
- No hay conflictos Git pendientes. Main permanece en 6c1357d28523ebc9117fee742157e9bc7c9c6496.
- Revisión de archivos candidatos: sin archivos .env, claves privadas o tokens detectados. Una coincidencia del escáner corresponde al texto ficticio unit-private-content-not-for-output de una prueba de sanitización, no a una credencial.
- Respaldo previo: C:/Users/leno/AppData/Local/Temp/MediFlow-before-Nico-Eliana-22d6b52c5d3647c494bf91c68340389d.

## Pendientes que no se presentan como resueltos

La prueba sintética real está autorizada previamente, pero sigue sin ejecutarse: falta confirmar configuración local de Gemini y el modelo/cuota.
Se necesitan resultados reales para evaluar calidad de extracción y cumplimiento de reglas, además de validar políticas clínicas con Laura.
No se certifica OCR ni calibración de confianza. El flujo de Brando está probado con proveedores simulados; eso no demuestra integración real en la cuenta OCI/Gemini.
No se hizo commit ni push. Este estado está preparado para un commit local de integración técnica, sin afirmar validación real de punta a punta.
