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
    source_head = SimpleNamespace(headers={"content-length": str(len(source))})
    destination_head = SimpleNamespace(headers={"content-length": str(len(source))})
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
    client.head_object.side_effect = [SimpleNamespace(headers={"content-length": "7"}), OCIError(404), OCIError(404)]
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
        SimpleNamespace(headers={"content-length": "1"}),
        SimpleNamespace(headers={"content-length": "1"}),
    ]

    with pytest.raises(DestinationObjectExistsError):
        OCIObjectMover(client, "namespace", "region").move("x", "recibidos", "procesados")

    client.copy_object.assert_not_called()
    client.delete_object.assert_not_called()


def test_copy_conflict_is_reported_without_deleting_source():
    client = MagicMock()
    mover = ready_mover(client)
    client.copy_object.side_effect = OCIError(412)

    with pytest.raises(DestinationObjectExistsError):
        mover.move("x", "recibidos", "procesados")

    client.delete_object.assert_not_called()
