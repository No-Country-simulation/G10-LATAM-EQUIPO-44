> Agregado por Edil: integración del 16 de octubre. Se conserva la entrega original como referencia. El flujo activo usa Gemini con consentimiento, GET y JSON de recepción; verifica la copia y conserva el original. Cohere, la configuración paralela y las rutas manuales de movimiento describen la propuesta de la rama, no el API actual. Ver docs/sprint-3/integracion-ramas-16-octubre.md.

Integración LangGraph
Responsable: Eliana

Este documento detalla la integración del orquestador de reglas clínicas y de confianza (LangGraph) con el endpoint de triaje, respetando la arquitectura original.

Archivos Modificados / Creados
1. backend/app/api/routes.py (Modificación mínima)
Se realizó un cambio quirúrgico en el endpoint principal para interceptar el flujo sin alterar su estructura.

Cambio: Dentro del bloque try, en la llamada a run_in_threadpool, se reemplazó la función original por procesar_con_orquestador. Todo el manejo de errores y subidas iniciales a OCI se mantuvo intacto.

2. backend/app/services/servicio_orquestador.py (Nuevo)
Actúa como un wrapper (envoltorio) integrador para conectar el Sprint 2 con el Sprint 3.

Ejecuta la extracción original con Gemini.

Preserva el campo justificacion_enrutamiento original para evitar errores de validación estricta (ValidationError de Pydantic).

Inyecta el resultado en el pipeline de LangGraph y fusiona la decisión final del grafo antes de devolver el objeto oficial.

3. backend/app/core/orquestador.py (Finalizado)
Contiene la definición del grafo de LangGraph (pipeline_v1_2) y coordina las reglas de negocio:

Nodo de Urgencia: Se conectó la función evaluate_analysis. Para evitar que el sistema actúe "a ciegas" y fuerce auditorías innecesarias, se implementó el envío del texto extraído (source_text) como parámetro de contexto.

Nodo de Ambigüedad: Se integró la función evaluar_confianza_con_dosis con el umbral oficial del MVP (0.70). Se configuraron 4 criterios de completitud justos para evitar falsos positivos matemáticos en documentos válidos.

Nodo Orquestador: Coordina los resultados anteriores y toma la decisión final de enrutamiento. Asigna destinos dinámicos (como Cola_Revision_Humana, Cola_Farmacia o Cola_Emergencia_Medica) y genera una justificación descriptiva, garantizando que el backend separe los archivos en los buckets de Oracle Cloud (procesados vs auditoria_humana).
