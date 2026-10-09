# MediFlow Backend 🏥⚡

Backend REST API con FastAPI e integración con Oracle Cloud Infrastructure (OCI) para triaje médico inteligente.

---

## 🚀 Requisitos Previos

- Python 3.10 o superior (validado en 3.12 y 3.14).
- Perfil del SDK OCI en `~/.oci/config` con acceso a los buckets `recibidos`, `procesados` y `auditoria_humana`.

Instalar dependencias del proyecto:
```bash
pip install -r mediflow/requirements.txt
```

---

## ⚙️ Variables de Entorno

Al iniciar, el backend carga `mediflow/.env` mediante `python-dotenv`, con una
ruta relativa al código, independiente de la carpeta desde la que ejecutes Uvicorn.
Las variables exportadas en la terminal tienen prioridad y no se sobrescriben.
Puedes copiar `mediflow/.env.example` a `mediflow/.env`; está ignorado por Git.
No se busca un segundo `.env` en `mediflow/backend/`.
Por defecto usa el perfil local `DEFAULT` del SDK; no copies credenciales al repositorio.

| Variable | Descripción | Valor por defecto |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Entorno de ejecución (`development` / `production`) | `development` |
| `PORT` | Puerto del servidor FastAPI | `8000` |
| `HOST` | Dirección de escucha | `0.0.0.0` |
| `OCI_CONFIG_PROFILE` | Perfil local del SDK | `DEFAULT` |
| `OCI_BUCKET_RECIBIDOS` | Bucket de ingesta | `recibidos` |
| `OCI_BUCKET_AUDITORIA` | Bucket para revisión | `auditoria_humana` |
| `OCI_BUCKET_PROCESADOS` | Bucket para documentos completados | `procesados` |

---

## 🏃 Cómo Ejecutar el Servidor

Desde la carpeta `mediflow/backend`:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

O desde la raíz del repositorio:
```bash
python -m uvicorn app.main:app --app-dir mediflow/backend --reload --port 8000
```

- **API Base:** [http://localhost:8000](http://localhost:8000)
- **Documentación Interactiva (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentación Redoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📬 Endpoint de Triaje: `POST /api/triage`

Recibe PDF, JPG/JPEG, PNG o TXT vía `multipart/form-data`, rechaza archivos
vacíos o mayores de 10 MiB y genera un identificador UUID completo.
La validación inicial revisa extensión y tamaño; todavía no analiza el contenido
para comprobar que corresponde al formato declarado.
Guarda el archivo en el bucket independiente `recibidos` y retorna JSON con estado
`recibido`. No llama al LLM: los campos clínicos son pendientes, no inferencias.

### Ejemplo con cURL

```bash
curl -X POST "http://localhost:8000/api/triage" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@ruta/a/tu/receta_medica.pdf"
```

### Ejemplo de Solicitud en Postman

1. **Método:** `POST`
2. **URL:** `http://localhost:8000/api/triage`
3. **Pestaña Body:** Seleccionar `form-data`
4. **Campo:**
   - Key: `file` (cambiar el selector de tipo de `Text` a `File`)
   - Value: Seleccionar el archivo local (ej. receta o estudio)
5. **Enviar (Send)**

### Ejemplo de Respuesta Exitosa (`201 Created`):

```json
{
  "status": "recibido",
  "documento_id": "DOC-CLIN-2026-E4A2",
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
    "cie10_sugerido": null
  },
  "decision_enrutamiento": {
    "destino_principal": "Cola_Procesamiento_Inicial",
    "requiere_auditoria_humana": false,
    "justificacion_enrutamiento": "Archivo almacenado en recibidos/"
  },
  "notificacion_generada": null,
  "almacenamiento_oci": {
    "bucket": "recibidos",
    "ruta_objeto": "DOC-CLIN-<uuid>.pdf",
    "status_backup": "exito"
  }
}
```

---

## 🧪 Ejecución de Pruebas

### 1. Pruebas Unitarias de Manejo de Errores OCI (Sin conexión OCI requerida, con Mocks):
```bash
cd mediflow/backend
python -m pytest tests -m "not integration" -v
```

### 2. Pruebas de Integración con OCI (Requiere credenciales en `~/.oci/config`):
```bash
# PowerShell, desde mediflow/backend; crea y elimina solo un objeto único.
$env:RUN_OCI_INTEGRATION = '1'
try {
    python -m pytest tests/test_oci_integration.py -v -s
} finally {
    Remove-Item Env:RUN_OCI_INTEGRATION -ErrorAction SilentlyContinue
}
```

La prueba real se omite por defecto. Para detalles, permisos y resultado esperado,
consulta [la documentación Sprint 1](../../docs/sprint-1/manejo_errores_oci.md).

## Flutter

El emulador Android consume `http://10.0.2.2:8000/api/triage` por defecto.
Inicia la API y el emulador antes de ejecutar Flutter. La selección local de archivos
puede usarse sin backend; procesar el documento requiere API y acceso OCI.

## Opciones del servidor

ENVIRONMENT se valida como texto y se muestra en el health check.
DEBUG se valida como booleano; por defecto es False y debe permanecer
desactivado en despliegue. Estas mejoras proceden de c839a90 y se alojan
en environment.py para no duplicar la carga de configuración.
Al usar Uvicorn CLI, HOST y PORT no se aplican automáticamente:
indica --host y --port al iniciar el servidor.


Compatibilidad Windows: si otra herramienta exporta DEBUG=release, se interpreta
como depuración desactivada. Valores distintos que no sean booleanos válidos
producen un error de configuración al iniciar.
