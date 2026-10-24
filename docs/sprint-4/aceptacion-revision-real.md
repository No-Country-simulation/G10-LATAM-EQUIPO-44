# Aceptación de revisión humana con OCI real — Sprint 4

**Preparado por Edil: 24 de octubre de 2026. Estado: NO EJECUTADO.**

Esta es la prueba propuesta para cerrar la conexión frontend → API → OCI. No se han realizado las escrituras descritas. Falta configurar las cuentas concretas autorizadas como auditores y autorizar la ejecución de este caso. La aprobación del contrato no demuestra por sí sola que la persistencia real haya sido aceptada.

El caso usa dos análisis sintéticos preparados de antemano. No invoca Gemini ni prueba extracción, clasificación o seguridad clínica. Tampoco sustituye las pruebas del pipeline de triaje.

## 1. Alcance concreto

Identificador de ejecución propuesto: `20261024-E7A29C`. Antes de crear los objetos debe comprobarse que no existan. Si existe cualquiera, detener esta ejecución y preparar otro identificador; nunca sobrescribirlo para repetir una prueba.

| Caso | ID reservado para esta propuesta | Decisión |
|---|---|---|
| A | `DOC-SYNTHETIC-S4-20261024-E7A29C-APPROVE` | `aprobado` |
| B | `DOC-SYNTHETIC-S4-20261024-E7A29C-REJECT` | `rechazado` |

La prueba creará como máximo seis objetos nuevos, todos en `auditoria_humana`: dos análisis y cuatro registros de revisión. No borrará objetos, no modificará documentos existentes, no llamará a Gemini y no enviará documentos clínicos reales. Los IDs de revisión y las fechas serán generados por el backend.

## 2. Condiciones previas

1. Crear una cuenta propia de MediFlow con permiso de auditor usando el comando administrativo de [usuarios-mediflow.md](usuarios-mediflow.md). Tailscale se utiliza solo para el acceso de red; sus cuentas no autentican usuarios de la aplicación.
2. Verificar que el backend obtiene la identidad del proveedor configurado. El navegador no puede elegir libremente el `reviewer_id`. El campo enviado debe corresponder a la identidad autenticada y el backend debe guardar su identidad canónica.
3. Conservar Tailscale Serve para acceso privado y HTTPS, el servidor en loopback y la protección de origen de las escrituras. Iniciar sesión en MediFlow con su usuario/contraseña antes de revisar; una bandera no omite autenticación ni autorización.
4. Mantener las credenciales únicamente en el servidor. Se conserva la carga de `mediflow/.env`, `OCI_CONFIG_PROFILE` y los buckets `recibidos`, `procesados` y `auditoria_humana`.
5. Contar con permisos de listado y lectura en los tres buckets: la consulta de pendientes busca las versiones actuales y deduplica los resultados entre ellos. Para esta prueba solo se requiere escritura en `auditoria_humana`. No se necesita permiso de borrado.
6. Autorizar este caso concreto antes de precargar sus dos JSON. La cuenta de servicio OCI y la identidad del auditor son responsabilidades distintas.
7. Ejecutar primero las pruebas locales de autenticación, permisos, contrato y persistencia simulada. Los fallos de red, la escritura parcial y los intentos de suplantación se prueban localmente, sin provocar fallos deliberados en la nube.

## 3. Contrato HTTP que se verificará

Rutas existentes:

- `GET /api/reviews/pending`
- `GET /api/documents/{document_id}`
- `POST /api/documents/{document_id}/review`
- `GET /api/documents/{document_id}/review-history`

Solicitud de aprobación, exactamente con los campos del contrato vigente:

```json
{
  "decision": "aprobado",
  "reviewer_id": "<identidad autenticada del auditor>",
  "observacion": null,
  "expected_review_status": "pendiente"
}
```

Solicitud de rechazo:

```json
{
  "decision": "rechazado",
  "reviewer_id": "<identidad autenticada del auditor>",
  "observacion": "Caso sintético S4: información insuficiente para esta prueba de revisión.",
  "expected_review_status": "pendiente"
}
```

El documento se identifica en la ruta. El frontend no genera `review_id` ni `reviewed_at`. La observación puede ser `null` en una aprobación; en un rechazo debe contener texto.

Una respuesta HTTP 200 y el registro OCI contendrán **exactamente seis campos**:

```json
{
  "documento_id": "<ID del caso A o B>",
  "review_id": "<generado por backend>",
  "review_status": "<aprobado o rechazado>",
  "reviewer_id": "<identidad canónica autenticada>",
  "observacion": null,
  "reviewed_at": "<fecha ISO 8601 UTC terminada en Z>"
}
```

En el caso B, `observacion` será el texto de rechazo anterior. `expected_review_status` no se almacena en OCI. `persisted` es una señal interna del adaptador web después de validar la respuesta; no es un séptimo campo de la API.

## 4. Preparación de los análisis sintéticos

Después de obtener autorización, precargar dos JSON que cumplan `TriageResponse`. Esta preparación no utiliza `POST /api/triage`: los análisis se construyen como fixtures sintéticos y no representan una salida de Gemini.

Para ambos casos:

- `documento_id`: ID correspondiente de la tabla.
- `cargado_por`: identidad canónica de quien realiza la precarga, según la definición backend aprobada; no un médico ficticio ni un dato extraído por el LLM.
- `status`: `auditoria_humana`.
- `clasificacion.tipo_documento`: `Receta Médica`.
- `clasificacion.especialidad`: `null`.
- `clasificacion.nivel_prioridad`: `Urgente`, usada solo para comprobar que la revisión no la sobrescribe.
- `clasificacion.score_confianza_clasificacion`: `0.5`, valor sintético sin significado de exactitud clínica.
- `datos_extraidos.paciente`: nombre `Persona ficticia de prueba S4` y edad `null`.
- `datos_extraidos.medico_solicitante`: nombre y matrícula `null`.
- `datos_extraidos.estudio_realizado`, `diagnostico_principal` y `cie10_sugerido`: `null`.
- `datos_extraidos.medicamentos_recetados`: `[]`.
- `decision_enrutamiento.destino_principal`: `Cola_Revision_Humana`.
- `decision_enrutamiento.requiere_auditoria_humana`: `true`.
- `decision_enrutamiento.justificacion_enrutamiento`: `Fixture sintético S4 para verificar revisión humana, sin análisis LLM.`
- `notificacion_generada`: `null`.
- `almacenamiento_oci`: bucket `auditoria_humana`, ruta igual al nombre del JSON del caso y `status_backup` `exito`.

Validar cada JSON con el esquema del backend antes de escribirlo. La precarga deberá usar escritura condicional `if_none_match="*"`; `guardar_resultado_triage` no proporciona por sí solo esa protección contra sobrescritura. No se incluye aquí un script de escritura: su ejecución sigue pendiente de autorización.

Claves exactas previstas:

```text
auditoria_humana/
  DOC-SYNTHETIC-S4-20261024-E7A29C-APPROVE.json
  DOC-SYNTHETIC-S4-20261024-E7A29C-REJECT.json
  reviews/DOC-SYNTHETIC-S4-20261024-E7A29C-APPROVE/_final.json
  reviews/DOC-SYNTHETIC-S4-20261024-E7A29C-APPROVE/{review_id_A}.json
  reviews/DOC-SYNTHETIC-S4-20261024-E7A29C-REJECT/_final.json
  reviews/DOC-SYNTHETIC-S4-20261024-E7A29C-REJECT/{review_id_B}.json
```

Guardar localmente el SHA-256 de cada análisis precargado para comprobar después que no cambió. No crear un archivo clínico adicional: en este caso se prueba el panel de revisión de análisis JSON, no la descarga del documento original.

## 5. Ejecución manual reproducible

1. Conectar el equipo auditor a la red privada autorizada de Tailscale. Mantener encendido el PC que ejecuta la presentación.
2. Abrir `https://desktop-2amsjb6.tailf48a22.ts.net/web/auditoria/index.html`.
3. Confirmar que el panel muestra la identidad autenticada y que no permite editarla libremente. Si falta identidad o permiso, detener la prueba.
4. Filtrar por el prefijo `DOC-SYNTHETIC-S4-20261024-E7A29C`. No aprobar ni rechazar otros documentos de la bandeja.
5. Verificar que A y B están pendientes. Abrir cada detalle mediante GET real y comprobar ID, prioridad `Urgente`, confianza `0.5`, estado `auditoria_humana`, motivo sintético y `cargado_por`.
6. Consultar el historial inicial: debe devolver `[]` para ambos IDs.
7. En A, dejar observación vacía si la UI la transforma en `null`, seleccionar Aprobar y confirmar una sola vez. Esperar HTTP 200 y la confirmación visible.
8. Refrescar la bandeja: A debe desaparecer de pendientes. Consultar su historial y comprobar una única decisión `aprobado`.
9. En B, escribir la observación exacta del apartado 3, seleccionar Rechazar y confirmar una sola vez. Esperar HTTP 200.
10. Refrescar la bandeja: B también debe desaparecer. Su historial debe contener una única decisión `rechazado` y la observación indicada.
11. Verificar ambos historiales tras recargar completamente la página para demostrar que los registros vienen del backend, no únicamente del estado de la vista.
12. Para cada ID sintético, repetir una vez su mismo POST desde un cliente autenticado del mismo origen. Puede usarse la petición capturada en las herramientas del navegador. Debe responder HTTP 409 y conservar el registro anterior; no alterar el cuerpo para inventar otra identidad.
13. Volver a consultar GET individual: el análisis debe conservar prioridad `Urgente`, `cargado_por` y los demás datos anteriores. Aprobar o rechazar registra una decisión separada; no convierte automáticamente el `status` original a `procesado`.
14. Descargar y verificar por SDK los seis objetos según el apartado 6. No borrar los objetos como parte de esta ejecución.

`GET /api/documents?status=auditoria_humana` puede seguir mostrando A y B después de decidir: consulta el estado original del análisis. La exclusión que se acepta corresponde específicamente a `/api/reviews/pending`.

## 6. Verificación de solo lectura por SDK

Los comandos siguientes **no se han ejecutado**. Realizan lecturas OCI, no escrituras. Ejecutarlos únicamente dentro de la prueba autorizada, desde PowerShell:

```powershell
Set-Location -LiteralPath 'D:\Nocountru\mediflow\backend'
@'
import hashlib
import json
from app.core.environment import load_environment
load_environment()
from app.core.oci_client import OCIStorageManager, ReviewRecord

manager = OCIStorageManager()
bucket = manager.settings.bucket_auditoria
base = "DOC-SYNTHETIC-S4-20261024-E7A29C"
fields = {"documento_id", "review_id", "review_status", "reviewer_id", "observacion", "reviewed_at"}
for suffix, decision in [("APPROVE", "aprobado"), ("REJECT", "rechazado")]:
    doc_id = f"{base}-{suffix}"
    analysis_bytes = manager.obtener_objeto_bytes(bucket, f"{doc_id}.json")
    analysis = json.loads(analysis_bytes)
    assert analysis["documento_id"] == doc_id
    assert analysis["clasificacion"]["nivel_prioridad"] == "Urgente"
    final_bytes = manager.obtener_objeto_bytes(bucket, f"reviews/{doc_id}/_final.json")
    payload = json.loads(final_bytes)
    assert set(payload) == fields
    review = ReviewRecord.from_mapping(payload)
    assert review.documento_id == doc_id
    assert review.review_status == decision
    mirror_bytes = manager.obtener_objeto_bytes(bucket, f"reviews/{doc_id}/{review.review_id}.json")
    assert final_bytes == mirror_bytes
    history = manager.list_reviews_for_document(doc_id)
    assert len(history) == 1
    assert history[0].to_dict() == payload
    assert manager.get_latest_review_status(doc_id) == decision
    print(json.dumps({"documento_id": doc_id, "status": decision,
                      "analysis_sha256": hashlib.sha256(analysis_bytes).hexdigest(),
                      "review_sha256": hashlib.sha256(final_bytes).hexdigest(),
                      "mirror_matches": True, "history_count": len(history)}))
'@ | .\.venv\Scripts\python.exe -
```

Comparar `analysis_sha256` con el SHA-256 guardado **antes** de decidir. Verificar además que `payload["reviewer_id"]` coincide con la identidad canónica autorizada, sin copiar credenciales ni el contenido completo del registro a las evidencias públicas. La comprobación de exclusión de pendientes se realiza en el paso UI/HTTP anterior; no imprimir la respuesta completa de la bandeja.

## 7. Fallos y concurrencia

- Segundo POST: HTTP 409. El objeto `_final.json` utiliza `if_none_match="*"` y no debe sobrescribirse.
- Error de autenticación del auditor: HTTP 401. Usuario sin permiso o intento de suplantación: HTTP 403. Verificar estos escenarios primero con pruebas locales que confirmen que no hubo acceso OCI.
- Datos inválidos: HTTP 422; documento no disponible para revisión: HTTP 400; inexistente: HTTP 404. No usar objetos ajenos para provocar estos casos.
- Error de persistencia, permisos o credenciales OCI: HTTP 502; timeout OCI: HTTP 504. No es equivalente a un 401/403 del usuario auditor.
- Si se escribió `_final.json` pero falló el espejo, no hay reversión automática. No reenviar como si no existiera una decisión. Consultar historial, mantener bloqueada otra aprobación/rechazo y registrar el fallo. La prueba no se considera completamente aceptada hasta verificar final y espejo.
- El fallback del historial a `_final.json` evita perder la decisión cuando falta el espejo; no demuestra por sí mismo que ambas copias estén presentes.

## 8. Evidencia y criterio de cierre

Preparar un informe filtrado exclusivamente por los dos IDs sintéticos con:

- Fecha de ejecución, rama y commit base, y estado local relevante.
- Identificador de ejecución, códigos HTTP y resultados de cada paso.
- Dos decisiones, seis campos por registro, UTC-Z y correspondencia entre ID, clave y contenido.
- SHA-256 anterior y posterior de los análisis; SHA-256 del final y espejo.
- Exclusión de pendientes y HTTP 409 sin modificación de la decisión previa.
- Capturas limitadas a los casos sintéticos; sin otros documentos, claves, tokens, `.env`, OCID completos ni respuestas completas de la bandeja.
- Distinción explícita entre aceptación técnica de persistencia y validación clínica, que esta prueba no realiza.

**Estado actual de aceptación: pendiente.** No hay todavía resultados de esta ejecución ni cuentas de auditor aprobadas/configuradas para presentarla como terminada. La evidencia previa con almacenamiento en memoria debe mantenerse identificada como prueba local, separada de la futura evidencia OCI real.
