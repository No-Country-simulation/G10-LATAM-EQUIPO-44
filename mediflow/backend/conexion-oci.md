# Conexión OCI vigente — Sprint 3

Actualizado el 17-10-2026. El backend utiliza tres buckets independientes:

```dotenv
OCI_BUCKET_RECIBIDOS=recibidos
OCI_BUCKET_PROCESADOS=procesados
OCI_BUCKET_AUDITORIA=auditoria_humana
```

`OCI_BUCKET_NAME` y `gestor.bucket_name` del ejemplo histórico no describen la
configuración vigente. Se usa `gestor.settings.bucket_recibidos` y sus pares.
Se carga `mediflow/.env`, sin depender del directorio de ejecución.

Autenticación: elegir perfil SDK (`OCI_CONFIG_FILE` opcional,
`OCI_CONFIG_PROFILE=DEFAULT`) o las cinco variables explícitas
`OCI_USER_OCID`, `OCI_FINGERPRINT`, `OCI_KEY_FILE`, `OCI_TENANCY_OCID`, `OCI_REGION`.
El cliente exige las cinco si aparece alguna de ellas; no mezclar una región
aislada con un perfil completo. En modo perfil, la región proviene del archivo
SDK. `OCI_NAMESPACE` es opcional; en su ausencia se obtiene por el SDK.
No publicar valores de credenciales ni el contenido del perfil.

La copia activa utiliza CopyObject nativo con verificación de tamaño/SHA-256
y versiones condicionadas por ETag, conservando el origen. La autorización del
servicio regional de copia es adicional a los permisos del usuario. Consulte
el [cierre S3-03/S3-04A/S3-06](../../docs/sprint-3/cierre-drazen-brando-sprint-3-17-octubre.md) para las operaciones,
permisos, pruebas y comandos reproducibles. No se requieren cambios IAM para las
dos muestras verificadas hoy; no se auditó la política efectiva.

Diagnóstico de lectura, desde backend:

```powershell
& .\.venv\Scripts\python.exe scripts/oci_diagnose.py
```

La prueba real optativa `scripts/verify_sprint3_oci.py` requiere
`--allow-oci-writes --confirm-synthetic` y un informe nuevo; conserva muestras y
no elimina objetos. No confundir un diagnóstico de conexión con copia verificada.

<details>
<summary>Referencia histórica de configuración y movimiento — no usar como guía vigente</summary>

<!-- Agregado por Edil: conservamos la guía de Eliana y aclaramos primero la configuración vigente para no seguir ejemplos antiguos por error. -->
# Nota de integración: configuración vigente

La guía original de Eliana queda debajo como referencia histórica. Para esta integración:
- Ejecuta instalación desde `mediflow` y los scripts OCI desde `mediflow/backend`.
- El backend carga `mediflow/.env`; no usa automáticamente `backend/.env`.
- Puedes usar el perfil local OCI con `OCI_CONFIG_PROFILE=DEFAULT`.
- Configura `OCI_BUCKET_RECIBIDOS=recibidos`, `OCI_BUCKET_PROCESADOS=procesados` y `OCI_BUCKET_AUDITORIA=auditoria_humana`.
- `OCI_BUCKET_NAME` es compatibilidad con el cliente anterior; no reemplaza los tres buckets oficiales.
- Las rutas reales son `mediflow/backend/app/core/oci_client.py` y `mediflow/backend/test_oci.py`.
- No ejecutes pruebas reales sin permiso: suben objetos a OCI. Una salida de ejemplo no prueba que tu cuenta se haya conectado.
- No guardes claves privadas ni secretos en Git. La verificación de traslado debe comprobarse con pruebas; esta documentación sola no la demuestra.

<!-- Agregado por Edil: los ejemplos siguientes pertenecen a la entrega original; no son la configuración oficial de tres buckets. -->

# Configuración de conexión (OCI)

El proyecto utiliza **Oracle Cloud Infrastructure (OCI) Object Storage** para almacenar y gestionar archivos.
La configuración de OCI se realiza mediante variables de entorno, por lo que las credenciales no se almacenan directamente en el código fuente.

## Requisitos

Antes de utilizar la integración con OCI, se necesita:

* Python 3.11 o superior.
* Una cuenta de Oracle Cloud Infrastructure.
* Un usuario OCI con permisos para utilizar Object Storage.
* Una API Key configurada para el usuario.
* Un bucket de Object Storage.
* El archivo de clave privada `.pem` generado para la API Key.

---

## 1. Instalar las dependencias

Desde la raíz del proyecto ejecutar:

```bash
pip install -r requirements.txt
```

Las principales dependencias utilizadas para la conexión OCI son:

```text
oci
python-dotenv
```

---

## 2. Crear el archivo `.env`

El repositorio contiene un archivo `.env.example` que sirve como plantilla.

El archivo debe contener:

```env
OCI_USER_OCID=ocid1.user.oc1.xxxxxxxxxxxxxxxxx
OCI_FINGERPRINT=xx:xx:xx:xx:xx:xx:xx
OCI_KEY_FILE=/ruta/a/tu/oci_api_key.pem
OCI_TENANCY_OCID=ocid1.tenancy.oc1.xxxxxxxxxxxxxxxxx
OCI_REGION=sa-santiago-1
OCI_NAMESPACE=
OCI_BUCKET_NAME=nombre-del-bucket
```

### Descripción de las variables

| Variable           | Descripción                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------- |
| `OCI_USER_OCID`    | OCID del usuario de OCI que realizará las operaciones.                                            |
| `OCI_FINGERPRINT`  | Fingerprint de la API Key asociada al usuario.                                                    |
| `OCI_KEY_FILE`     | Ruta local al archivo de clave privada `.pem`.                                                    |
| `OCI_TENANCY_OCID` | OCID de la tenancy de OCI.                                                                        |
| `OCI_REGION`       | Región donde se encuentra el recurso de OCI.                                                      |
| `OCI_NAMESPACE`    | Namespace de Object Storage. Es opcional. Si se deja vacío, se obtiene automáticamente desde OCI. |
| `OCI_BUCKET_NAME`  | Nombre del bucket de Object Storage utilizado por la aplicación.                                  |

---

## 3. Configurar la API Key de OCI

Cada desarrollador debe utilizar sus propias credenciales de OCI.

Para crear una API Key:

1. Ingresar a la consola de Oracle Cloud Infrastructure.
2. Abrir el perfil del usuario.
3. Ingresar a **My Profile**.
4. Buscar la sección **API Keys**.
5. Seleccionar **Add API Key**.
6. Generar un nuevo par de claves.
7. Descargar la clave privada.
8. Guardar el archivo `.pem` en una ubicación segura.

La variable:

```env
OCI_KEY_FILE=/ruta/a/tu/oci_api_key.pem
```

debe apuntar a la ubicación donde se guardó la clave privada.

### Ejemplo en Windows

```env
OCI_KEY_FILE=C:\Users\usuario\.oci\oci_api_key.pem
```

### Ejemplo utilizando la carpeta `.oci`

```env
OCI_KEY_FILE=~/.oci/oci_api_key.pem
```

La clave privada **no debe subirse al repositorio**.

---

## 4. Configurar el bucket

La aplicación utiliza Oracle Cloud Object Storage.

Por ejemplo:

```env
OCI_BUCKET_NAME=mediflow-documentos
```

El nombre debe coincidir exactamente con el bucket creado en OCI.

El bucket puede ser creado desde:

**OCI Console → Storage → Object Storage → Buckets**

El bucket y el usuario que utiliza la aplicación deben tener las políticas IAM necesarias para realizar las operaciones requeridas.

---

## 5. Seguridad

Por motivos de seguridad, los siguientes archivos **no deben ser subidos al repositorio**:

```text
.env
*.pem
*.key
```
---

## 6. Probar la conexión con OCI

Una vez configurado el archivo `.env`, ejecutar:

```bash
python test_oci.py
```

Si la configuración es correcta, se debería obtener una salida similar a:

```text
Inicializando conexión con OCI...
Conexión con OCI exitosa.
Namespace: axabfpklpxt1
Región: sa-santiago-1
Subiendo 'prueba_oci.txt' al bucket 'mediflow-documentos' como 'prueba_oci.txt'...
Subida local completada con éxito.
Archivo subido correctamente.
```

Esto confirma que:

* Las variables de entorno fueron cargadas correctamente.
* Las credenciales OCI son válidas.
* La API Key puede autenticarse.
* El cliente de Object Storage fue creado correctamente.
* El bucket es accesible.
* Se puede subir un archivo a Object Storage.

---

## 7. Descargar un archivo

Para descargar un archivo almacenado en OCI:

```python
from app.core.oci_client import OCIStorageManager


gestor = OCIStorageManager()

gestor.descargar_archivo(
    nombre_bucket=gestor.bucket_name,
    nombre_archivo="informe.pdf",
    ruta_descarga="descargas/informe.pdf"
)
```

El archivo será descargado desde OCI y almacenado localmente en la ruta indicada.

---

## 8. Subir un archivo desde memoria

La clase también permite subir contenido directamente desde memoria:

```python
from app.core.oci_client import OCIStorageManager


gestor = OCIStorageManager()

gestor.subir_archivo_desde_memoria(
    contenido_bytes=contenido,
    nombre_bucket=gestor.bucket_name,
    nombre_destino="documentos/archivo.pdf"
)
```

Esto resulta útil cuando el archivo es recibido directamente desde una aplicación web, por ejemplo mediante FastAPI, Flask o Streamlit, sin necesidad de guardarlo previamente en el disco.

---

## 9. Mover un archivo entre buckets

La clase permite mover un objeto desde un bucket de origen hacia un bucket de destino:

```python
from app.core.oci_client import OCIStorageManager


gestor = OCIStorageManager()

gestor.mover_archivo(
    nombre_archivo="informe.pdf",
    bucket_origen="bucket-origen",
    bucket_destino="bucket-destino"
)
```

El proceso realiza:

1. Copia del archivo al bucket de destino.
2. Verificación de que la copia se realizó correctamente.
3. Eliminación del archivo original únicamente después de confirmar la copia.

---

## 10. Estructura relacionada con OCI

La integración se organiza de la siguiente manera:

```text
mediflow/
│
├── app/
│   └── core/
│       └── oci_client.py
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── test_oci.py
└── prueba_oci.txt
```

### Archivos importantes

**`oci_client.py`**

Contiene la clase `OCIStorageManager`, encargada de gestionar la conexión y las operaciones con OCI Object Storage.

**`.env`**

Contiene la configuración y credenciales locales de cada desarrollador. No debe subirse al repositorio.

**`.env.example`**

Plantilla de configuración que permite a nuevos desarrolladores conocer las variables necesarias.

**`test_oci.py`**

Script de prueba para verificar la conexión con OCI y la subida de archivos.

**`requirements.txt`**

Contiene las dependencias necesarias para ejecutar el proyecto.

---

## 11. Flujo de configuración para nuevos desarrolladores

El flujo recomendado es:

```text
Clonar repositorio
        │
        ▼
Instalar dependencias
        │
        ▼
Copiar .env.example
        │
        ▼
Crear .env
        │
        ▼
Configurar credenciales OCI
        │
        ▼
Configurar API Key
        │
        ▼
Configurar bucket
        │
        ▼
Ejecutar test_oci.py
        │
        ▼
Conexión OCI verificada
```
</details>
