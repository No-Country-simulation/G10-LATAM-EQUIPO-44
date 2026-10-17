"""Diagnóstico OCI de solo lectura con la configuración canónica de MediFlow.

Ejecutar desde mediflow/backend: python -m scripts.oci_diagnose
No imprime nombres de objetos, documentos, credenciales ni mensajes crudos del SDK.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import sys
from typing import Any

from app.core.environment import load_environment
from app.core.oci_client import OCISettings, OCIStorageManager


def build_client(profile: str | None = None) -> OCIStorageManager:
    # Agregado por Edil: usar el mismo mediflow/.env y perfil que el backend.
    # No crear otro Settings ni leer backend/.env para este diagnóstico.
    load_environment()
    settings = OCISettings.from_environment()
    if profile is not None:
        settings = replace(settings, config_profile=profile)
    return OCIStorageManager(settings)


def print_bucket(client: Any, namespace: str, bucket: str) -> None:
    # Agregado por Edil: consultar solo metadatos del bucket. Antes se listaban
    # nombres de documentos, que no hacen falta para verificar conectividad.
    client.get_bucket(namespace_name=namespace, bucket_name=bucket)
    print(f"Bucket {bucket}: metadatos accesibles")


def print_metadata(client: Any, namespace: str, bucket: str, object_name: str) -> None:
    response = client.head_object(
        namespace_name=namespace, bucket_name=bucket, object_name=object_name
    )
    print("Objeto seleccionado: metadatos accesibles")
    for key in ("content-length", "content-type"):
        value = response.headers.get(key)
        if value is not None:
            print(f"  {key}: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico OCI de solo lectura")
    parser.add_argument("--profile", default=None,
                        help="Sobrescribe OCI_CONFIG_PROFILE solo para esta ejecución")
    parser.add_argument("--object", dest="object_name")
    parser.add_argument("--bucket", default=None)
    args = parser.parse_args(argv)
    try:
        manager = build_client(args.profile)
        buckets = (manager.settings.bucket_recibidos,
                   manager.settings.bucket_procesados,
                   manager.settings.bucket_auditoria)
        if args.bucket is not None and args.bucket not in buckets:
            raise ValueError("El bucket no pertenece a la configuración del proyecto.")
        print("Configuración OCI cargada; no se muestran credenciales ni documentos")
        for bucket in buckets:
            print_bucket(manager.object_storage, manager.namespace, bucket)
        if args.object_name:
            print_metadata(manager.object_storage, manager.namespace,
                           args.bucket or manager.settings.bucket_recibidos,
                           args.object_name)
        return 0
    except Exception as error:
        # Agregado por Edil: no imprimir str(error): el SDK puede incluir rutas,
        # OCID o datos de la solicitud. La categoría y HTTP bastan para orientar.
        status = getattr(error, "status", None)
        status_text = f"; HTTP {status}" if type(status) is int else ""
        print(f"ERROR OCI: {type(error).__name__}{status_text}; revise configuración, "
              "conectividad y permisos localmente.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


# Agregado por Edil: versión original de Brando conservada como referencia.
# """Read-only OCI Object Storage diagnostic for MediFlow.
#
# Run from ``mediflow/backend``.  This script never writes, copies, or deletes
# objects.
# """
#
# from __future__ import annotations
#
# import argparse
# import os
# import sys
# from typing import Any
#
# import oci
#
# from app.core.config import settings
#
#
# def build_client(profile: str) -> tuple[Any, str, str]:
#     config = settings.get_oci_config_dict()
#     if config is None:
#         config = oci.config.from_file(profile_name=profile)
#     client = oci.object_storage.ObjectStorageClient(config)
#     namespace = settings.OCI_NAMESPACE or client.get_namespace().data
#     return client, namespace, config["region"]
#
#
# def print_bucket(client: Any, namespace: str, bucket: str) -> None:
#     print(f"\nBucket: {bucket}")
#     response = client.list_objects(
#         namespace_name=namespace,
#         bucket_name=bucket,
#         fields="name,size,timeCreated,etag",
#     )
#     objects = response.data.objects
#     if not objects:
#         print("  (sin objetos)")
#         return
#     for item in objects:
#         print(f"  {item.name} | size={item.size} bytes")
#
#
# def print_metadata(client: Any, namespace: str, bucket: str, object_name: str) -> None:
#     response = client.head_object(
#         namespace_name=namespace,
#         bucket_name=bucket,
#         object_name=object_name,
#     )
#     headers = response.headers
#     print(f"\nMetadatos: {bucket}/{object_name}")
#     for key in ("content-length", "content-type", "etag", "last-modified", "opc-version"):
#         if key in headers:
#             print(f"  {key}: {headers[key]}")
#
#
# def main() -> int:
#     parser = argparse.ArgumentParser(description="Diagnóstico OCI de solo lectura")
#     parser.add_argument("--profile", default="DEFAULT")
#     parser.add_argument("--object", dest="object_name")
#     parser.add_argument("--bucket", default=None)
#     args = parser.parse_args()
#
#     try:
#         client, namespace, region = build_client(args.profile)
#         print(f"Configuración OCI válida; región={region}; namespace disponible")
#         print_bucket(client, namespace, settings.OCI_BUCKET_RECIBIDOS)
#         print_bucket(client, namespace, settings.OCI_BUCKET_PROCESADOS)
#         if args.object_name:
#             print_metadata(
#                 client,
#                 namespace,
#                 args.bucket or settings.OCI_BUCKET_RECIBIDOS,
#                 args.object_name,
#             )
#         return 0
#     except oci.exceptions.ConfigFileNotFound as error:
#         print(f"ERROR configuración: no se encontró el perfil OCI: {error}", file=sys.stderr)
#     except oci.exceptions.InvalidConfig as error:
#         print(f"ERROR configuración: perfil OCI inválido: {error}", file=sys.stderr)
#     except oci.exceptions.ServiceError as error:
#         status = getattr(error, "status", "desconocido")
#         print(f"ERROR OCI: status={status}; revise permisos, bucket y objeto", file=sys.stderr)
#     except (ConnectionError, TimeoutError, OSError) as error:
#         print(f"ERROR conectividad o sistema: {error}", file=sys.stderr)
#     return 1
#
#
# if __name__ == "__main__":
#     raise SystemExit(main())
