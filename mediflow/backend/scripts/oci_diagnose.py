"""Read-only OCI Object Storage diagnostic for MediFlow.

Run from ``mediflow/backend``.  This script never writes, copies, or deletes
objects.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import oci

from app.core.config import settings


def build_client(profile: str) -> tuple[Any, str, str]:
    config = settings.get_oci_config_dict()
    if config is None:
        config = oci.config.from_file(profile_name=profile)
    client = oci.object_storage.ObjectStorageClient(config)
    namespace = settings.OCI_NAMESPACE or client.get_namespace().data
    return client, namespace, config["region"]


def print_bucket(client: Any, namespace: str, bucket: str) -> None:
    print(f"\nBucket: {bucket}")
    response = client.list_objects(
        namespace_name=namespace,
        bucket_name=bucket,
        fields="name,size,timeCreated,etag",
    )
    objects = response.data.objects
    if not objects:
        print("  (sin objetos)")
        return
    for item in objects:
        print(f"  {item.name} | size={item.size} bytes")


def print_metadata(client: Any, namespace: str, bucket: str, object_name: str) -> None:
    response = client.head_object(
        namespace_name=namespace,
        bucket_name=bucket,
        object_name=object_name,
    )
    headers = response.headers
    print(f"\nMetadatos: {bucket}/{object_name}")
    for key in ("content-length", "content-type", "etag", "last-modified", "opc-version"):
        if key in headers:
            print(f"  {key}: {headers[key]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnóstico OCI de solo lectura")
    parser.add_argument("--profile", default="DEFAULT")
    parser.add_argument("--object", dest="object_name")
    parser.add_argument("--bucket", default=None)
    args = parser.parse_args()

    try:
        client, namespace, region = build_client(args.profile)
        print(f"Configuración OCI válida; región={region}; namespace disponible")
        print_bucket(client, namespace, settings.OCI_BUCKET_RECIBIDOS)
        print_bucket(client, namespace, settings.OCI_BUCKET_PROCESADOS)
        if args.object_name:
            print_metadata(
                client,
                namespace,
                args.bucket or settings.OCI_BUCKET_RECIBIDOS,
                args.object_name,
            )
        return 0
    except oci.exceptions.ConfigFileNotFound as error:
        print(f"ERROR configuración: no se encontró el perfil OCI: {error}", file=sys.stderr)
    except oci.exceptions.InvalidConfig as error:
        print(f"ERROR configuración: perfil OCI inválido: {error}", file=sys.stderr)
    except oci.exceptions.ServiceError as error:
        status = getattr(error, "status", "desconocido")
        print(f"ERROR OCI: status={status}; revise permisos, bucket y objeto", file=sys.stderr)
    except (ConnectionError, TimeoutError, OSError) as error:
        print(f"ERROR conectividad o sistema: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
