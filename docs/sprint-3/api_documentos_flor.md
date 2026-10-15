# MediFlow — Documentación de Endpoints GET para Frontend Web (Flor) 📄✨

**Autor:** Drazen Gamboa | Backend Developer
**Sprint:** 3 (Tareas S3-03 y S3-04A)
**Destinataria:** Flor (Célula Frontend Web)
**Fecha:** Octubre 2026

---

## 📌 1. Panorama General

Para el Sprint 3 se habilitaron los endpoints de consulta y listado de documentos persistidos en **Oracle Cloud Infrastructure (OCI Object Storage)**.

Cada vez que un documento ingresa por `POST /api/triage` (ya sea en estado `recibido` o procesado por IA con `analyze=true` en estados `procesado` o `auditoria_humana`), su resultado completo se almacena como un archivo `{documento_id}.json` en el bucket correspondiente a su estado:
* `recibidos`: Documentos ingresados pendientes de análisis IA.
* `procesados`: Documentos analizados con éxito y sin banderas de riesgo.
* `auditoria_humana`: Documentos que requieren revisión médica o con datos incompletos/ilegibles.

Los endpoints GET permiten listar todos estos documentos y consultar el detalle de un documento específico mediante su `documento_id`.

---

## 🚀 2. Endpoints Disponibles

### A. Listar Documentos: `GET /api/documents`

Obtiene la lista de documentos clínicos persistidos.

* **URL:** `http://localhost:8000/api/documents`
* **Método:** `GET`
* **Parámetros de consulta (Query Params - Opcionales):**
  * `status`: Filtra por estado del ciclo de vida. Valores permitidos: `"recibido"`, `"procesado"`, `"auditoria_humana"`.
  * `prioridad`: Filtra por prioridad clínica. Valores permitidos: `"Rutina"`, `"Urgente"`.
  * `limit`: Cantidad máxima de registros a devolver (por defecto `100`, mín `1`, máx `500`).

#### Ejemplos de URLs con filtros:
* Todos los documentos: `GET /api/documents`
* Solo los que requieren auditoría: `GET /api/documents?status=auditoria_humana`
* Solo urgencias procesadas: `GET /api/documents?status=procesado&prioridad=Urgente`

#### Códigos de Respuesta HTTP:
* **`200 OK`**: Retorna un arreglo JSON con los documentos (o `[]` si no hay coincidencias).
* **`500 Internal Server Error`**: Ocurrió un error al contactar OCI Object Storage.

---

### B. Consultar Documento por ID: `GET /api/documents/{document_id}`

Obtiene el detalle completo y resultado de triaje de un documento específico.

* **URL:** `http://localhost:8000/api/documents/{document_id}`
* **Método:** `GET`
* **Ejemplo:** `http://localhost:8000/api/documents/DOC-CLIN-A1B2C3D4`

#### Códigos de Respuesta HTTP:
* **`200 OK`**: Retorna el objeto JSON del documento solicitado.
* **`400 Bad Request`**: El identificador contiene caracteres no permitidos (ej. `..`, `/`, `\`).
* **`404 Not Found`**: El documento no existe en ninguno de los buckets de OCI (`{"detail": "Documento 'DOC-XYZ' no encontrado."}`).
* **`502 Bad Gateway`**: El JSON recuperado de OCI está corrupto o no cumple el contrato oficial.
* **`500 Internal Server Error`**: Error de comunicación con OCI.

---

## 📋 3. Estructura y Ejemplos del Contrato JSON (`TriageResponse`)

El modelo devuelto por la API es 100% compatible con el contrato oficial definido en `app/models/schemas.py` y `app/core/contrato.json`.

### Ejemplo 1: Documento Procesado (`procesado` / `Rutina`)
```json
{
  "status": "procesado",
  "documento_id": "DOC-CLIN-89F1A2BC",
  "clasificacion": {
    "tipo_documento": "Receta médica",
    "especialidad": "General",
    "nivel_prioridad": "Rutina",
    "score_confianza_clasificacion": 0.95
  },
  "datos_extraidos": {
    "paciente": {
      "nombre": "Carlos Gómez",
      "edad": 52
    },
    "medico_solicitante": {
      "nombre": "Dr. Fernando Morales",
      "matricula": "MN-45892"
    },
    "estudio_realizado": null,
    "diagnostico_principal": "Hipertensión arterial estadio 1",
    "cie10_sugerido": "I10",
    "medicamentos_recetados": [
      {
        "medicamento": "Enalapril",
        "dosis": "10 mg cada 12 horas"
      }
    ]
  },
  "decision_enrutamiento": {
    "destino_principal": "Cola_Farmacia",
    "requiere_auditoria_humana": false,
    "justificacion_enrutamiento": "Receta rutinaria clara y legible, derivada a farmacia."
  },
  "notificacion_generada": null,
  "almacenamiento_oci": {
    "bucket": "procesados",
    "ruta_objeto": "DOC-CLIN-89F1A2BC.pdf",
    "status_backup": "exito"
  }
}
```

### Ejemplo 2: Documento en Auditoría Humana (`auditoria_humana` / `Urgente`)
```json
{
  "status": "auditoria_humana",
  "documento_id": "DOC-CLIN-33B7E9F1",
  "clasificacion": {
    "tipo_documento": "Informe de laboratorio",
    "especialidad": "Cardiología",
    "nivel_prioridad": "Urgente",
    "score_confianza_clasificacion": 0.45
  },
  "datos_extraidos": {
    "paciente": {
      "nombre": "María Rodríguez",
      "edad": 68
    },
    "medico_solicitante": {
      "nombre": null,
      "matricula": null
    },
    "estudio_realizado": "Troponina T ultrasensible y ECG",
    "diagnostico_principal": "Sospecha de síndrome coronario agudo",
    "cie10_sugerido": "I21.9",
    "medicamentos_recetados": []
  },
  "decision_enrutamiento": {
    "destino_principal": "Cola_Revision_Humana",
    "requiere_auditoria_humana": true,
    "justificacion_enrutamiento": "Troponina elevada y firma médica ambigua. Requiere revisión urgente por especialista."
  },
  "notificacion_generada": {
    "canal": "Alerta_Medica_Guardia",
    "mensaje": "Paciente crítico requiere confirmación clínica inmediata."
  },
  "almacenamiento_oci": {
    "bucket": "auditoria_humana",
    "ruta_objeto": "DOC-CLIN-33B7E9F1.pdf",
    "status_backup": "exito"
  }
}
```

### Ejemplo 3: Documento Solo Recibido (`recibido` / pendiente)
```json
{
  "status": "recibido",
  "documento_id": "DOC-CLIN-55AA88CC",
  "clasificacion": {
    "tipo_documento": "Pendiente de procesamiento",
    "especialidad": "General",
    "nivel_prioridad": "Rutina",
    "score_confianza_clasificacion": 0.0
  },
  "datos_extraidos": {
    "paciente": {
      "nombre": null,
      "edad": null
    },
    "medico_solicitante": {
      "nombre": null,
      "matricula": null
    },
    "estudio_realizado": null,
    "diagnostico_principal": null,
    "cie10_sugerido": null,
    "medicamentos_recetados": []
  },
  "decision_enrutamiento": {
    "destino_principal": "Cola_Procesamiento_Inicial",
    "requiere_auditoria_humana": false,
    "justificacion_enrutamiento": "Archivo almacenado en 'recibidos/DOC-CLIN-55AA88CC.pdf'"
  },
  "notificacion_generada": null,
  "almacenamiento_oci": {
    "bucket": "recibidos",
    "ruta_objeto": "DOC-CLIN-55AA88CC.pdf",
    "status_backup": "exito"
  }
}
```

---

## 💻 4. Guía de Conexión en JavaScript para `frontend_web`

Actualmente tu código en `mediflow/frontend_web/src/historial/app.js` utilizaba:
```javascript
const records = window.MediFlowDocuments.documents.map(window.MediFlowDocuments.toRow);
```

### Cómo reemplazarlo por la API en vivo manteniendo compatibilidad:

Dado que cada elemento devuelto por `GET /api/documents` coincide exactamente con el contrato `TriageResponse`, podés conectarlo de forma directa manteniendo la función `window.MediFlowDocuments.toRow(doc)` que ya tenías programada:

```javascript
// URL base de la API FastAPI
const API_BASE = "http://localhost:8000/api";

async function cargarDocumentosDesdeAPI() {
  try {
    const response = await fetch(`${API_BASE}/documents`);
    if (!response.ok) {
      throw new Error(`Error en el servidor: HTTP ${response.status}`);
    }
    const docs = await response.json();

    // Transformar los documentos del backend a filas para la tabla
    const records = docs.map(window.MediFlowDocuments.toRow);

    // Si la lista está vacía, la tabla mostrará el estado vacío existente
    return records;
  } catch (error) {
    console.error("Error al cargar documentos:", error);
    toast("No se pudo conectar con el servidor de documentos.", "rojo");
    return [];
  }
}
```

### Para la pantalla de detalle / auditoría (`GET /api/documents/{id}`):
```javascript
async function obtenerDetalleDocumento(docId) {
  try {
    const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(docId)}`);
    if (response.status === 404) {
      toast(`El documento ${docId} no fue encontrado.`, "naranja");
      return null;
    }
    if (!response.ok) {
      throw new Error(`Error HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Error al consultar documento:", error);
    toast("Error al recuperar el documento.", "rojo");
    return null;
  }
}
```

---

## 🛠️ 5. Probar con Swagger UI o Postman

* **Swagger UI:** Abrí [http://localhost:8000/docs](http://localhost:8000/docs) en tu navegador.
  * Buscá la sección **Triage**.
  * Desplegá `GET /api/documents` y hacé click en **"Try it out"** ➔ **"Execute"**.
  * Desplegá `GET /api/documents/{document_id}`, ingresá un ID (ej. `DOC-DEMO-001` o cualquier ID obtenido) y ejecutá.
* **CORS:** FastAPI ya tiene habilitado `CORSMiddleware` con `allow_origins=["*"]`, por lo que podés realizar peticiones `fetch()` directamente desde el frontend sirviendo en `http://localhost:8080` sin problemas de CORS.


## Agregado por Edil: correcciones al integrar S3
POST requiere guardar el JSON; un fallo devuelve 503 y X-Document-ID, conservando el original recibido.
GET no transforma errores de red/permisos en 404 o listas vacías. Los JSON corruptos o incompatibles devuelven 502.
La prioridad se filtra antes de aplicar limit y el SDK recorre todas las páginas.
El JSON se guarda en el bucket según estado; el documento original permanece en recibidos. Los metadatos almacenamiento_oci describen el original, no prometen que este fue movido.
El SDK puede responder 404 NotAuthorizedOrNotFound: no es posible demostrar permisos solo con ese código. IAM debe comprobarse aparte.
La web no se conecta automáticamente: Flor debe reemplazar su fuente mock por estos endpoints con manejo de estados/errores.
