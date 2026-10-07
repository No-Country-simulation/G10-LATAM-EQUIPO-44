from app.core.oci_client import OCIStorageManager


def main():
    print("Inicializando conexión con OCI...")

    gestor = OCIStorageManager()

    print("Conexión con OCI exitosa.")
    print(f"Namespace: {gestor.namespace}")
    print(f"Región: {gestor.config['region']}")

    if not gestor.bucket_name:
        raise ValueError(
            "OCI_BUCKET_NAME no está configurado en el archivo .env"
        )

    gestor.subir_archivo(
        ruta_local="prueba_oci.txt",
        nombre_bucket=gestor.bucket_name,
        nombre_destino="prueba_oci.txt",
    )

    print("Archivo subido correctamente.")


if __name__ == "__main__":
    main()