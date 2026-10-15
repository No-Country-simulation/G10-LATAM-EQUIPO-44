# Integración local de las ramas de Laura Eliana y Drazen

> Actualización tras pruebas reales: la recepción JSON ahora se guarda antes de Gemini y el historial web consulta el GET. Ver pruebas-integracion-real-14-octubre.md; las notas anteriores sobre ausencia de JSON tras fallo y mocks describen la revisión inicial.

Agregado por Edil: se conserva el trabajo local de Flutter, cámara, diseño, diagnósticos y BAT. Los aportes se incorporan por archivos y adaptaciones compatibles; no se crearon commits de merge ni se publicó esta integración.

## Procedencia

| Rama | Commit | Autor y entrega |
| --- | --- | --- |
| feature/validacion-salida-llm | f9003ad | Laura Paiva: siete casos de validación y documentación S2-02 |
| feature/contratoJSON | bcefff1 | Eliana Carta: justificacion_enrutamiento obligatorio en documentación |
| feature/S3-implementacion_get | 2d8bb03 | Drazen Gamboa: GET, persistencia JSON, primitivas OCI y pruebas S3 |

Laura reutiliza el validador de backend existente. Se conservan sus siete pruebas, sin crear un contrato paralelo.
El cambio de Eliana se aplica a detalleContrato.md conservando las aclaraciones existentes. No se reemplaza el JSON de ejemplo por el bucket antiguo de su rama.
Los archivos originales de rutas y cliente OCI de Drazen están conservados como texto en entregas-originales/drazen. Se normalizan solo espacios finales y saltos de línea; las versiones exactas siguen en su commit Git.

## Correcciones agregadas por Edil

1. POST guarda y valida el JSON. Si falla, devuelve 503 y X-Document-ID; no devuelve un 201 falso. Se conserva el archivo original.
2. Se conservan las categorías de diagnóstico existentes sin registrar documentos, claves o mensajes crudos del SDK.
3. Buscar en otro bucket solo después de un 404 del SDK. Un 403, fallo de red o JSON corrupto no se convierte en objeto ausente.
4. Listado OCI paginado con next_start_with/start y detección de marcadores repetidos.
5. Deduplificar y filtrar prioridad antes de aplicar el límite, sin recuperar una versión anterior para forzar coincidencia.
6. IDs seguros para objetos JSON, estados permitidos y comprobación de que la identidad del resultado corresponde al documento.
7. GET retorna error por JSON corrupto/incompatible, en lugar de fingir listado vacío o parcial correcto.
8. Flutter puede mostrar el mensaje controlado de fallo de persistencia JSON y conservar su código HTTP.

Se mantienen métodos públicos de Drazen. La ampliación prioridad en listar_resultados_triage es opcional. Los originales con except/pass quedan disponibles en las referencias; el código activo explica por qué no los usa.

## Lo que ahora existe

- POST /api/triage guarda JSON de recepción o análisis según el flujo solicitado.
- GET /api/documents con status, prioridad y limit.
- GET /api/documents/{document_id}.
- JSON recibido en recibidos, procesado en procesados, revisión en auditoria_humana.
- El archivo original permanece en recibidos: almacenamiento_oci describe ese archivo; no se afirma traslado automático.

## Verificación

Backend y Laura: 146 pruebas aprobadas, una prueba real OCI excluida. Dos avisos de deprecación de dependencias, sin fallos.
Flutter: 130 pruebas aprobadas; analyze sin problemas. Incluye cámara, consentimiento, diseño y diagnóstico de errores.
Web: cuatro pruebas aprobadas; sigue usando mocks, no se presenta como conectada.
Sin conflictos Git. Revisión de candidatos sin claves privadas ni patrones de tokens detectados; .env no se incorpora.
No se realizaron llamadas reales a OCI o Gemini.

## Estado y pendientes

Rama activa: feature/s3-edil-resultados. Main permanece en 7a4a28e5b728dae345ef8df94ef3d671b6b66df4.
Los cambios están locales, sin commit ni push. El stash anterior, worktrees y respaldos se conservan.
Respaldo previo: C:/Users/leno/AppData/Local/Temp/MediFlow-before-S3-branches-1a4993ab545e4153acf471da7303f4db.

S3-04B ya dispone de una implementación local para coordinar con Drazen una prueba real de escritura/lectura JSON. Sigue faltando esa evidencia, verificación IAM y aceptación de la integración.
No se implementa un endpoint de reprocesamiento idempotente. Si el análisis falla antes de guardar su JSON, el archivo recibido puede existir sin resultado consultable por GET. El reenvío sigue creando otro ID.
No se añade autenticación ni autorización por documento en los GET; no se declara apto para exposición pública de datos clínicos.
OCI puede devolver NotAuthorizedOrNotFound con 404; no permite demostrar por sí solo si faltaba el objeto o permiso. Validar IAM aparte.
Las pruebas de Laura no certifican exactitud clínica, calibración ni reglas de urgencia. El fallo de fotos informado previamente todavía requiere su causa concreta del backend.
