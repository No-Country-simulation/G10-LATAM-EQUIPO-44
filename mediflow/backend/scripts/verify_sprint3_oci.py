"""Prueba optativa OCI/API de Sprint 3 con bytes fijos sin información clínica.

Reutiliza recepción HTTP y etapas existentes de copia/persistencia. La entrada
estructurada de análisis es una fixture local: no llama ni sustituye a Gemini
en el servidor. No elimina objetos ni modifica IAM.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.environment import load_environment
from app.core.oci_client import OCIStorageManager
from app.api.routes import _copy_original_to_result_bucket, _persist_triage_result
from app.models.schemas import TriageResponse
from app.services.servicio_orquestador import procesar_con_orquestador

CONTENT = b"MediFlow storage verification. Synthetic software fixture. No clinical data."


def safe_error(error):
    """Conservar categoría/código/HTTP, nunca mensaje o URL crudos del SDK."""
    records, seen = [], set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        item = {"category": type(error).__name__}
        for key in ("status", "code", "operation_name"):
            value = getattr(error, key, None)
            if type(value) is int or isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
                item[key] = value
        records.append(item)
        error = error.__cause__ or error.__context__
    return records


class TraceStorage:
    """Observa y reenvía siempre al SDK real, sin fallback de transferencia."""
    def __init__(self, client, events):
        self.client, self.events = client, events

    def __getattr__(self, name):
        original = getattr(self.client, name)
        if not callable(original):
            return original
        def call(*args, **kwargs):
            item = {"operation": name}
            self.events.append(item)
            if name == "copy_object":
                details = kwargs["copy_object_details"]
                item["source_etag_condition"] = bool(details.source_object_if_match_e_tag)
                item["destination_no_overwrite"] = details.destination_object_if_none_match_e_tag == "*"
            try:
                response = original(*args, **kwargs)
                item["http_status"] = response.status
                if name == "copy_object":
                    item["work_request_id"] = response.headers.get("opc-work-request-id")
                if name == "get_work_request":
                    item["work_request_status"] = response.data.status
                    if str(response.data.status).lower() in {"failed", "canceled", "cancelled"}:
                        # El worker puede fallar después del HTTP 202. Guardar el código real.
                        try:
                            errors = self.client.list_work_request_errors(args[0]).data
                            item["worker_errors"] = [{"code": e.code,
                                "insufficient_service_permissions": "InsufficientServicePermissions" in str(e.message)} for e in errors]
                        except Exception as error:
                            item["worker_error_lookup_failure"] = safe_error(error)
                return response
            except Exception as error:
                item["errors"] = safe_error(error)
                raise
        return call


def inspect_object(manager, bucket, name):
    response = manager.object_storage.head_object(namespace_name=manager.namespace, bucket_name=bucket, object_name=name)
    etag = response.headers["etag"]
    downloaded = manager.object_storage.get_object(namespace_name=manager.namespace, bucket_name=bucket, object_name=name, if_match=etag)
    content = downloaded.data.content
    return {"bucket": bucket, "size": int(response.headers["content-length"]),
            "etag": etag, "sha256": hashlib.sha256(content).hexdigest()}, content


def fixture(received, *, review=False):
    """Datos explícitos de prueba de software, sin diagnóstico ni dosis clínica."""
    doc = json.loads(json.dumps(received))
    doc["status"] = "procesado"
    doc["clasificacion"].update(tipo_documento="Receta Médica", score_confianza_clasificacion=0.99)
    doc["datos_extraidos"]["paciente"]["nombre"] = "SYNTHETIC_SOFTWARE_TEST"
    doc["datos_extraidos"]["medico_solicitante"]["nombre"] = "SYNTHETIC_SOFTWARE_TEST"
    doc["datos_extraidos"]["medicamentos_recetados"] = [{"medicamento": "TEST_ONLY_NO_CLINICAL_USE", "dosis": None}]
    doc["decision_enrutamiento"].update(destino_principal="Cola_Farmacia",
        requiere_auditoria_humana=False, justificacion_enrutamiento="Synthetic software fixture.")
    if review:
        doc["status"] = "auditoria_humana"
        doc["decision_enrutamiento"].update(destino_principal="Cola_Revision_Humana", requiere_auditoria_humana=True)
    return procesar_con_orquestador(doc, source_text=CONTENT.decode("ascii"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-oci-writes", action="store_true")
    parser.add_argument("--confirm-synthetic", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8144")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--review", action="store_true", help="Otra muestra propia con revisión previa explícita para auditoria_humana")
    args = parser.parse_args(argv)
    if not (args.allow_oci_writes and args.confirm_synthetic):
        parser.error("Requiere autorización OCI y confirmación de muestra sintética.")
    url = urlsplit(args.base_url)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
        parser.error("Usar el backend local de pruebas sin credenciales en URL.")
    if args.report.exists():
        parser.error("No sobrescribir una evidencia existente.")
    load_environment()
    report = {"task": "Drazen S3-03/S3-04A; Brando S3-06", "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "oci_real": True, "http_real": True, "gemini_called": False,
              "analysis_input": "local_fixed_software_fixture_not_llm_output",
              "rules_profile": os.environ.get("TRIAGE_RULES_PROFILE", "general"),
              "deletes_performed": False, "iam_changes": False, "events": [], "passed": False}
    def save():
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stage = "initialize_oci"
    try:
        manager = OCIStorageManager()
        manager.object_storage = TraceStorage(manager.object_storage, report["events"])
        report["region"] = manager.config.get("region") or manager.settings.region
        with httpx.Client(base_url=args.base_url, timeout=120, trust_env=False) as client:
            stage = "http_receive"
            response = client.post("/api/triage", data={"analyze": "false"}, files={"file": ("synthetic-storage-check.txt", CONTENT, "text/plain")})
            report["receipt_http"] = response.status_code
            response.raise_for_status()
            received = TriageResponse.model_validate(response.json(), strict=True).model_dump(mode="json")
            doc_id = received["documento_id"]
            report["document_id"] = doc_id
            report["object_name"] = name = received["almacenamiento_oci"]["ruta_objeto"]
            source = manager.settings.bucket_recibidos
            stage = "source_reception_verification"
            before, original = inspect_object(manager, source, name)
            assert original == CONTENT and received["status"] == "recibido"
            report["source_before"] = before
            report["received_json_matches_http"] = manager.recuperar_json(source, doc_id + ".json") == received
            assert report["received_json_matches_http"]
            stage = "orchestration_of_local_fixture"
            routed = fixture(received, review=args.review)
            report["expected"] = {"id": doc_id, "status": routed["status"], "priority": routed["clasificacion"]["nivel_prioridad"],
                                  "destination": routed["decision_enrutamiento"]["destino_principal"]}
            stage = "native_copy_and_verification"
            final = asyncio.run(_copy_original_to_result_bucket(manager, routed, doc_id, source, name))
            final_data = final.model_dump(mode="json")
            stage = "json_persistence"
            asyncio.run(_persist_triage_result(manager, final, doc_id))
            stage = "verify_retained_original_and_copy"
            after, original_after = inspect_object(manager, source, name)
            target = final.almacenamiento_oci.bucket
            copied, copied_content = inspect_object(manager, target, name)
            report["source_after"], report["destination"] = after, copied
            report["integrity"] = {"original_retained": original_after == CONTENT,
                "source_etag_unchanged": before["etag"] == after["etag"],
                "sizes_match": before["size"] == after["size"] == copied["size"] == len(CONTENT),
                "sha256_match": before["sha256"] == after["sha256"] == copied["sha256"],
                "copy_bytes_match": copied_content == CONTENT,
                "etag_equality_not_required_between_objects": True}
            assert all(report["integrity"].values())
            stage = "json_readback"
            json_meta, json_content = inspect_object(manager, target, doc_id + ".json")
            report["final_json_metadata"] = json_meta
            report["final_json_equals_model"] = json.loads(json_content) == final_data
            assert report["final_json_equals_model"]
            assert manager.recuperar_resultado_triage(doc_id) == final_data
            stage = "http_get_by_id"
            detail = client.get("/api/documents/" + doc_id)
            report["get_by_id_http"] = detail.status_code
            detail.raise_for_status()
            report["get_by_id_equals_final"] = detail.json() == final_data
            assert report["get_by_id_equals_final"]
            stage = "http_get_list"
            listing = client.get("/api/documents", params={"limit": 500})
            report["get_list_http"] = listing.status_code
            listing.raise_for_status()
            matches = [d for d in listing.json() if d.get("documento_id") == doc_id]
            report["list_contains_single_current_version"] = len(matches) == 1 and matches[0] == final_data
            assert report["list_contains_single_current_version"]
            stage = "http_missing_id"
            missing = client.get("/api/documents/DOC-SYNTHETIC-MISSING-" + uuid4().hex)
            report["missing_id_http"] = missing.status_code
            assert missing.status_code == 404
            report["passed"] = True
    except Exception as error:
        report["failed_stage"] = stage
        report["errors"] = safe_error(error)
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        save()
    print(json.dumps({key: report[key] for key in ("passed", "document_id", "failed_stage", "errors") if key in report}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
