"""Pruebas locales del verificador optativo, sin conexiones OCI."""
import copy
import json
from types import SimpleNamespace

import pytest

from scripts import verify_sprint3_oci as verifier


def test_diagnostic_preserves_permission_code_without_secrets():
    inner = RuntimeError("private-token clinical-content https://private-url")
    inner.status, inner.code, inner.operation_name = 403, "InsufficientServicePermissions", "copy_object"
    outer = RuntimeError("private-outer")
    outer.__cause__ = inner
    result = verifier.safe_error(outer)
    assert result[1] == {"category": "RuntimeError", "status": 403, "code": "InsufficientServicePermissions", "operation_name": "copy_object"}
    assert "private" not in json.dumps(result)


def test_oci_writes_require_both_flags(tmp_path):
    for flags in ([], ["--allow-oci-writes"], ["--confirm-synthetic"]):
        with pytest.raises(SystemExit) as error:
            verifier.main(["--report", str(tmp_path / "unused.json"), *flags])
        assert error.value.code == 2


def test_preexisting_evidence_is_never_overwritten(tmp_path):
    path = tmp_path / "evidence.json"
    path.write_text("previous", encoding="utf-8")
    with pytest.raises(SystemExit):
        verifier.main(["--report", str(path), "--allow-oci-writes", "--confirm-synthetic"])
    assert path.read_text(encoding="utf-8") == "previous"


@pytest.mark.parametrize("url", ["https://external.example", "http://user:token@localhost", "http://127.0.0.1:8000/?token=private"])
def test_nonlocal_or_credential_urls_rejected_before_oci(tmp_path, url):
    with pytest.raises(SystemExit):
        verifier.main(["--report", str(tmp_path / "evidence.json"), "--base-url", url, "--allow-oci-writes", "--confirm-synthetic"])


def test_trace_rethrows_real_permission_failure():
    error = RuntimeError("private-message")
    error.status, error.code = 403, "InsufficientServicePermissions"
    def fail(**kwargs): raise error
    events = []
    proxy = verifier.TraceStorage(SimpleNamespace(copy_object=fail), events)
    with pytest.raises(RuntimeError) as caught:
        proxy.copy_object(copy_object_details=SimpleNamespace(source_object_if_match_e_tag="etag", destination_object_if_none_match_e_tag="*"))
    assert caught.value is error
    assert events[0]["errors"][0]["code"] == "InsufficientServicePermissions"
    assert events[0]["source_etag_condition"] and events[0]["destination_no_overwrite"]
    assert "private" not in json.dumps(events)


def test_failed_async_copy_records_worker_permission_error():
    events = []
    client = SimpleNamespace(
        get_work_request=lambda request: SimpleNamespace(status=200, data=SimpleNamespace(status="FAILED")),
        list_work_request_errors=lambda request: SimpleNamespace(data=[SimpleNamespace(code="InsufficientServicePermissions", message="InsufficientServicePermissions private-token")]),
    )
    verifier.TraceStorage(client, events).get_work_request("request-id")
    assert events[0]["worker_errors"] == [{"code": "InsufficientServicePermissions", "insufficient_service_permissions": True}]
    assert "private" not in json.dumps(events)


@pytest.mark.parametrize("review,state,destination", [(False, "procesado", "Cola_Farmacia"), (True, "auditoria_humana", "Cola_Revision_Humana")])
def test_local_fixture_uses_existing_orchestrator_without_mutating_receipt(monkeypatch, review, state, destination):
    monkeypatch.setenv("TRIAGE_RULES_PROFILE", "general")
    receipt = {"documento_id": "DOC-SYNTHETIC", "status": "recibido", "clasificacion": {"nivel_prioridad": "Rutina"},
        "datos_extraidos": {"paciente": {}, "medico_solicitante": {}},
        "decision_enrutamiento": {}, "almacenamiento_oci": {"bucket": "recibidos", "ruta_objeto": "DOC-SYNTHETIC.txt", "status_backup": "exito"}}
    snapshot = copy.deepcopy(receipt)
    result = verifier.fixture(receipt, review=review)
    assert receipt == snapshot
    assert result["status"] == state
    assert result["decision_enrutamiento"]["destino_principal"] == destination
    assert result["clasificacion"]["nivel_prioridad"] == "Rutina"
