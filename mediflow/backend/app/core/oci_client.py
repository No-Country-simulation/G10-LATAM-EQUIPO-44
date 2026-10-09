"""
Módulo OCIStorageManager
------------------------
Este módulo centraliza la conexión con Oracle Cloud Infrastructure (OCI).

Funciones creadas y parámetros que reciben:
- subir_archivo_desde_memoria(contenido_bytes, nombre_bucket, nombre_destino): Sube un archivo directamente desde un flujo de bytes (ideal para FastAPI).
- subir_archivo(ruta_local, nombre_bucket, nombre_destino): Sube un archivo físico leyendo la ruta de tu disco duro.
- descargar_archivo(nombre_bucket, nombre_archivo, ruta_descarga): Descarga un archivo desde un bucket hacia tu equipo.
- mover_archivo(nombre_archivo, bucket_origen, bucket_destino): Copia un documento hacia un nuevo bucket y elimina el original.

Ejemplo sencillo de uso:
------------------------
from oci_client import OCIStorageManager

gestor = OCIStorageManager()
gestor.subir_archivo_desde_memoria(
    contenido_bytes=archivo_bytes, 
    nombre_bucket="recibidos", 
    nombre_destino="DOC-123.pdf"
)
"""

import oci
import os

from .oci_transfer import OCIObjectMover
from .config import settings


class OCIStorageManager:
    def __init__(self, config_profile=None):
        # Carga la configuración local por defecto desde ~/.oci/config
        profile = config_profile or settings.OCI_CONFIG_PROFILE
        self.config = oci.config.from_file(
            file_location=settings.OCI_CONFIG_FILE,
            profile_name=profile,
        )
        self.object_storage = oci.object_storage.ObjectStorageClient(self.config)
        self.settings = settings
        # El namespace es un identificador único del Tenancy en OCI
        self.namespace = settings.OCI_NAMESPACE or self.object_storage.get_namespace().data

    def subir_archivo_desde_memoria(self, contenido_bytes, nombre_bucket: str, nombre_destino: str):
        """Sube un archivo directamente desde memoria (ideal para recibir desde la API REST)."""
        print(f"Subiendo archivo desde memoria al bucket '{nombre_bucket}' como '{nombre_destino}'...")
        self.object_storage.put_object(
            namespace_name=self.namespace,
            bucket_name=nombre_bucket,
            object_name=nombre_destino,
            put_object_body=contenido_bytes
        )
        print("Subida a memoria completada con éxito.")

    def subir_a_recibidos(self, contenido_bytes: bytes, nombre_destino: str) -> str:
        """Sube un objeto al bucket recibido, respetando el prefijo configurado."""
        object_name = f"{settings.OCI_PREFIX_RECIBIDOS}{nombre_destino}"
        self.subir_archivo_desde_memoria(
            contenido_bytes,
            settings.OCI_BUCKET_RECIBIDOS,
            object_name,
        )
        return object_name

    def subir_archivo(self, ruta_local: str, nombre_bucket: str, nombre_destino: str):
        """Sube un archivo local al bucket de OCI (útil para pruebas de escritorio)."""
        if not os.path.exists(ruta_local):
            raise FileNotFoundError(f"El archivo local '{ruta_local}' no fue encontrado.")

        with open(ruta_local, "rb") as f:
            print(f"Subiendo '{ruta_local}' al bucket '{nombre_bucket}' como '{nombre_destino}'...")
            self.object_storage.put_object(
                namespace_name=self.namespace,
                bucket_name=nombre_bucket,
                object_name=nombre_destino,
                put_object_body=f
            )
        print("Subida local completada con éxito.")

    def descargar_archivo(self, nombre_bucket: str, nombre_archivo: str, ruta_descarga: str):
        """Descarga un objeto del bucket a una ruta local."""
        print(f"Descargando '{nombre_archivo}' desde el bucket '{nombre_bucket}'...")
        respuesta = self.object_storage.get_object(
            namespace_name=self.namespace,
            bucket_name=nombre_bucket,
            object_name=nombre_archivo
        )

        with open(ruta_descarga, "wb") as f:
            for chunk in respuesta.data.raw.stream(1024 * 1024, decode_content=False):
                f.write(chunk)
        print(f"Archivo guardado exitosamente en '{ruta_descarga}'.")

    def mover_archivo(self, nombre_archivo: str, bucket_origen: str, bucket_destino: str):
        """Mueve un objeto verificando su contenido antes de eliminar el origen."""
        return OCIObjectMover(
            self.object_storage,
            self.namespace,
            self.config["region"],
        ).move(nombre_archivo, bucket_origen, bucket_destino)