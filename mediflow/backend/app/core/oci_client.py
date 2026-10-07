
from __future__ import annotations

import os
import time

import oci
from dotenv import load_dotenv


# Carga las variables definidas en el archivo .env
# sin sobrescribir variables de entorno ya existentes.
load_dotenv()

REQUIRED_ENV_VARS = [
    "OCI_USER_OCID",
    "OCI_FINGERPRINT",
    "OCI_KEY_FILE",
    "OCI_TENANCY_OCID",
    "OCI_REGION",
]


class OCIStorageManager:
    """Gestiona las operaciones sobre OCI Object Storage."""

    def __init__(self, config_profile: str | None = None):
        """
        Inicializa el cliente de OCI.
        El parámetro config_profile se mantiene por compatibilidad con código existente.
        """

        # Se mantiene el parámetro para evitar romper código existente.
        del config_profile

        # Validar que las variables necesarias estén configuradas.
        missing_vars = [
            variable
            for variable in REQUIRED_ENV_VARS
            if not os.getenv(variable)
        ]

        if missing_vars:
            raise ValueError(
                "Faltan variables de entorno requeridas para OCI: "
                + ", ".join(missing_vars)
            )


        # Obtención de la configuración OCI desde el entorno.
        self.config = {
            "user": os.getenv("OCI_USER_OCID"),
            "fingerprint": os.getenv("OCI_FINGERPRINT"),
            "key_file": os.path.expanduser(os.getenv("OCI_KEY_FILE", "")),
            "tenancy": os.getenv("OCI_TENANCY_OCID"),
            "region": os.getenv("OCI_REGION"),
        }

        # Valida que la configuración mínima requerida por OCI esté correctamente definida.
        oci.config.validate_config(self.config)

        # Crea el cliente de Object Storage.
        self.object_storage = oci.object_storage.ObjectStorageClient(self.config)

        # El namespace puede configurarse mediante el entorno. Si no existe, se obtiene directamente desde OCI.
        self.namespace = (os.getenv("OCI_NAMESPACE") or self.object_storage.get_namespace().data)
        
        #Traer el nombre del bucket desde la variable de entorno
        self.bucket_name = os.getenv("OCI_BUCKET_NAME")

    def subir_archivo_desde_memoria(self, contenido_bytes, nombre_bucket: str, nombre_destino: str,):
        """
        Sube un archivo directamente desde memoria.
        """
        print(f"Subiendo archivo desde memoria al bucket " f"'{nombre_bucket}' como '{nombre_destino}'...")

        self.object_storage.put_object(namespace_name=self.namespace, bucket_name=nombre_bucket, object_name=nombre_destino, put_object_body=contenido_bytes,)

        print("Subida a memoria completada con éxito.")

    def subir_archivo(self, ruta_local: str, nombre_bucket: str, nombre_destino: str,):
        """
        Sube un archivo local al bucket de OCI.
        """

        if not os.path.exists(ruta_local):
            raise FileNotFoundError(
                f"El archivo local '{ruta_local}' no fue encontrado."
            )

        with open(ruta_local, "rb") as archivo:
            print(f"Subiendo '{ruta_local}' al bucket " f"'{nombre_bucket}' como '{nombre_destino}'...")

            self.object_storage.put_object(namespace_name=self.namespace, bucket_name=nombre_bucket, object_name=nombre_destino, put_object_body=archivo,)

        print("Subida local completada con éxito.")

    def descargar_archivo(self, nombre_bucket: str, nombre_archivo: str, ruta_descarga: str,):
        """
        Descarga un objeto desde OCI hacia una ruta local.
        """

        print(f"Descargando '{nombre_archivo}' " f"desde el bucket '{nombre_bucket}'...")

        respuesta = self.object_storage.get_object(
            namespace_name=self.namespace,
            bucket_name=nombre_bucket,
            object_name=nombre_archivo,
        )

        with open(ruta_descarga, "wb") as archivo:
            for chunk in respuesta.data.raw.stream(
                1024 * 1024, decode_content=False,):
                archivo.write(chunk)

        print(f"Archivo guardado exitosamente en " f"'{ruta_descarga}'.")

    def mover_archivo(self, nombre_archivo: str, bucket_origen: str, bucket_destino: str,):
        """
        Mueve un archivo entre buckets.

        El proceso consiste en:
        1. Solicitar la copia del archivo.
        2. Esperar hasta confirmar que el archivo existe en el bucket destino.
        3. Eliminar el archivo del bucket origen.
        """

        print(f"Moviendo '{nombre_archivo}' " f"de '{bucket_origen}' a '{bucket_destino}'...")

        detalle_copia = oci.object_storage.models.CopyObjectDetails(
            source_object_name=nombre_archivo,
            destination_region=self.config["region"],
            destination_namespace=self.namespace,
            destination_bucket=bucket_destino,
            destination_object_name=nombre_archivo,
        )

        # 1. Solicitar la copia del objeto.
        self.object_storage.copy_object(self.namespace, bucket_origen, detalle_copia,)

        # 2. Esperar confirmación de que el objeto
        # existe en el bucket destino.
        print("   Esperando confirmación del copiado en OCI...")

        copiado = False

        for _ in range(10):
            time.sleep(1.5)

            respuesta = self.object_storage.list_objects(self.namespace, bucket_destino,)

            nombres = [
                objeto.name
                for objeto in respuesta.data.objects
            ]

            if nombre_archivo in nombres:
                copiado = True
                break

        # Si no se confirmó la copia, no se elimina el archivo original.
        if not copiado:
            raise Exception(f"No se pudo completar la copia de " f"'{nombre_archivo}' hacia " f"'{bucket_destino}'.")

        # 3. Eliminar el archivo original solamente .después de confirmar la copia.
        self.object_storage.delete_object(self.namespace, bucket_origen, nombre_archivo,)

        print("Movimiento completado con éxito.")