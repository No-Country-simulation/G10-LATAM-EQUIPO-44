# MediFlow Backend 🏥⚡

Backend REST API con FastAPI e integración con Oracle Cloud Infrastructure (OCI) para triaje médico inteligente.

---

## 🚀 Requisitos Previos

- Python 3.10 o superior (validado en 3.12 y 3.14).
- Cuenta y CLI de OCI configurada en `~/.oci/config` con acceso a los buckets de Object Storage.

Instalar dependencias del proyecto:
```bash
pip install -r mediflow/requirements.txt
```

---

## ⚙️ Variables de Entorno y Conexión OCI

La configuración del sistema se gestiona de forma centralizada con `pydantic-settings` en `app/core/config.py`.

Puedes crear un archivo `.env` en `mediflow/` o en la raíz del repositorio basándote en `mediflow/.env.example`.

### Estrategia de Autenticación con OCI:
1. **Vía variables de entorno (`.env`):** Ideal para despliegues, CI/CD y entornos en contenedor. Si defines `OCI_USER_OCID`, `OCI_FINGERPRINT`, `OCI_KEY_FILE`, `OCI_TENANCY_OCID` y `OCI_REGION` en el archivo `.env`, el backend se autentica directamente con esas credenciales.
2. **Vía archivo local `~/.oci/config` (Fallback):** Si no defines las credenciales en el `.env`, el gestor utiliza automáticamente tu perfil local de OCI CLI (`DEFAULT`), garantizando retrocompatibilidad con entornos de desarrollo locales.

| Variable | Descripción | Valor por defecto |
| :--- | :--- | :--- |
| `ENVIRONMENT` | Entorno de ejecución (`development` / `production`) | `development` |
| `PORT` | Puerto del servidor FastAPI | `8000` |
| `HOST` | Dirección de escucha | `0.0.0.0` |
| `DEBUG` | Modo depuración | `True` |
| `OCI_USER_OCID` | OCID del usuario en OCI | `None` (Usa fallback a `~/.oci/config`) |
| `OCI_FINGERPRINT` | Huella digital (fingerprint) de la clave API | `None` |
| `OCI_KEY_FILE` | Ruta absoluta o con `~` a la clave privada `.pem` | `None` |
| `OCI_TENANCY_OCID` | OCID del Tenancy en OCI | `None` |
| `OCI_REGION` | Región de OCI (ej. `us-ashburn-1`) | `None` |
| `OCI_NAMESPACE` | Namespace del Tenancy en OCI | Opcional (Se resuelve dinámicamente si no se define) |
| `OCI_BUCKET_RECIBIDOS` | Bucket de ingesta de documentos | `recibidos` |
| `OCI_BUCKET_AUDITORIA` | Bucket para documentos en revisión | `auditoria_humana` |
| `OCI_BUCKET_PROCESADOS` | Bucket para documentos completados | `procesados` |
| `DATABASE_URL` | Cadena de conexión a base de datos | `sqlite:///./mediflow.db` |

---

## 🏃 Cómo Ejecutar el Servidor

Desde la carpeta `mediflow/backend`:
```bash
python -m uvicorn app.main:app --reload --port 8000
```

O desde la raíz del repositorio:
```bash
python -m uvicorn mediflow.backend.app.main:app --reload --port 8000
```

- **API Base:** [http://localhost:8000](http://localhost:8000)
- **Documentación Interactiva (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Documentación Redoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📬 Endpoint de Triaje: `POST /api/triage`

Recibe un documento clínico (PDF, JPG, PNG, TXT) vía `multipart/form-data`, genera un identificador único estandarizado (`DOC-CLIN-2026-XXXX`), lo persiste directamente en el bucket `recibidos` de OCI y retorna el contrato JSON oficial con estado `recibido`.

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
    "justificacion_enrutamiento": "Archivo subido correctamente al bucket 'recibidos'"
  },
  "notificacion_generada": null,
  "almacenamiento_oci": {
    "bucket": "recibidos",
    "ruta_objeto": "DOC-CLIN-2026-E4A2_receta_medica.pdf",
    "status_backup": "exito"
  }
}
```

---

## 🧪 Ejecución de Pruebas

### 1. Pruebas Unitarias de Manejo de Errores OCI (Sin conexión OCI requerida, con Mocks):
```bash
python mediflow/backend/tests/test_oci_error_handler.py
```

### 2. Pruebas de Integración con OCI (Requiere credenciales en `~/.oci/config`):
```bash
python mediflow/backend/tests/test_oci_integration.py
```
