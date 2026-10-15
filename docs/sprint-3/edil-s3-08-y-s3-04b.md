# Sprint 3 — tareas de Edil

> Actualización del 14 de octubre: la entrega S3-04A de Drazen está incorporada localmente con correcciones y pruebas. La ejecución real y evidencia OCI siguen pendientes. Ver integracion-ramas-14-octubre.md; las notas de ausencia de implementación de abajo describen el estado anterior.

Agregado por Edil: este informe separa implementación local y aceptación con servicios reales. No atribuye a Edil la lógica clínica ni la persistencia pendiente de otros integrantes.

## S3-08 — resultado Flutter

| Subtarea | Implementación | Verificación pendiente |
| --- | --- | --- |
| S3-08.1 Revisar contrato | Revisado TriageResponse y POST /api/triage; prioridades Rutina/Urgente y estados recibido/procesado/auditoria_humana | Confirmación de Eliana de que este contrato es definitivo para Sprint 3 |
| S3-08.2 Modelo | Lectura de tipo, prioridad, destino, justificación y revisión; valida identidad, bloques mínimos, confianza y coherencia | Cambios posteriores del contrato deberán revisarse |
| S3-08.3 Servicio | Multipart real; analyze solo con consentimiento; rechaza JSON vacío, 204 y resultados incompletos | Prueba con backend real configurado |
| S3-08.4 Resultado | Vista reutilizable de resultado, recepción y revisión humana | Aceptación visual en dispositivo real |
| S3-08.5 Urgencia | Alerta con texto e icono cuando el servidor devuelve Urgente; también si requiere revisión humana | Eliana debe validar o integrar la política real de urgencia del backend |
| S3-08.6 Errores | Conserva errores seguros, timeout/cancelación y reintento; detecta contrato contradictorio | No muestra detalles privados del proveedor |
| S3-08.7 Flujo | Tests selección → envío — resultado y errores/reintento con transporte simulado | No confundir esos tests con llamadas reales |
| S3-08.8 Pruebas | Flutter test y analyze; resultados registrados al final | No sustituye la aceptación de punta a punta |

La app no deduce urgencia, no prescribe, no decide traslado de buckets y no envía notificaciones por su cuenta.
La recepción sin análisis no se presenta como resultado clínico terminado.

## S3-04B — persistencia JSON OCI

El endpoint actual sube bytes del documento a recibidos y retorna JSON. No encontramos un servicio que guarde el JSON del análisis y luego lo recupere como parte del flujo S3-04A.
El cliente OCI tiene primitivas de subir/descargar/mover, pero su existencia no prueba persistencia JSON del backend.

- S3-04.5: pendiente de implementación de Drazen, buckets accesibles y permisos de lectura/escritura. No se ejecutó la prueba real ni se generó evidencia ficticia.
- S3-04.6: procedimiento preparado en guia-verificacion-json-oci.md.

Dependencias concretas para pedir al equipo:
1. Drazen: commit de S3-04A, método o endpoint para guardar y recuperar análisis, bucket y convención de nombre, comportamiento ante fallo parcial y resultado esperado.
2. Eliana: confirmación del contrato final y de la validación/enrutamiento de Urgente; no basta con que Gemini produzca la palabra Urgente.
3. Cuenta OCI: perfil, buckets recibidos/procesados/auditoria_humana e IAM apropiado, configurados localmente sin subir secretos.
4. Backend/IA: servidor accesible, clave y modelo configurados, cuota disponible; documentos sintéticos para la aceptación.

No se modificaron módulos ajenos para sustituir esas dependencias.


## Resultados locales — 12 de octubre de 2026

- Flutter analyze --no-pub: sin problemas.
- Flutter test --no-pub: 99 pruebas aprobadas.
- git diff --check: sin errores de formato.
- Rama local: feature/s3-edil-resultados. Sin commit ni push de estas tareas.
- Se conservan main y el stash de los cambios anteriores; no se modifica backend ni credenciales.
- No se ejecutaron servicios Gemini/OCI reales ni se produjo evidencia ficticia.

Archivos de implementación: triage_result.dart, triage_api_service.dart, document_selection_screen.dart y nuevo widgets/triage_result_card.dart.
Pruebas: se conservan y adaptan triage_api_service_test.dart y triage_flow_test.dart; se agregan triage_result_s3_test.dart y helpers/triage_fixture.dart con datos sintéticos.
