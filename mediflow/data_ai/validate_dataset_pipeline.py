"""S3-01.4: evaluación optativa del dataset mediante el API/pipeline reales."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mediflow/backend"))
from app.models.schemas import TriageResponse

DATASET = Path(__file__).resolve().parent / "dataset"
DESTINATIONS = {
    "FARMACIA": "Cola_Farmacia",
    "HISTORIA_CLINICA": "Cola_Historia_Clinica",
    "EMERGENCIA_MEDICA": "Cola_Emergencia_Medica",
}
SAFE_DESTINATIONS = set(DESTINATIONS.values()) | {"Cola_Revision_Humana", "Cola_Procesamiento_Inicial"}
MIMES = {".txt": "text/plain", ".pdf": "application/pdf", ".jpg": "image/jpeg"}


def load_cases(dataset: Path = DATASET) -> list[dict]:
    # Agregado por Edil: conservar las expectativas de Nicolás sin adaptarlas
    # a lo que responda Gemini. Solo se evalúan NOR/URG en esta tarea.
    cases = []
    with (dataset / "dataset_master.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["scenario"] not in {"NOR", "URG"}:
                continue
            filename = row["file_name"]
            if Path(filename).name != filename or not re.fullmatch(r"MF_\d{3}", row["case_id"]):
                raise ValueError("Identificador o ruta de caso inválidos.")
            path = dataset / {"NOR": "normal", "URG": "urgente"}[row["scenario"]] / filename
            if not path.is_file() or path.suffix.lower() not in MIMES:
                raise ValueError("Archivo del dataset ausente o formato no admitido.")
            if row["human_review"] not in {"True", "False"}:
                raise ValueError("Expectativa de revisión inválida.")
            review = row["human_review"] == "True"
            cases.append({
                "case_id": row["case_id"], "scenario": row["scenario"],
                "file": path, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "expected": {
                    "priority": {"ROUTINE": "Rutina", "URGENT": "Urgente"}[row["expected_priority"]],
                    "destination": DESTINATIONS[row["expected_destination"]],
                    "human_review": review,
                    "status": "auditoria_humana" if review else "procesado",
                },
            })
    if len({case["case_id"] for case in cases}) != len(cases) or not cases:
        raise ValueError("Inventario vacío o con casos duplicados.")
    return sorted(cases, key=lambda case: case["case_id"])


def compare_result(expected: dict, payload: dict) -> dict:
    result = TriageResponse.model_validate(payload, strict=True)
    observed = {
        "priority": result.clasificacion.nivel_prioridad,
        "destination": (result.decision_enrutamiento.destino_principal
                        if result.decision_enrutamiento.destino_principal in SAFE_DESTINATIONS
                        else "UNRECOGNIZED"),
        "human_review": result.decision_enrutamiento.requiere_auditoria_humana,
        "status": result.status,
    }
    comparisons = {key: observed[key] == value for key, value in expected.items()}
    # Agregado por Edil: separar éxito técnico de fidelidad al dataset. Un 201
    # con prioridad Rutina en un caso URG no debe contarse como aprobado.
    coherent = (
        (result.status == "auditoria_humana") == observed["human_review"]
        == (observed["destination"] == "Cola_Revision_Humana")
    )
    bucket = {"procesado": "procesados", "auditoria_humana": "auditoria_humana"}.get(result.status)
    storage_ok = result.almacenamiento_oci.bucket == bucket and result.almacenamiento_oci.status_backup == "exito"
    return {
        "observed": observed, "comparisons": comparisons,
        "coherent_routing": coherent, "final_storage_declared": storage_ok,
        "classification_confidence": result.clasificacion.score_confianza_clasificacion,
        "matches_dataset": all(comparisons.values()),
    }


def safe_id(value) -> str | None:
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) else None


def run_case(client: httpx.Client, case: dict) -> dict:
    path = case["file"]
    record = {
        "case_id": case["case_id"], "scenario": case["scenario"],
        "filename": path.name, "source_sha256": case["sha256"],
        "expected": case["expected"], "attempted": True,
        "technical_ok": False, "matches_dataset": False,
    }
    start = time.monotonic()
    try:
        # Agregado por Edil: un único POST por caso. No hay reintento ni mocks;
        # el servidor existente decide extracción TXT/PDF o media nativa Gemini.
        with path.open("rb") as handle:
            response = client.post("/api/triage", data={"analyze": "true"},
                                   files={"file": (path.name, handle, MIMES[path.suffix.lower()])})
        record["http_status"] = response.status_code
        if response.status_code != 201:
            record["outcome"] = "api_error"
            document_id = safe_id(response.headers.get("X-Document-ID"))
            if document_id:
                record["document_id"] = document_id
                recovered = client.get("/api/documents/" + document_id)
                record["recovery_http_status"] = recovered.status_code
                if recovered.status_code == 200:
                    state = recovered.json().get("status")
                    record["recovered_status"] = state if state in {"recibido", "procesado", "auditoria_humana"} else "UNRECOGNIZED"
            return record
        payload = response.json()
        record.update(compare_result(case["expected"], payload))
        document_id = safe_id(payload.get("documento_id"))
        if not document_id:
            raise ValueError("ID inseguro.")
        record["document_id"] = document_id
        recovered = client.get("/api/documents/" + document_id)
        record["get_http_status"] = recovered.status_code
        record["get_matches_post"] = recovered.status_code == 200 and recovered.json() == payload
        record["technical_ok"] = record["get_matches_post"] and record["coherent_routing"] and record["final_storage_declared"]
        record["outcome"] = "passed" if record["technical_ok"] and record["matches_dataset"] else "mismatch"
    except Exception as error:
        # Agregado por Edil: no guardar el error crudo, JSON extraído, nombres de
        # pacientes, diagnósticos o justificativos. Solo la categoría técnica.
        record["outcome"] = "execution_error"
        record["error_category"] = type(error).__name__
    finally:
        record["duration_seconds"] = round(time.monotonic() - start, 3)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--allow-cloud", action="store_true")
    parser.add_argument("--confirm-synthetic", action="store_true")
    parser.add_argument("--base-url", default="http://127.0.0.1:8141")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--case", action="append", dest="case_ids",
                        help="Evaluar solo este ID; permite repetir un caso corregido sin reenviar el dataset.")
    args = parser.parse_args(argv)
    cases = load_cases()
    if args.case_ids:
        selected = set(args.case_ids)
        if selected - {case["case_id"] for case in cases}:
            parser.error("ID no incluido en los casos normales/urgentes.")
        cases = [case for case in cases if case["case_id"] in selected]
    if args.check_only or not (args.allow_cloud and args.confirm_synthetic):
        print(json.dumps({"cloud_executed": False, "cases": len(cases),
                          "formats": {ext: sum(c["file"].suffix.lower() == ext for c in cases) for ext in MIMES}}))
        return 0 if args.check_only else 2
    url = urlsplit(args.base_url)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.path not in {"", "/"} or url.query or url.fragment:
        parser.error("Usar únicamente el backend de pruebas local, sin credenciales en la URL.")
    report_path = args.report or ROOT / f"docs/sprint-3/evidencias/nico-dataset-{uuid4().hex}.json"
    if report_path.exists():
        parser.error("La evidencia ya existe; elegir otro archivo para no sobrescribirla.")
    runtime_files = [
        "mediflow/backend/app/api/routes.py", "mediflow/backend/app/services/gemini_client.py",
        "mediflow/backend/app/services/triage_pipeline.py", "mediflow/backend/app/core/orquestador.py",
        "mediflow/data_ai/urgency_detector.py", "mediflow/data_ai/rules/urgency_catalog_v1_1.json",
        "mediflow/data_ai/prompts/master_prompt.txt", "mediflow/data_ai/score_confianza.py",
        "mediflow/data_ai/dataset/dataset_master.csv",
        "mediflow/data_ai/synthetic_demo_rules.py", "mediflow/data_ai/rules/triage_rules_v1.json",
    ]
    report = {
        "agregado_por": "Edil", "task": "S3-01.4 Nicolás",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "user_confirmed_synthetic": True, "real_pipeline": True, "mocks": False,
        "base_url": args.base_url, "planned_cases": len(cases),
        # Agregado por Edil: contexto declarado por quien inicia la instancia
        # local; no se deduce el perfil de la respuesta ni del nombre del caso.
        "operator_declared_rules_profile": os.getenv("TRIAGE_RULES_PROFILE", "general"),
        "runtime_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in runtime_files},
        "cases": [],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    def save():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Agregado por Edil: guardar por caso para no perder evidencia parcial si
    # se interrumpe la prueba. No limpiar objetos OCI ni alterar expectativas.
    save()
    with httpx.Client(base_url=args.base_url, timeout=120, follow_redirects=False, trust_env=False) as client:
        for case in cases:
            record = run_case(client, case)
            report["cases"].append(record)
            save()
            print(case["case_id"] + ": " + record["outcome"], flush=True)
            if record.get("http_status") in {401, 403, 429} or record["outcome"] == "execution_error":
                report["stop_reason"] = "auth_quota_or_transport_error_no_automatic_retry"
                break
    records = report["cases"]
    report["summary"] = {
        "planned": len(cases), "executed": len(records),
        "technical_passed": sum(r["technical_ok"] for r in records),
        "dataset_passed": sum(r["outcome"] == "passed" for r in records),
        "priority_matched": sum(r.get("comparisons", {}).get("priority", False) for r in records),
        "destination_matched": sum(r.get("comparisons", {}).get("destination", False) for r in records),
        "review_matched": sum(r.get("comparisons", {}).get("human_review", False) for r in records),
    }
    report["all_expectations_passed"] = len(records) == len(cases) and all(r["outcome"] == "passed" for r in records)
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    save()
    print(json.dumps(report["summary"]))
    return 0 if report["all_expectations_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
