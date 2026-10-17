# Correcciones de Flutter — Edil — Sprint 3

Agregado por Edil: implementación local para cerrar los pendientes de la app.
Este informe no declara terminadas las tareas de IA, orquestación ni auditoría web.

## Alcance de la entrega S3-08

| Subtarea | Estado técnico |
| --- | --- |
| S3-08.1 Revisar contrato real | Conservado TriageResponse; no hay campos ni rutas nuevas de backend. |
| S3-08.2 Modelo de respuesta | Conserva validación de identidad, estados, prioridad y coherencia de revisión. El GET exige el mismo ID solicitado. |
| S3-08.3 Servicio HTTP | POST existente y GET de seguimiento real implementado; timeout/cancelación, IDs seguros y mensajes controlados. |
| S3-08.4 Pantalla de éxito | Distingue recibido, extracción completada y auditoría; conserva el resultado si falla una actualización. |
| S3-08.5 Alerta urgente | Sigue mostrando solo la prioridad recibida del backend como provisional, incluso si requiere auditoría. |
| S3-08.6 Errores | Conserva X-Document-ID tras fallo o cuerpo interrumpido; no ofrece otro POST si hay ID; confirma antes de reenvíos inciertos sin ID. |
| S3-08.7 Flujo | Pruebas selección → POST → error con ID → GET, actualización posterior y reintento confirmado. Transporte simulado. |
| S3-08.8 Pruebas | flutter analyze y flutter test; resultados registrados al finalizar esta revisión. |

## Motivo de las correcciones

- Antes, Reintentar repetía POST aunque el backend ya hubiera recibido el archivo.
  Ahora se consulta el ID cuando está disponible y se explica el riesgo si no lo está.
- Antes, no había consulta desde la app; ahora se usa el GET ya implementado por
  Drazen y adaptado en la integración. Consultar no es reprocesar.
- Antes, el selector aceptaba archivos vacíos y no limitaba su tamaño. Ahora
  valida antes de leer/enviar y verifica los bytes reales cuando no hay ruta.
- Antes, un resultado confirmado solo se mostraba al finalizar el POST. Ahora
  permanece visible cuando una actualización GET falla, junto al aviso del fallo.

Las condiciones y llamadas anteriores relevantes se conservan en comentarios,
con explicaciones Agregado por Edil. No se cambió backend, web ni credenciales.

## Verificación local

Desde mediflow/frontend_mobile/mediflow_app:

    flutter analyze --no-pub
    flutter test --no-pub

Las pruebas no llaman OCI ni Gemini y usan únicamente datos ficticios. Verifican
el HTTP simulado, no la disponibilidad de servicios ni la cámara de un dispositivo.

Resultado final del 15 de octubre: flutter analyze sin problemas; flutter test
con 162 aprobadas y una prueba HTTP real optativa omitida. Se agregaron casos
para IDs inválidos o distintos, cuerpo interrumpido, error de transporte tras
cabeceras, HTTP 408, confirmación de reenvío y tamaños reales de archivo.
git diff --check sin errores. Revisión de archivos nuevos/modificados sin patrones
de claves privadas o tokens detectados. Sin commit ni push de estas correcciones.

## Aceptación manual pendiente

1. Iniciar backend y app; seleccionar un TXT sintético y enviar sin consentimiento
   de Gemini. Confirmar recibido y actualizar estado sin crear otro documento.
2. Con datos sintéticos y servicios autorizados/configurados, comprobar éxito de
   análisis, urgencia y auditoría según respuestas reales del backend.
3. En Android físico: tomar foto, repetir/cancelar/confirmar, revisar orientación
   y comprobar que confirmar no envía ni activa el consentimiento.
4. Probar archivo vacío y mayor de 10 MiB en Android y Windows.

No se ejecutó una compilación de distribución ni una prueba de cámara física
en esta corrección. No se certifica una respuesta Gemini exitosa ni precisión clínica.

## Dependencias ajenas al frontend

- Conectar detector y score al pipeline y acordar criterios/umbral por tipo.
- Implementar reprocesamiento/idempotencia si se requiere reanálisis del mismo ID.
- Implementar revisión humana persistida y autorización por documento.
- Gemini disponible para la aceptación integral; el fallo 503 anterior no se
  considera solucionado por pasar pruebas con transporte simulado.

S3-04B: existe evidencia real de escritura/lectura JSON sintético en los tres
buckets del 14 de octubre, en pruebas-integracion-real-14-octubre.md. No se
repitió aquí y no equivale a guardar un análisis real exitoso de Gemini.

La implementación Flutter puede revisarse como entrega técnica; el cierre de
aceptación de punta a punta queda pendiente de las comprobaciones anteriores.
