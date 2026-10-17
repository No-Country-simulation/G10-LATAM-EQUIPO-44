from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.oci_transfer import (
    DestinationObjectExistsError,
    ObjectTransferError,
    OCIObjectMover,
    SourceObjectNotFoundError,
    TransferVerificationError,
)


class OCIError(Exception):
    def __init__(self, status: int):
        self.status = status


def response(size: int, content: bytes):
    return SimpleNamespace(
        headers={"content-length": str(size)},
        data=SimpleNamespace(raw=SimpleNamespace(stream=lambda *_args, **_kwargs: [content])),
    )


def ready_mover(client, *, source=b"safe test content"):
    # Agregado por Edil: emular las versiones que el SDK real entrega por ETag.
    source_head = SimpleNamespace(headers={"content-length": str(len(source)), "etag": "source-v1"})
    destination_head = SimpleNamespace(headers={"content-length": str(len(source)), "etag": "destination-v1"})
    client.head_object.side_effect = [
        source_head,
        OCIError(404),
        destination_head,
        destination_head,
    ]
    client.get_object.side_effect = [response(len(source), source), response(len(source), source)]
    client.copy_object.return_value = SimpleNamespace(headers={})
    return OCIObjectMover(
        client,
        "namespace",
        "us-phoenix-1",
        sleep=lambda _seconds: None,
        timeout=1,
    )


def test_success_verifies_content_before_deleting_source():
    client = MagicMock()

    def delete_only_after_two_reads(**_kwargs):
        assert client.get_object.call_count == 2

    client.delete_object.side_effect = delete_only_after_two_reads
    result = ready_mover(client).move("sample.txt", "recibidos", "procesados")

    assert result.object_name == "sample.txt"
    assert result.source_size == result.destination_size == len(b"safe test content")
    client.copy_object.assert_called_once()
    client.delete_object.assert_called_once_with(
        namespace_name="namespace",
        bucket_name="recibidos",
        object_name="sample.txt",
        if_match="source-v1",
    )


def test_copy_verifies_content_and_retains_source():
    client = MagicMock()
    result = ready_mover(client).copy("sample.txt", "recibidos", "procesados")

    assert result.source_size == result.destination_size == len(b"safe test content")
    client.copy_object.assert_called_once()
    client.delete_object.assert_not_called()


def test_delete_is_not_called_when_source_lookup_fails():
    client = MagicMock()
    client.head_object.side_effect = OCIError(500)

    with pytest.raises(ObjectTransferError):
        OCIObjectMover(client, "namespace", "region").move("x", "recibidos", "procesados")

    client.delete_object.assert_not_called()


def test_missing_source_is_reported():
    client = MagicMock()
    client.head_object.side_effect = OCIError(404)

    with pytest.raises(SourceObjectNotFoundError):
        OCIObjectMover(client, "namespace", "region").move("x", "recibidos", "procesados")

    client.copy_object.assert_not_called()
    client.delete_object.assert_not_called()


def test_copy_error_preserves_source():
    client = MagicMock()
    mover = ready_mover(client)
    client.copy_object.side_effect = OCIError(500)

    with pytest.raises(ObjectTransferError):
        mover.move("x", "recibidos", "procesados")

    client.delete_object.assert_not_called()


def test_destination_not_found_after_copy_preserves_source():
    client = MagicMock()
    client.head_object.side_effect = [SimpleNamespace(headers={"content-length": "7", "etag": "v1"}), OCIError(404), OCIError(404)]
    client.copy_object.return_value = SimpleNamespace(headers={})
    mover = OCIObjectMover(client, "namespace", "region", sleep=lambda _seconds: None, timeout=0)

    with pytest.raises(TransferVerificationError):
        mover.move("x", "recibidos", "procesados")

    client.delete_object.assert_not_called()


def test_integrity_error_preserves_source():
    client = MagicMock()
    mover = ready_mover(client, source=b"source")
    client.get_object.side_effect = [response(6, b"source"), response(6, b"changed")]

    with pytest.raises(TransferVerificationError):
        mover.move("x", "recibidos", "procesados")

    client.delete_object.assert_not_called()


def test_delete_error_is_reported_after_verified_copy():
    client = MagicMock()
    mover = ready_mover(client)
    client.delete_object.side_effect = OCIError(403)

    with pytest.raises(ObjectTransferError):
        mover.move("x", "recibidos", "procesados")

    client.delete_object.assert_called_once()


def test_existing_destination_is_never_overwritten():
    client = MagicMock()
    client.head_object.side_effect = [
        SimpleNamespace(headers={"content-length": "1", "etag": "v1"}),
        SimpleNamespace(headers={"content-length": "1", "etag": "v2"}),
    ]

    with pytest.raises(DestinationObjectExistsError):
        OCIObjectMover(client, "namespace", "region").move("x", "recibidos", "procesados")

    client.copy_object.assert_not_called()
    client.delete_object.assert_not_called()


def test_copy_conflict_is_reported_without_deleting_source():
    client = MagicMock()
    mover = ready_mover(client)
    client.copy_object.side_effect = OCIError(409)

    with pytest.raises(DestinationObjectExistsError):
        mover.move("x", "recibidos", "procesados")

    client.delete_object.assert_not_called()


# Agregado por Edil: proteger cambios concurrentes, además de comparar bytes.
def test_copy_and_hash_reads_use_the_observed_versions():
    client = MagicMock()
    ready_mover(client).copy("sample.txt", "recibidos", "procesados")

    details = client.copy_object.call_args.kwargs["copy_object_details"]
    assert details.source_object_if_match_e_tag == "source-v1"
    assert details.destination_object_if_none_match_e_tag == "*"
    assert [call.kwargs["if_match"] for call in client.get_object.call_args_list] == [
        "source-v1", "destination-v1"
    ]
    client.delete_object.assert_not_called()


def test_changed_source_during_copy_is_not_misreported_as_destination_conflict():
    client = MagicMock()
    mover = ready_mover(client)
    client.copy_object.side_effect = OCIError(412)

    with pytest.raises(ObjectTransferError, match="Cambió el origen") as caught:
        mover.move("sample.txt", "recibidos", "procesados")

    assert not isinstance(caught.value, DestinationObjectExistsError)
    client.delete_object.assert_not_called()


def test_changed_source_during_hash_read_preserves_source():
    client = MagicMock()
    mover = ready_mover(client)
    client.get_object.side_effect = OCIError(412)

    with pytest.raises(TransferVerificationError):
        mover.move("sample.txt", "recibidos", "procesados")

    client.delete_object.assert_not_called()


def test_changed_source_before_delete_is_not_deleted_unconditionally():
    client = MagicMock()
    mover = ready_mover(client)
    client.delete_object.side_effect = OCIError(412)

    with pytest.raises(ObjectTransferError):
        mover.move("sample.txt", "recibidos", "procesados")

    assert client.delete_object.call_args.kwargs["if_match"] == "source-v1"


def test_missing_source_etag_stops_before_copy_or_delete():
    client = MagicMock()
    client.head_object.return_value = SimpleNamespace(headers={"content-length": "1"})

    with pytest.raises(TransferVerificationError, match="etag"):
        OCIObjectMover(client, "namespace", "region").move("x", "recibidos", "procesados")

    client.copy_object.assert_not_called()
    client.delete_object.assert_not_called()


@pytest.mark.parametrize("object_name,source,destination", [
    ("", "recibidos", "procesados"),
    ("sample.txt", "recibidos", "recibidos"),
    ("sample.txt", "", "procesados"),
])
def test_invalid_transfer_has_no_storage_side_effects(object_name, source, destination):
    client = MagicMock()
    with pytest.raises(ValueError):
        OCIObjectMover(client, "namespace", "region").copy(object_name, source, destination)
    client.head_object.assert_not_called()
    client.copy_object.assert_not_called()
    client.delete_object.assert_not_called()


def test_storage_manager_copy_reuses_verifier_and_keeps_historical_move(monkeypatch):
    from app.core.oci_client import OCIStorageManager
    from app.core import oci_transfer

    manager = OCIStorageManager.__new__(OCIStorageManager)
    manager.object_storage = MagicMock()
    manager.namespace = "test-namespace"
    manager.config = {"region": "test-region"}
    manager.settings = SimpleNamespace(region=None)
    mover_factory = MagicMock()
    monkeypatch.setattr(oci_transfer, "OCIObjectMover", mover_factory)

    result = manager.copiar_archivo(" sample.txt ", " recibidos ", " procesados ")

    mover_factory.assert_called_once_with(
        manager.object_storage, "test-namespace", "test-region"
    )
    mover_factory.return_value.copy.assert_called_once_with(
        "sample.txt", "recibidos", "procesados"
    )
    assert result is mover_factory.return_value.copy.return_value
    mover_factory.return_value.move.assert_not_called()


def test_diagnostic_checks_three_buckets_without_listing_document_names(monkeypatch, capsys):
    from scripts import oci_diagnose

    manager = SimpleNamespace(
        object_storage=MagicMock(), namespace="test-namespace",
        settings=SimpleNamespace(bucket_recibidos="recibidos",
                                 bucket_procesados="procesados",
                                 bucket_auditoria="auditoria_humana"),
    )
    monkeypatch.setattr(oci_diagnose, "build_client", lambda _profile: manager)

    assert oci_diagnose.main([]) == 0

    assert manager.object_storage.get_bucket.call_count == 3
    manager.object_storage.list_objects.assert_not_called()
    manager.object_storage.get_object.assert_not_called()
    assert "test-namespace" not in capsys.readouterr().out


def test_diagnostic_does_not_print_sensitive_sdk_error(monkeypatch, capsys):
    from scripts import oci_diagnose

    def fail(_profile):
        raise RuntimeError("PRIVATE_TEST_PATH_AND_REQUEST_DATA")

    monkeypatch.setattr(oci_diagnose, "build_client", fail)

    assert oci_diagnose.main([]) == 1
    captured = capsys.readouterr()
    assert "PRIVATE_TEST_PATH_AND_REQUEST_DATA" not in captured.out + captured.err
    assert "RuntimeError" in captured.err
