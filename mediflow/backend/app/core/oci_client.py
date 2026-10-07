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

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import oci

try:
    from app.core.config import settings
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.core.config import settings

class OCIStorageManager:
    def __init__(self, config_profile: str = "DEFAULT", custom_config: Optional[Dict[str, Any]] = None):
        """
        Inicializa el gestor de OCI Object Storage.

        Estrategia de resolución de credenciales:
        1. Diccionario explícito 'custom_config' (si se pasa por parámetro).
        2. Perfil explícito en ~/.oci/config (si 'config_profile' es distinto a 'DEFAULT').
        3. Variables de entorno / archivo .env (si están configuradas en settings).
        4. Perfil DEFAULT en archivo local ~/.oci/config (fallback para desarrollo local).
        """
        if custom_config:
            self.config = custom_config
        elif config_profile != "DEFAULT":
            self.config = oci.config.from_file(profile_name=config_profile)
        elif settings.has_oci_env_credentials():
            self.config = settings.get_oci_config_dict()
        else:
            self.config = oci.config.from_file(profile_name=config_profile)

        oci.config.validate_config(self.config)
        self.object_storage = oci.object_storage.ObjectStorageClient(self.config)

        # El namespace identifica unívocamente el Tenancy en OCI
        dummy_namespaces = ("mediflow_namespace", "")
        if settings.OCI_NAMESPACE and settings.OCI_NAMESPACE not in dummy_namespaces:
            self.namespace = settings.OCI_NAMESPACE
        else:
            self.namespace = self.object_storage.get_namespace().data

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
        """Mueve un archivo entre buckets (copia y elimina el original tras confirmar)."""
        import time
        print(f"Moviendo '{nombre_archivo}' de '{bucket_origen}' a '{bucket_destino}'...")
        
        detalle_copia = oci.object_storage.models.CopyObjectDetails(
            source_object_name=nombre_archivo,
            destination_region=self.config["region"],
            destination_namespace=self.namespace,
            destination_bucket=bucket_destino,
            destination_object_name=nombre_archivo
        )
        
        # 1. Iniciar la solicitud de copia en OCI
        self.object_storage.copy_object(self.namespace, bucket_origen, detalle_copia)
        
        # 2. Esperar confirmación de que el objeto llegó al destino
        print("   Esperando confirmación del copiado en OCI...")
        copiado = False
        for _ in range(10):
            time.sleep(1.5)
            res = self.object_storage.list_objects(self.namespace, bucket_destino)
            nombres = [obj.name for obj in res.data.objects]
            if nombre_archivo in nombres:
                copiado = True
                break
        
        if not copiado:
            raise Exception(f"No se pudo completar la copia de '{nombre_archivo}' hacia '{bucket_destino}'.")
            
        # 3. Borrar del origen únicamente cuando ya existe en el destino
        self.object_storage.delete_object(self.namespace, bucket_origen, nombre_archivo)
        print("Movimiento completado con éxito.")